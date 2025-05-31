import asyncio
from pymongo import AsyncMongoClient
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    logger.error("MONGO_URI not found in environment variables! Script cannot connect to DB.")
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

async def restore_template_obtained_counts():
    logger.info("Starting template item obtained counts restoration script from player obtained_items.")

    for clan_name, template_coll in CLAN_TEMPLATE_COLLS.items():
        logger.info(f"Processing data for clan: {clan_name}")

        try:

            template_doc = await template_coll.find_one({})
            if not template_doc:
                logger.error(f"Template document not found in collection '{template_coll.name}' for clan '{clan_name}'. Cannot restore obtained counts.")
                continue

            template_tiers = template_doc.get("tiers", {})
            if not isinstance(template_tiers, dict):
                 logger.error(f"Template document in '{template_coll.name}' for '{clan_name}' has an invalid 'tiers' field (not a dictionary). Skipping restoration for this clan.")
                 continue

            clan_item_obtained_counts: Dict[str, int] = {} 



            players_cursor = player_coll.find({"clan": clan_name}) 
            clan_players = await players_cursor.to_list(length=None)
            logger.info(f"Fetched {len(clan_players)} players for clan {clan_name}.")

        except Exception as e:
            logger.error(f"Error fetching template or players for clan {clan_name}: {e}", exc_info=True)
            continue 


        for player_doc in clan_players:

            obtained_items = player_doc.get("obtained_items", {})
            if not isinstance(obtained_items, dict):
                logger.warning(f"Player {player_doc.get('discord_id')} in clan {clan_name} has invalid 'obtained_items' field (not a dictionary). Skipping.")
                continue

            for item_key, count in obtained_items.items():
                if isinstance(item_key, str):
                    try:
                        count_int = int(count)
                        if item_key not in clan_item_obtained_counts:
                            clan_item_obtained_counts[item_key] = 0

                        clan_item_obtained_counts[item_key] += count_int
                    except (ValueError, TypeError):
                        logger.warning(f"Non-integer count for item key '{item_key}' in obtained_items for player {player_doc.get('discord_id')} in clan {clan_name}. Skipping.")
                        continue 
                else:
                    logger.warning(f"Non-string item key '{item_key}' in obtained_items for player {player_doc.get('discord_id')} in clan {clan_name}. Skipping.")


        logger.info(f"Finished processing player obtained_items for clan {clan_name}. Calculated item obtained totals: {clan_item_obtained_counts}")


        template_modified = False


        for t_name, t_data in template_tiers.items():
            if not isinstance(t_data, dict): continue
            sources = t_data.get("sources", [])
            if not isinstance(sources, list): continue 

            for s_data in sources:
                if not isinstance(s_data, dict): continue 
                items = s_data.get("items", [])
                if not isinstance(items, list): continue 
                source_name = s_data.get("name")

                if source_name:
                    for i_data in items:
                        if not isinstance(i_data, dict): continue 
                        item_name = i_data.get("name")

                        if item_name:
                            # Construct the unique item key matching the player's obtained_items format
                            item_key = f"{t_name}.{source_name}.{item_name}"

                            # Get the calculated total obtained count for this item
                            calculated_total_obtained = clan_item_obtained_counts.get(item_key, 0)

                            # Update the 'obtained' field in the template entry
                            current_obtained_value = i_data.get("obtained", 0)
                            try:
                                # Convert current_obtained_value to int before comparison/setting
                                current_obtained_int = int(current_obtained_value)

                                if current_obtained_int != calculated_total_obtained:
                                    i_data["obtained"] = calculated_total_obtained # Set the obtained count
                                    template_modified = True
                                    logger.debug(f"Restored obtained count for '{item_key}' in template for '{clan_name}' to {calculated_total_obtained}. Old value was {current_obtained_int}.")
                                else:
                                     logger.debug(f"Obtained count for '{item_key}' in template for '{clan_name}' is already correct ({calculated_total_obtained}).")

                            except (ValueError, TypeError):
                                logger.error(f"Could not convert current 'obtained' value to int for item '{item_key}' in template for '{clan_name}'. Skipping update for this item.")


        if template_modified:
            try:
                update_result = await template_coll.replace_one(
                    {"_id": template_doc["_id"]},
                    template_doc
                )

                if update_result.modified_count > 0:
                    logger.info(f"Successfully saved restored template document for clan '{clan_name}'.")
                else:
                    logger.warning(f"Restored template document for clan '{clan_name}' was not modified despite calculations (replace_one didn't report changes).")

            except Exception as e:
                logger.error(f"Error saving restored template document for clan {clan_name}: {e}", exc_info=True)
        else:
            logger.info(f"No item obtained counts were updated in the template for clan '{clan_name}'.")


    logger.info("Template item obtained counts restoration script finished.")


async def main():
    await restore_template_obtained_counts()

if __name__ == "__main__":
    asyncio.run(main())