# This script would run independently, likely as a scheduled task.
import asyncio
from pymongo import AsyncMongoClient
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    logger.error("MONGO_URI not found in environment variables!")
    exit()

# Database and collections
mongo = AsyncMongoClient(host=MONGO_URI)
db = mongo["Frenzy"]
player_coll = db["Players"]
ironfoundry_template_coll = db["ironfoundry"] # Correct collection for IF templates
ironclad_template_coll = db["ironclad"]   # Correct collection for IC templates

# Mapping clan names to their template collections
CLAN_TEMPLATE_COLLS = {
    "ironfoundry": ironfoundry_template_coll,
    "ironclad": ironclad_template_coll,
}

async def aggregate_activity_data():
    logger.info("Starting activity data aggregation script.")

    for clan_name, template_coll in CLAN_TEMPLATE_COLLS.items(): # template_coll here is the specific clan collection
        logger.info(f"Aggregating data for clan: {clan_name}")

        try:
            # Fetch the clan's template document from the specific clan collection
            # Assuming there's only one template document per clan collection
            template_doc = await template_coll.find_one({})
            if not template_doc:
                logger.error(f"Template document not found in collection '{template_coll.name}' for clan '{clan_name}'. Cannot aggregate activity totals.")
                continue # Move to the next clan

            # Get the activities array from the template
            template_activities = template_doc.get("activities", [])
            if not isinstance(template_activities, list):
                 logger.error(f"Template document in '{template_coll.name}' for '{clan_name}' has an invalid 'activities' field (not a list). Skipping aggregation for this clan.")
                 continue

            # Create a map for easy lookup of activities in the template by name and unit
            template_activity_map: Dict[str, Dict[str, Any]] = {} # Key: "ActivityName:MetricName"
            for activity_entry in template_activities:
                act_name = activity_entry.get("name")
                act_unit = activity_entry.get("unit")
                # Check if the activity entry has both name and unit
                if act_name and act_unit:
                    template_activity_map[f"{act_name}:{act_unit}"] = activity_entry
                else:
                    logger.warning(f"Activity entry in template in '{template_coll.name}' for '{clan_name}' is missing 'name' or 'unit': {activity_entry}")


            # Initialize aggregated differences
            aggregated_diffs: Dict[str, Dict[str, float]] = {} # { "ActivityName": { "MetricName": total_difference } }


            # Fetch all player documents for this clan
            players_cursor = player_coll.find({"clan": clan_name}) # Assuming player documents have 'clan' field
            clan_players = await players_cursor.to_list(length=None)
            logger.info(f"Fetched {len(clan_players)} players for clan {clan_name}.")

        except Exception as e:
            logger.error(f"Error fetching template or players for clan {clan_name}: {e}", exc_info=True)
            continue # Move to the next clan

        # --- Process each player's tracking entries ---
        for player_doc in clan_players:
            # Ensure 'tracking' field exists and is a list
            tracking_entries = player_doc.get("tracking", [])
            if not isinstance(tracking_entries, list):
                logger.warning(f"Player {player_doc.get('discord_id')} in clan {clan_name} has invalid 'tracking' field (not a list). Skipping.")
                continue

            for entry in tracking_entries:
                activity_name = entry.get("name")
                start_data = entry.get("start")
                end_data = entry.get("end")

                # Process only completed tracking entries
                # Check if name, start, and end are present and end has values
                if activity_name and start_data and end_data and end_data.get("values"):
                    start_values = start_data.get("values", {})
                    end_values = end_data.get("values", {})

                    # Iterate over the metrics recorded at the end
                    if isinstance(end_values, dict): # Ensure end_values is a dictionary
                         for metric_name, end_value in end_values.items():
                             # Ensure start_value exists and is numeric
                             start_value = start_values.get(metric_name, 0) # Get corresponding start value, default to 0
                             try:
                                 start_value = float(start_value) # Ensure it's numeric
                                 end_value = float(end_value)   # Ensure it's numeric
                                 difference = end_value - start_value

                                 # Aggregate the difference for this specific activity and metric
                                 if activity_name not in aggregated_diffs:
                                     aggregated_diffs[activity_name] = {}
                                 if metric_name not in aggregated_diffs[activity_name]:
                                     aggregated_diffs[activity_name][metric_name] = 0.0

                                 aggregated_diffs[activity_name][metric_name] += difference
                             except (ValueError, TypeError):
                                 logger.warning(f"Non-numeric start or end value for metric '{metric_name}' in activity '{activity_name}' for player {player_doc.get('discord_id')} in clan {clan_name}. Skipping aggregation for this metric.")
                                 continue # Skip this metric


        logger.info(f"Finished processing player tracking entries for clan {clan_name}. Calculated differences: {aggregated_diffs}")


        # --- Update the clan's template document with aggregated values ---
        template_modified = False
        for activity_name, metrics_diffs in aggregated_diffs.items():
            for metric_name, total_difference in metrics_diffs.items():
                # Find the corresponding entry in the template's activities array
                template_entry_key = f"{activity_name}:{metric_name}"
                template_activity_entry = template_activity_map.get(template_entry_key)

                if template_activity_entry:
                    # Add the aggregated difference to the current_value in the template entry
                    current_value = template_activity_entry.get("current_value", 0.0) # Default to 0.0 for numeric
                    try:
                        template_activity_entry["current_value"] = float(current_value) + float(total_difference) # Ensure numeric addition
                        template_modified = True
                        logger.debug(f"Updated current_value for '{activity_name}' ({metric_name}) in template for '{clan_name}' by {total_difference}. New value: {template_activity_entry['current_value']}")
                    except (ValueError, TypeError):
                         logger.error(f"Could not convert current_value or total_difference to float for '{activity_name}' ({metric_name}) in template for '{clan_name}'. Skipping update for this metric.")
                         continue
                else:
                    logger.warning(f"Matching activity entry not found in template in '{template_coll.name}' for '{clan_name}' for tracking data: '{activity_name}' ({metric_name}). Skipping update for this metric.")

        # Save the updated template document if any changes were made
        if template_modified:
            try:
                # Use replace_one to save the modifications to the activities array
                update_result = await template_coll.replace_one(
                    {"_id": template_doc["_id"]},
                    template_doc
                )

                if update_result.modified_count > 0:
                    logger.info(f"Successfully saved updated template document for clan '{clan_name}'.")
                else:
                    logger.warning(f"Template document for clan '{clan_name}' was not modified despite aggregation (replace_one didn't report changes).")

            except Exception as e:
                logger.error(f"Error saving updated template document for clan {clan_name}: {e}", exc_info=True)
        else:
            logger.info(f"No activity current_values were updated in the template for clan '{clan_name}'.")


    logger.info("Activity data aggregation script finished.")


async def activity_update():
    await aggregate_activity_data()

