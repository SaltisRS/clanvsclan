from decimal import DivisionByZero
import math
from typing import Any, Dict, List, Literal, Optional, Tuple
import discord

from loguru import logger
from dotenv import load_dotenv
from discord import Embed, app_commands
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from cachetools import TTLCache


from ..modules.activity_modals import ACTIVITY_MODAL_MAP, get_activity_modal_class, upload_screenshot


load_dotenv()
IC_roleid = 1343921208948953128
IF_roleid = 1343921101687750716
ICPERM = [1369428787342737488, 1369428819907448832]
IFPERM = [1369428706161852436, 1369428754773840082]
autocomplete_cache = TTLCache(maxsize=512, ttl=30)
db = Optional[AsyncDatabase]
if_coll = Optional
ic_coll = Optional
template_coll = Optional
player_coll = Optional

SPECIAL_FRENZY_MULTIPLIER_NAMES = {
    "Banana Split",
    "Demon Slayer II",
    "Oscar Worthy",
    "How to Smelt Your Dragon",
    "Raining Blood",
    "The Zarosian Candidate",
    "Rock Solid",
    "Shape of Italy",
    "Mystic Pizza",
    "Eye of the Beholder",
    "Lord of Bones",
    "Man Purse",
    "Gonna Need a Bigger Boat",
    "Kitchen Nightmares",
    "Rogue One",
    "Throwing Shade",
    "Get to the Chompa!",
    "Return the Slab",
    "Deadliest Catch",
    "What's in the Box?!",
    "Rag and Bone Man III",
    "Agent of Chaos",
    "The Blade that was Broken",
    "Tzhaar Wars",
    "CANNONBALL!"
}


IMAGE_UPLOAD_CHOICES = [
    app_commands.Choice(name="Hunter's Guild", value="Hunter's Guild"),
    app_commands.Choice(name="Clue Caskets", value="Clue Caskets"),
    app_commands.Choice(name="Gotr Points", value="Gotr Points"),
    app_commands.Choice(name="Wintertodt Cart", value="Wintertodt Cart"),
    app_commands.Choice(name="Brimstone Keys", value="Brimstone Keys"),
    app_commands.Choice(name="Bryophyta Keys", value="Bryophyta Keys"),
    app_commands.Choice(name="Obor Keys", value="Obor Keys"),
    app_commands.Choice(name="Impling Jars", value="Impling Jars"),
    app_commands.Choice(name="Ancient Totems", value="Ancient Totems"),
    app_commands.Choice(name="Soulwars Crates", value="Soulwars Crates"),
    app_commands.Choice(name="Mermaid Tears", value="Mermaid Tears"),
    app_commands.Choice(name="Shade Keys", value="Shade Keys"),
    app_commands.Choice(name="Tempoross Reward Pool", value="Tempoross Reward Pool"),
]

async def autocomplete_activity(interaction: discord.Interaction, current: str):
     return [
         discord.app_commands.Choice(name=activity, value=activity)
         for activity in ACTIVITY_MODAL_MAP.keys()
         if current.lower() in activity.lower()
     ][:25]

async def autocomplete_activity_metric(interaction: discord.Interaction, current: str):
    """Autocomplete for activity metrics based on the selected activity."""
    activity = getattr(interaction.namespace, "activity", None)
    activity_data = ACTIVITY_METRICS.get(activity) # type: ignore
    if not activity_data:
        return []

    available_metrics = activity_data.get("metrics", [])

    return [
        discord.app_commands.Choice(name=metric, value=metric)
        for metric in available_metrics
        if current.lower() in metric.lower()
    ][:25]

async def autocomplete_tier(interaction: discord.Interaction, current: str):
    if "tiers" not in autocomplete_cache:
        template = await template_coll.find_one({})
        if not template:
            return []
        autocomplete_cache["tiers"] = list(template.get("tiers", {}).keys())

    return [
        discord.app_commands.Choice(name=tier, value=tier)
        for tier in autocomplete_cache["tiers"]
        if current.lower() in tier.lower()
    ][:25]

async def autocomplete_source(interaction: discord.Interaction, current: str):
    tier = getattr(interaction.namespace, "tier", None)
    if not tier:
        return []

    cache_key = f"sources_{tier}"
    if cache_key not in autocomplete_cache:
        template = await template_coll.find_one({})
        if not template or tier not in template.get("tiers", {}):
            return []

        sources = template["tiers"][tier].get("sources", [])
        autocomplete_cache[cache_key] = [source["name"] for source in sources]

    return [
        discord.app_commands.Choice(name=source, value=source)
        for source in autocomplete_cache[cache_key]
        if current.lower() in source.lower()
    ][:25]


async def autocomplete_item(interaction: discord.Interaction, current: str):
    tier = getattr(interaction.namespace, "tier", None)
    source = getattr(interaction.namespace, "source", None)
    if not tier or not source:
        return []

    cache_key = f"items_{tier}_{source}"
    if cache_key not in autocomplete_cache:
        template = await template_coll.find_one({})
        if not template or tier not in template.get("tiers", {}):
            return []

        sources = template["tiers"][tier].get("sources", [])
        source_data = next((s for s in sources if s["name"] == source), None)
        if not source_data:
            return []

        items = [item["name"] for item in source_data.get("items", [])]
        autocomplete_cache[cache_key] = items

    return [
        discord.app_commands.Choice(name=item, value=item)
        for item in autocomplete_cache[cache_key]
        if current.lower() in item.lower()
    ][:25]

def get_template_collection(clan: str):
    
    """Returns the correct template collection based on clan string."""
    if clan == "ironfoundry":
        return if_coll
    elif clan == "ironclad":
        return ic_coll
    else:
        logger.warning(f"Attempted to get template collection for unknown clan: {clan}")
        return None
    
async def get_player_info(discord_id: int):
    
    """Fetches a player's document from the Players collection."""
    try:
        player_document = await player_coll.find_one({"discord_id": discord_id})
        return player_document
    except Exception as e:
        logger.error(f"Error fetching player info for {discord_id}: {e}", exc_info=True)
        return None

async def get_clan_from_roles(interaction: discord.Interaction):
    for role in interaction.user.roles:
        if role.id == IF_roleid:
            return "ironfoundry"
        if role.id == IC_roleid:
            return "ironclad"

    return None


async def _template_find_helper(template_doc: Dict[str, Any], tier_name: str, source_name: str, item_name: str) -> Optional[Dict[str, Any]]:
    """Finds an item's data within a loaded template document."""
    if not template_doc:
        return None
    tiers = template_doc.get("tiers", {})
    tier_data = tiers.get(tier_name)
    if not tier_data:
        return None
    sources = tier_data.get("sources", [])
    for source_data in sources:
        if source_data.get("name") == source_name:
            items = source_data.get("items", [])
            for item_data in items:
                if item_data.get("name") == item_name:
                    # Return a dictionary containing the item, its source, and its tier for context
                    return {"item": item_data, "source": source_data, "tier": tier_data, "tier_name": tier_name}
    return None


async def _template_unlock_multi(template_doc: Dict[str, Any], template_doc_before_submission: Dict[str, Any]):
    """
    Checks if any clan multipliers should be unlocked based on the template's
    item obtained counts and updates the template document if so.
    Compares against template_doc_before_submission to log *newly* unlocked multipliers.
    """
    clan_multipliers = template_doc.get("multipliers", [])
    clan_multipliers_before = template_doc_before_submission.get("multipliers", [])
    template_modified = False
    newly_unlocked_multipliers: List[str] = [] # To track newly unlocked multipliers

    # Create a mapping of item names to their obtained counts in the template for quick lookup
    template_item_obtained_counts = {}
    for tier_name, tier_data in template_doc.get("tiers", {}).items():
        for source_data in tier_data.get("sources", []):
            for item_data in source_data.get("items", []):
                template_item_obtained_counts[item_data.get("name")] = item_data.get("obtained", 0)

    for i, multiplier in enumerate(clan_multipliers):
        # Only check multipliers that are not yet unlocked in the CURRENT template_doc
        if not multiplier.get("unlocked", False):
             required_item_names = multiplier.get("requirement", [])
             all_requirements_met_in_template = True

             for required_item_name in required_item_names:
                 # Check if the item exists in the template AND has been obtained at least once
                 if template_item_obtained_counts.get(required_item_name, 0) == 0:
                     all_requirements_met_in_template = False
                     break # No need to check further requirements for this multiplier

             if all_requirements_met_in_template:
                 multiplier["unlocked"] = True # Modify the template_doc in place
                 template_modified = True

                 # Check if this multiplier was UNLOCKED in this process
                 # Compare its 'unlocked' status in the current vs. before template
                 if i < len(clan_multipliers_before) and not clan_multipliers_before[i].get("unlocked", False):
                      newly_unlocked_multipliers.append(multiplier.get('name', 'Unnamed Multiplier'))


    if template_modified:
        # Save the template document with the updated 'unlocked' flag(s)
        try:
            # Using replace_one as previously decided for simplicity, as accept_button handles the full save.
            # The template_doc object itself has been modified in place.
            pass # We'll let the accept_button method handle the save

        except Exception as e:
            # Log any errors during this checking phase if needed, though the main save happens later
            logger.error(f"Error during multiplier unlock check for clan '{template_doc.get('associated_team')}': {e}", exc_info=True)

    return newly_unlocked_multipliers

def _player_calculate_helper(item_data: Dict[str, Any]) -> float:
    """
    Calculates points for an item by awarding its base_points for EACH instance obtained.
    Ignores unique/duplicate thresholds; assumes base_points is per-instance.
    """
    total_item_points = 0.0
    current_obtained = int(item_data.get("obtained", 0))
    base_points = float(item_data.get("points", 0))

    # Points are awarded for each instance obtained
    total_item_points = current_obtained * base_points

    return total_item_points

def _template_calculate_helper(item_data: Dict[str, Any]) -> float:
    """
    Calculates the total points an item should contribute based on its current 'obtained' count,
    dynamically applying thresholds derived from the item's 'required' and 'duplicate_required' fields.

    NOTE: The item_data's 'required' and 'duplicate_required' fields define the context
          for 'half' and 'full' for that specific item's configuration (e.g., Ironfoundry vs. Ironclad).
    """
    try: # Keep the try-except for robustness
        total_item_points = 0.0
        current_obtained = int(item_data.get("obtained", 0))
        base_points = float(item_data.get("points", 0))
        duplicate_item_points = float(item_data.get("duplicate_points", 0))
        
        # Correctly initialize both variables from item_data
        unique_required = int(item_data.get("required", 1))
        duplicate_items_for_set = int(item_data.get("duplicate_required", 1))

        # Safety checks (fixed typo on the duplicate variable assignment)
        if unique_required <= 0:
            unique_required = 1
        # --- FIX IS HERE: changed `duplicate_required_for_set` to `duplicate_items_for_set` ---
        if duplicate_items_for_set <= 0:
            duplicate_items_for_set = 1


        # --- Points from Unique Obtainment: ---
        # Awards full base_points if current_obtained meets unique_required
        if current_obtained >= unique_required:
            total_item_points += base_points
        # Awards half base_points ONLY if unique_required is 2 and obtained is 1
        # This covers the "half unique value" rule specifically for items requiring 2 uniques.
        elif unique_required == 2 and current_obtained == 1:
            total_item_points += base_points / 2

        # --- Points from Duplicate Obtainment: ---
        # Calculate how many items are obtained beyond the unique requirement.
        obtained_beyond_unique = current_obtained - unique_required

        # Awards full duplicate_item_points if obtained_beyond_unique meets duplicate_required_for_set
        if obtained_beyond_unique >= duplicate_items_for_set: # Use duplicate_items_for_set
            total_item_points += duplicate_item_points
        # Awards half duplicate_item_points ONLY if duplicate_required_for_set is 2 and obtained_beyond_unique is 1
        # This covers the "half dupe value" rule specifically for items requiring 2 duplicates.
        elif duplicate_items_for_set == 2 and obtained_beyond_unique == 1: # Use duplicate_items_for_set
            total_item_points += duplicate_item_points / 2

    except Exception as e:
        total_item_points = 0
        # Consider using a more specific logger here, e.g., self.logger.error, or just logger.exception
        logger.debug(e) # This will log the error if something else goes wrong
        
    logger.debug(total_item_points) # This will log the final calculated value (or 0 if error)
    return total_item_points

def does_multiplier_affect_source(multiplier_data: Dict[str, Any], source_name: str) -> bool:
    """Checks if a multiplier affects a given source."""
    affected_sources = multiplier_data.get("affects", [])
    return source_name in affected_sources


class SubmissionView(discord.ui.View):
    def __init__(self, submitter_id: int, original_interaction_id: int, clan_of_submission: str, tier_name: str, source_name: str, item_name: str):
        super().__init__(timeout=None)
        self.submitter_id = submitter_id
        self.original_interaction_id = original_interaction_id
        self.clan_of_submission = clan_of_submission
        self.tier_name = tier_name
        self.source_name = source_name
        self.item_name = item_name

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        user_role_ids = [role.id for role in interaction.user.roles]
        required_permission_roles = IFPERM + ICPERM

        for required_role_id in required_permission_roles:
            if required_role_id in user_role_ids:
                return True

        return False


    async def _get_submission_documents(self):
        """Fetches and validates player and template documents."""
        player_document = await get_player_info(self.submitter_id)
        if not player_document:
            logger.error(f"Player data not found for submitter {self.submitter_id} on accept.")
            return None

        template_collection = get_template_collection(self.clan_of_submission)
        if template_collection is None:
            logger.error(f"Template collection not found for clan '{self.clan_of_submission}'.")
            return None

        template_doc = await template_collection.find_one({})
        if not template_doc:
            logger.error(f"Template document missing for clan '{self.clan_of_submission}'.")
            return None
        return player_document, template_doc, template_collection


    async def _check_submission_rejection(self, item_template_data: Dict[str, Any], old_obtained_count: int) -> bool:
        """Checks if the submission should be rejected based on item's obtained state."""
        unique_req = int(item_template_data.get("required", 1))
        dup_req_items = int(item_template_data.get("duplicate_required", 1))
        max_points_threshold = unique_req + dup_req_items

        if old_obtained_count >= max_points_threshold:
            logger.info(f"Item '{self.item_name}' (obtained: {old_obtained_count}) already past max points threshold ({max_points_threshold}). Rejecting.")
            return True
        return False


    def _update_item_obtained_count(self, item_template_data: Dict[str, Any]) -> int:
        """Increments the item's obtained count and returns the new count."""
        new_obtained_count = item_template_data.get("obtained", 0) + 1
        item_template_data["obtained"] = new_obtained_count
        logger.info(f"Template: Incremented obtained count for '{self.item_name}' to {new_obtained_count} in clan '{self.clan_of_submission}'.")
        return new_obtained_count




    def _template_calculate_points(self, template_doc: Dict[str, Any]) -> float:
        """
        Calculates the total potential points for the template based on
        current obtained counts and unlocked multipliers,
        including the "Frenzy" source multiplier logic,
        where a source becomes Frenzied if all its items have 'obtained' > 0.
        """
        total_template_points = 0.0
        clan_multipliers = template_doc.get("multipliers", [])

        
        for t_name, t_data in template_doc.get("tiers", {}).items():
            if not isinstance(t_data, dict):
                logger.warning(f"Malformed tier data for '{t_name}'. Skipping.")
                continue
            t_data["points_gained"] = 0.0

            sources = t_data.get("sources", [])
            if not isinstance(sources, list):
                logger.warning(f"Malformed sources list for tier '{t_name}'. Skipping.")
                continue

            for s_data in sources:
                if not isinstance(s_data, dict):
                    logger.warning(f"Malformed source data in tier '{t_name}'. Skipping.")
                    continue
                s_data["source_gained"] = 0.0
                source_name = s_data.get("name")

                if not source_name:
                    logger.warning(f"Source missing 'name' in tier '{t_name}'. Skipping.")
                    continue

                effective_multiplier_factor = 1.0
                special_frenzy_applied_to_source = False

                for multiplier in clan_multipliers:
                    if not isinstance(multiplier, dict):
                        logger.warning(f"Malformed multiplier data found: {multiplier}. Skipping.")
                        continue

                    multiplier_name = multiplier.get("name")

                    if multiplier.get("unlocked", False) and does_multiplier_affect_source(multiplier, source_name):
                        factor = float(multiplier.get("factor", 1.0))
                        effective_multiplier_factor *= factor
                        logger.debug(f"Applied multiplier '{multiplier_name}' ({factor}x) to source '{source_name}'.")

                        if multiplier_name in SPECIAL_FRENZY_MULTIPLIER_NAMES:
                            special_frenzy_applied_to_source = True


                source_items = s_data.get("items", [])
                if not isinstance(source_items, list):
                    logger.warning(f"Source '{source_name}' has invalid 'items' field (not a list). Skipping Frenzy check.")
                    source_items = []

                all_items_uniquely_obtained_in_source = True
                if not source_items:
                    all_items_uniquely_obtained_in_source = False
                else:
                    for item_data in source_items:
                        if not isinstance(item_data, dict):
                            logger.warning(f"Malformed item data in source '{source_name}'. Skipping for Frenzy check.")
                            all_items_uniquely_obtained_in_source = False
                            break
                        
                        item_obtained_count = int(item_data.get("obtained", 0))

                        if item_obtained_count <= 0:
                            all_items_uniquely_obtained_in_source = False
                            break


                if all_items_uniquely_obtained_in_source and not special_frenzy_applied_to_source:
                    FRENZY_DEFAULT_FACTOR = 1.25
                    effective_multiplier_factor *= FRENZY_DEFAULT_FACTOR
                    logger.debug(f"Applied default Frenzy multiplier ({FRENZY_DEFAULT_FACTOR}x) to source '{source_name}.")


                source_before = 0
                source_after = 0
                for i_data in s_data.get("items", []):
                    if not isinstance(i_data, dict):
                        logger.warning(f"Malformed item data in source '{source_name}'. Skipping point calculation.")
                        continue

                    item_total_points_base = _template_calculate_helper(i_data)

                    item_total_points_multiplied = item_total_points_base * effective_multiplier_factor
                    source_before += item_total_points_base
                    source_after += item_total_points_multiplied
                    s_data["source_gained"] += item_total_points_multiplied
                logger.debug(s_data["name"])
                logger.debug(f"{source_before}: Base")
                logger.debug(f"{source_after}: Multiplied")
                t_data["points_gained"] += s_data["source_gained"]
            total_template_points += t_data["points_gained"]

        template_doc["total_gained"] = total_template_points

        return total_template_points

    async def _player_calulate_from_items(self,
    player_document: Dict[str, Any],
    template_document: Dict[str, Any]
) -> float:
        """
        Calculates a player's total points based on their obtained items,
        applying applicable UNLOCKED clan multipliers and source-based multipliers.

        Args:
            player_document: The player's document from the database.
            template_document: The clan's template document from the database.

        Returns:
            The calculated total points for the player.
        """
        if not player_document or not template_document:
            logger.error("Player or template document is missing for player total points calculation.")
            return 0.0

        player_total_points = 0.0
        player_clan = player_document.get("clan")
        player_obtained_items = player_document.get("obtained_items", {})

        clan_multipliers = template_document.get("multipliers", [])
        unlocked_clan_multipliers = [
            m for m in clan_multipliers if m.get("unlocked", False)
        ]



        for item_key, obtained_count_player in player_obtained_items.items():
            if not isinstance(item_key, str) or not isinstance(obtained_count_player, int) or obtained_count_player <= 0:
                logger.warning(f"Malformed obtained_item entry for player {player_document.get('discord_id')}: {item_key}: {obtained_count_player}. Skipping.")
                continue

            parts = item_key.split('.')
            if len(parts) != 3:
                logger.warning(f"Invalid item_key format '{item_key}' for player {player_document.get('discord_id')}. Skipping.")
                continue
            tier_name, source_name, item_name = parts

            item_info = await _template_find_helper(template_document, tier_name, source_name, item_name)
            if not item_info or "item" not in item_info:
                logger.warning(f"Item template data not found for item key '{item_key}' in template for clan '{player_clan}'. Skipping.")
                continue
            item_template_data = item_info["item"]


            temp_item_data_for_calculation = item_template_data.copy()
            temp_item_data_for_calculation["obtained"] = obtained_count_player


            item_base_contribution = _player_calculate_helper(temp_item_data_for_calculation)

            effective_unlocked_multiplier_factor = 1.0
            for multiplier_data in unlocked_clan_multipliers:
                if does_multiplier_affect_source(multiplier_data, source_name):
                    factor = float(multiplier_data.get("factor", 1.0))
                    effective_unlocked_multiplier_factor *= factor

            item_total_contribution = item_base_contribution * effective_unlocked_multiplier_factor

            player_total_points += item_total_contribution

        return player_total_points

    async def _player_obtained_count(self, player_document: Dict[str, Any], points_gained_this_submission: float, new_obtained_count_template: int):
        player_obtained_items = player_document.get("obtained_items", {})
        item_key = f"{self.tier_name}.{self.source_name}.{self.item_name}"
        player_obtained_items[item_key] = player_obtained_items.get(item_key, 0) + 1 
        player_document["obtained_items"] = player_obtained_items



        if "submissions" not in player_document: player_document["submissions"] = []
        player_document["submissions"].append({
            "item": self.item_name, "source": self.source_name, "tier": self.tier_name,
            "status": "accepted", "accepted_by": self.original_interaction_id,
            "timestamp": discord.utils.utcnow(), "points_awarded": points_gained_this_submission
        })


    async def _player_recalculate_all(self):
        """
        Recalculates the total_gained points for ALL players in the database
        based on their obtained_items and the latest UNLOCKED clan multipliers.
        Updates each player's document in the database.

        This function is intended for periodic execution, not on every submission.
        """
        logger.info("Starting recalculation of all player points and database update.")

        template_docs = {}
        try:
            if_template_doc = await if_coll.find_one({})
            if if_template_doc:
                template_docs["ironfoundry"] = if_template_doc
            else:
                logger.warning("Ironfoundry template document not found.")

            ic_template_doc = await ic_coll.find_one({})
            if ic_template_doc:
                template_docs["ironclad"] = ic_template_doc
            else:
                logger.warning("Ironclad template document not found.")

        except Exception as e:
            logger.error(f"Error fetching template documents for global recalculation: {e}", exc_info=True)
            return 

        if not template_docs:
            logger.warning("No template documents loaded. Skipping global player points recalculation.")
            return


        all_players_cursor = player_coll.find({})
        all_players = await all_players_cursor.to_list(length=None)
        logger.info(f"Fetched {len(all_players)} players for global recalculation.")

        players_updated_count = 0
        errors_count = 0

        for player_doc in all_players:
            player_id = player_doc.get("_id")
            discord_id = player_doc.get("discord_id")
            player_clan = player_doc.get("clan")

            if not player_clan or player_clan not in template_docs:
                logger.warning(f"Player {discord_id} has invalid/unknown clan '{player_clan}'. Skipping point recalculation for this player.")
                errors_count += 1
                continue

            current_template = template_docs[player_clan]

            try:
                new_player_total_gained_unrounded = await self._player_calulate_from_items(
                    player_doc,
                    current_template
                )

                new_player_total_gained = round(new_player_total_gained_unrounded, 2)
                
                if not player_doc["total_gained"]:
                    player_doc["total_gained"] = 0.0

                old_player_total_gained = float(player_doc.get("total_gained", 0.0))

                if new_player_total_gained != old_player_total_gained:
                    player_doc["total_gained"] = new_player_total_gained

                    update_result = await player_coll.replace_one({"_id": player_id}, player_doc)

                    if update_result.modified_count > 0:
                        players_updated_count += 1

            except Exception as e:
                logger.error(f"Error recalculating or updating points for player {discord_id} ({player_id}): {e}", exc_info=True)
                errors_count += 1
        logger.info(f"Players checked: {len(all_players)}, Players updated: {players_updated_count}, Errors: {errors_count}")



    async def _submit_construct_message(self, interaction: discord.Interaction, button: discord.ui.Button, points_gained: float, player_total_points: float):
        """Sends feedback messages and disables buttons."""
        button.disabled = True
        button.label = "Accepted"
        if len(self.children) > 1 and isinstance(self.children[1], discord.ui.Button): # Check if deny button exists
            self.children[1].disabled = True
            self.children[1].label = "Accepted"
        await interaction.message.edit(view=self) # type: ignore

        await interaction.followup.send(
            f"Submission for '{self.item_name}' by <@{self.submitter_id}> accepted by {interaction.user.mention}.",
            ephemeral=True
        )
        submitter_user = interaction.client.get_user(self.submitter_id)
        if submitter_user:
            try:
                await submitter_user.send(f"Your submission for '{self.item_name}' has been accepted!")
            except discord.Forbidden:
                logger.warning(f"Could not DM submitter {self.submitter_id}.")


    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept_submission_button")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Accept button clicked by {interaction.user.id} for item '{self.item_name}' submitted by {self.submitter_id}")
        await interaction.response.defer()

        # 1. Get Documents
        docs = await self._get_submission_documents()
        if not docs:
            await interaction.followup.send("Error: Could not retrieve necessary data for processing.", ephemeral=True)
            return
        player_document, template_doc, template_collection = docs

        # 2. Find Item in Template
        item_info = await _template_find_helper(template_doc, self.tier_name, self.source_name, self.item_name)
        if not item_info:
            await interaction.followup.send(f"Error: Item '{self.item_name}' no longer found in template.", ephemeral=True)
            return
        item_template_data = item_info["item"]

        # Store the state of the template document *before* this submission for point calculation later
        import copy
        template_doc_before_submission = copy.deepcopy(template_doc)


        # 3. Check for Rejection
        old_obtained_count_template = int(item_template_data.get("obtained", 0))
        if await self._check_submission_rejection(item_template_data, old_obtained_count_template):
            button.disabled = True
            if len(self.children) > 1 and isinstance(self.children[1], discord.ui.Button): self.children[1].disabled = True
            await interaction.message.edit(view=self) # type: ignore
            await interaction.followup.send(
                f"Submission for '{self.item_name}' by <@{self.submitter_id}> rejected by {interaction.user.mention}.\n"
                f"Reason: Item has already reached its maximum point award threshold for the clan.",
                ephemeral=False
            )
            return

        # 4. Update Item Obtained Count in the TEMPLATE (modifies template_doc in place)
        new_obtained_count_template = self._update_item_obtained_count(item_template_data)

        total_template_points_before = self._template_calculate_points(template_doc_before_submission)

        newly_unlocked_multiplier_names = await _template_unlock_multi(template_doc, template_doc_before_submission)

        if newly_unlocked_multiplier_names:
             logger.info(f"Newly unlocked multipliers in this submission: {', '.join(newly_unlocked_multiplier_names)}")

        total_template_points_after = self._template_calculate_points(template_doc)
        points_gained_this_submission = total_template_points_after - total_template_points_before
        logger.info(f"Points gained from this submission calculated based on template change: {points_gained_this_submission:.2f}")



        # 5. Update Player Data
        await self._player_obtained_count(player_document, points_gained_this_submission, new_obtained_count_template)

        # 6. Save Changes to DB
        template_replace_result = await template_collection.replace_one({"_id": template_doc["_id"]}, template_doc)
        player_update_result = await player_coll.replace_one({"_id": player_document["_id"]}, player_document)

        # 7. Send Feedback
        if template_replace_result.acknowledged and player_update_result.acknowledged:
            await self._submit_construct_message(interaction, button, points_gained_this_submission, player_document["total_gained"])
            # Optional: Add information about newly unlocked multipliers to the feedback message
            if newly_unlocked_multiplier_names:
                 unlock_message = f"\n🎉 **Multipliers Unlocked:** {', '.join(newly_unlocked_multiplier_names)} 🎉"
                 try:
                     # Attempt to edit the original follow-up message
                     await interaction.channel.send(content=unlock_message) # type: ignore # This needs careful handling of original message content
                 except Exception as e:
                     logger.warning(f"Could not edit followup message to add unlock info: {e}")
                     # Or send a new message
                     await interaction.followup.send(unlock_message)

        else:
            await interaction.followup.send("Error: Failed to save updates to the database.", ephemeral=True)
            logger.error(f"DB save acknowledged status: Template={template_replace_result.acknowledged}, Player={player_update_result.acknowledged}")
        
        # 8. Recalculate Player points (leaderboards)
        await self._player_recalculate_all()


    
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_submission_button")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Submission denied by {interaction.user.id} for item '{self.item_name}' submitted by {self.submitter_id}")
        button.disabled = True
        if len(self.children) > 0 and isinstance(self.children[0], discord.ui.Button): self.children[0].disabled = True
        await interaction.message.edit(view=self) # type: ignore
        await interaction.response.send_message(f"Submission for '{self.item_name}' by <@{self.submitter_id}> denied by {interaction.user.mention}.", ephemeral=False)
        submitter_user = interaction.client.get_user(self.submitter_id)
        if submitter_user:
            try:
                await submitter_user.send(f"Your submission for '{self.item_name}' has been denied.")
            except discord.Forbidden:
                logger.warning(f"Could not DM submitter {self.submitter_id}.")
    
async def build_submission_embed(
    interaction: discord.Interaction,
    item_data: Dict[str, Any],
    source_data: Dict[str, Any],
    tier_name: str,
    screenshot: discord.Attachment
) -> discord.Embed:
    embed = Embed(
        title=item_data.get("name", "Unnamed Item")
    )
    embed.set_thumbnail(url=item_data.get('icon_url'))
    embed.set_footer(text=f"Submitted by: {interaction.user.display_name} ({interaction.user.name})") # Use display_name
    embed.add_field(name="Source", value=f"**{source_data.get('name', 'Unnamed Source')}** ({tier_name})", inline=True)
    embed.add_field(name="Points Value", value=f"**{item_data.get('points', 'N/A')}**", inline=True)
    embed.set_image(url=screenshot.url)
    return embed
    
    
    
@app_commands.command(name="submit", description="Submit an item obtained with screenshots for review.")
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source, item=autocomplete_item)
async def submit(
    interaction: discord.Interaction,
    tier: str,
    source: str,
    item: str,
    screenshot: discord.Attachment
):
    logger.info(f"Received submission from {interaction.user.id} ({interaction.user.name}) for Item: '{item}' (Source: '{source}', Tier: '{tier}') with screenshots.")
    await interaction.response.defer()

    try:
        player_clan = await get_clan_from_roles(interaction=interaction)
        if not player_clan:
            await interaction.followup.send("Could not determine your clan from your roles. Please ensure you have a valid clan role.", ephemeral=True)
            return

        template_collection = get_template_collection(player_clan)
        if template_collection is None:
            await interaction.followup.send("Could not determine your clan's template. Please contact an admin.", ephemeral=True)
            return

        template_doc_for_find = await template_collection.find_one({})
        if not template_doc_for_find:
            await interaction.followup.send(f"Template for clan '{player_clan}' not found.", ephemeral=True)
            return

        found_item_info = await _template_find_helper(template_doc_for_find, tier, source, item)

        if not found_item_info:
            await interaction.followup.send(f"Item '{item}' not found in source '{source}' ({tier}) in your clan's template. Please check the spelling or contact an admin if this is an error.", ephemeral=True)
            return

        submission_embed = await build_submission_embed(interaction, found_item_info["item"], found_item_info["source"], found_item_info["tier_name"], screenshot)
        view = SubmissionView(
            submitter_id=interaction.user.id,
            original_interaction_id=interaction.id,
            clan_of_submission=player_clan,
            tier_name=tier,
            source_name=source,
            item_name=item
        )

        await interaction.followup.send(embed=submission_embed, view=view)

    except Exception as e:
        logger.error(f"An unexpected error occurred during item submission: {e}", exc_info=True)
        await interaction.followup.send("An unexpected error occurred while processing your submission. Please try again later.", ephemeral=True)


@app_commands.command(name="precheck", description="Upload activity start or end screenshots.")
@app_commands.describe(
    action="Choose whether this is a start or end screenshot.",
    content="The type of content for the screenshot.",
    screenshot="The screenshot."
)
@app_commands.choices(content=IMAGE_UPLOAD_CHOICES)
async def precheck(
    interaction: discord.Interaction,
    action: Literal["Start", "End"],
    content: str,
    screenshot: discord.Attachment
):
    logger.info(f"Received /precheck {action} from {interaction.user.id} ({interaction.user.name}) for Content: '{content}' with screenshot.")
    await interaction.response.defer(ephemeral=False)

    try:
        url = await upload_screenshot(screenshot)
        if url is None:
            await interaction.followup.send("Failed to upload screenshot. Please try again.")
            logger.error(f"Failed to get upload URL for screenshot from {interaction.user.id}")
            return
        
        player_data = await get_player_info(interaction.user.id)
        if not player_data:
            await interaction.followup.send("User data not found. Cannot save screenshot.")
            logger.error(f"Player data not found for {interaction.user.id} during precheck.")
            return

        screenshots_list = player_data.get("screenshots", [])
        if not isinstance(screenshots_list, list):
             logger.error(f"Player {interaction.user.id} has invalid 'screenshots' field (not a list). Cannot proceed with precheck.")
             await interaction.followup.send("Error processing your data: Invalid screenshots format. Please contact an admin.", ephemeral=True)
             return

        existing_entry = None
        for entry in screenshots_list:
            if isinstance(entry, dict) and entry.get("name") == content:
                existing_entry = entry
                break

        update_successful = False
        feedback_message = "Operation failed."
        db_update_operation = None
        array_filters = None

        if action == "Start":
            if existing_entry is not None:
                feedback_message = f"A tracking entry for **{content}** already exists. Start can only be set once."
            else:
                new_entry = {
                    "name": content,
                    "start": url,
                    "end": None
                }
                db_update_operation = {"$push": {"screenshots": new_entry}}

                feedback_message = f"✅ Set starting screenshot for **{content}**."
                update_successful = True

        elif action == "End":
            if existing_entry is None or existing_entry.get("start") is None:
                 feedback_message = f"You must upload a **Start** screenshot for **{content}** before setting an End screenshot."
            else:
                 db_update_operation = {
                     "$set": {
                         "screenshots.$[elem].end": url
                     }
                 }
                 array_filters = [{"elem.name": content}]

                 feedback_message = f"✅ Set ending screenshot for **{content}**."
                 update_successful = True


        if db_update_operation:
            try:
                update_result = await player_coll.update_one(
                    {"_id": player_data["_id"]},
                    db_update_operation,
                    array_filters=array_filters if array_filters is not None else None
                )

                if update_result.acknowledged:
                    if update_result.modified_count > 0:
                         logger.info(f"Successfully updated screenshots for user {interaction.user.id} with action '{action}' for content '{content}'. Modified count: {update_result.modified_count}")
                    else:
                         logger.warning(f"Screenshots update acknowledged but modified_count was 0 for user {interaction.user.id} with action '{action}' for content '{content}'. This is expected if the state was already correct.")

                else:
                     logger.error(f"Screenshots update acknowledged was False for user {interaction.user.id} with action '{action}' for content '{content}'.")
                     feedback_message = "Database update not acknowledged. Data might not be saved."
                     update_successful = False


            except Exception as e:
                logger.error(f"Error saving screenshots for user {interaction.user.id} with action '{action}' for content '{content}': {e}", exc_info=True)
                feedback_message = "Error saving screenshot data. Please try again."
                update_successful = False

        logger.info(update_successful)
        await interaction.followup.send(feedback_message)

    except Exception as e:
        logger.error(f"An unexpected error occurred in precheck command for user {interaction.user.id}: {e}", exc_info=True)
        await interaction.followup.send("An unexpected error occurred while processing your request. Please try again.")


@app_commands.command(name="tracking", description="Set activity start or end count with a screenshot.")
@app_commands.describe(
    action="Choose whether to start or end an activity.",
    activity="The name of the activity.",
    screenshot="A screenshot verifying the count(s)."
)
@app_commands.choices(action=[
    app_commands.Choice(name="Start", value="Start"),
    app_commands.Choice(name="End", value="End"),
])
@app_commands.autocomplete(activity=autocomplete_activity)
async def tracking(
    interaction: discord.Interaction,
    action: str,
    activity: str,
    screenshot: discord.Attachment
):
    logger.info(f"Received /set_count {action} from {interaction.user.id} ({interaction.user.name}) for Activity: '{activity}' with screenshot.")

    if activity not in ACTIVITY_MODAL_MAP:
         await interaction.followup.send(f"'{activity}' is not a recognized trackable activity.", ephemeral=True)
         logger.warning(f"Player {interaction.user.id} submitted unknown activity: {activity}")
         return

    logger.info("Setting Modal Type")
    activity_modal_class = get_activity_modal_class(activity)

    if not activity_modal_class:
         logger.error(f"Could not determine modal class for activity '{activity}' from ACTIVITY_MODAL_MAP.")
         await interaction.followup.send(f"An internal error occurred. Could not find modal configuration for activity '{activity}'.", ephemeral=True)
         return

    player_document = await get_player_info(interaction.user.id)
    if not player_document:
        await interaction.followup.send("Could not retrieve player data for initial check.", ephemeral=True)
        logger.error(f"Player data not found for {interaction.user.id} during initial check for '{activity}' {action}.")
        return

    logger.info("Initializing Modal Class")
    modal = activity_modal_class(
        action=action,
        activity=activity,
        screenshot=screenshot
    )
    
    try:
        logger.info("Sending Modal...")
        await interaction.response.send_modal(modal)
    except Exception as e:
        logger.info(e)
        await interaction.response.send_message(e)
        
        
@app_commands.command(name="list_source_multipliers", description="Lists effective multipliers for each source for a given clan.")
@app_commands.describe(clan="The clan to check multipliers for (Ironfoundry or Ironclad).")
@app_commands.choices(clan=[
    app_commands.Choice(name="Ironfoundry", value="ironfoundry"),
    app_commands.Choice(name="Ironclad", value="ironclad"),
])
async def list_source_multipliers(interaction: discord.Interaction, clan: str):
    logger.info(f"Received /list_source_multipliers for clan '{clan}' from {interaction.user.id}")
    await interaction.response.defer()

    template_collection = get_template_collection(clan)
    if template_collection is None:
        logger.error(f"Could not get template collection for clan '{clan}'.")
        await interaction.followup.send(f"Error: Could not find template data for clan '{clan}'.", ephemeral=True)
        return

    template_doc = await template_collection.find_one({})
    if not template_doc:
        logger.error(f"Template document not found for clan '{clan}'.")
        await interaction.followup.send(f"Error: Template document for clan '{clan}' is missing.", ephemeral=True)
        return

    clan_multipliers = template_doc.get("multipliers", [])
    unlocked_clan_multipliers = [
        m for m in clan_multipliers if isinstance(m, dict) and m.get("unlocked", False)
    ]
    logger.debug(f"Unlocked clan multipliers for {clan}: {[m.get('name', 'Unnamed') for m in unlocked_clan_multipliers]}")


    source_multipliers_info: Dict[str, Dict[str, Any]] = {}

    tiers = template_doc.get("tiers", {})
    if isinstance(tiers, dict):
        for t_name, t_data in tiers.items():
            if isinstance(t_data, dict):
                sources = t_data.get("sources", [])
                if isinstance(sources, list):
                    for s_data in sources:
                        if isinstance(s_data, dict):
                            source_name = s_data.get("name")
                            if source_name:
                                effective_multiplier_factor = 1.0
                                applied_multiplier_names = []

                                for multiplier_data in unlocked_clan_multipliers:
                                    if does_multiplier_affect_source(multiplier_data, source_name):
                                        factor = float(multiplier_data.get("factor", 1.0))
                                        effective_multiplier_factor *= factor
                                        applied_multiplier_names.append(multiplier_data.get("name", "Unnamed"))

                                source_multipliers_info[source_name] = {
                                    "factor": round(effective_multiplier_factor, 2),
                                    "applied_by": applied_multiplier_names
                                }
                            else:
                                logger.warning(f"Source data in tier '{t_name}' is missing 'name'. Skipping.")
                        else:
                            logger.warning(f"Invalid source data in tier '{t_name}' (not a dict). Skipping.")
                else:
                    logger.warning(f"Sources field in tier '{t_name}' is not a list. Skipping.")
            else:
                logger.warning(f"Tier data for '{t_name}' is not a dict. Skipping.")
    else:
        logger.warning("Template 'tiers' field is not a dictionary. Cannot calculate source multipliers.")


    embed = Embed(
        title=f"Effective Source Multipliers for {clan.title()}",
        description="This shows the combined multiplier applied to points gained from each source, based on currently **unlocked** clan multipliers.",
        color=discord.Color.blue()
    )

    if not source_multipliers_info:
        embed.add_field(name="No Sources Found", value="Could not find any sources in the template, or no multipliers calculated.", inline=False)
    else:
        sorted_source_names = sorted(source_multipliers_info.keys())
        
        current_field_value = ""
        field_count = 0
        
        for source_name in sorted_source_names:
            info = source_multipliers_info[source_name]
            multiplier_text = f"**{info['factor']}x**"
            if info['applied_by']:
                multiplier_text += f" (by: {', '.join(info['applied_by'])})"
            
            line = f"- {source_name}: {multiplier_text}\n"
            
            if len(current_field_value) + len(line) > 1000:
                embed.add_field(
                    name=f"Source Multipliers ({field_count + 1})",
                    value=current_field_value,
                    inline=False
                )
                current_field_value = line
                field_count += 1
            else:
                current_field_value += line
        
        if current_field_value:
            embed.add_field(
                name=f"Source Multipliers ({field_count + 1})" if field_count > 0 else "Source Multipliers",
                value=current_field_value,
                inline=False
            )

    embed.set_author(name=interaction.guild.name if interaction.guild else "Server")

    await interaction.followup.send(embed=embed)
    
@app_commands.command(name="status", description="Shows your currently open activity tracking and precheck listings.")
async def status(interaction: discord.Interaction):
    logger.info(f"Received /status from {interaction.user.id} ({interaction.user.name})")
    await interaction.response.defer(ephemeral=True) # Defer ephemerally for privacy

    player_doc = await get_player_info(interaction.user.id)
    if not player_doc:
        await interaction.followup.send("Could not find your player data. Please contact an admin if this persists.", ephemeral=True)
        return

    open_tracking_entries: List[str] = []
    open_precheck_entries: List[str] = []


    tracking_entries = player_doc.get("tracking", [])
    if isinstance(tracking_entries, list):
        for entry in tracking_entries:
            if isinstance(entry, dict) and entry.get("name"):
                start_data = entry.get("start")
                end_data = entry.get("end")

                # An entry is "open" if a 'start' exists AND the 'end' object is missing OR its screenshot field is empty
                if start_data and \
                   (end_data is None or (isinstance(end_data, dict) and end_data.get("screenshot") == "")):
                    
                    activity_name = entry["name"]
                    start_values = start_data.get("values", {})
                    # Add sanity check for values being dict
                    start_display = ""
                    if isinstance(start_values, dict) and start_values:
                         start_display = ", ".join([f"{k}: {v}" for k, v in start_values.items()])
                    else:
                         start_display = "No start values recorded"


                    open_tracking_entries.append(f"- **{activity_name}** (Started with: {start_display})")
                else:
                    # Log if it's considered completed or malformed
                    if start_data and end_data and isinstance(end_data, dict) and end_data.get("screenshot"):
                        logger.debug(f"Tracking entry '{entry.get('name')}' is completed for user {interaction.user.id}.")
                    else:
                        logger.debug(f"Tracking entry '{entry.get('name')}' for user {interaction.user.id} not considered open (no start or malformed).")
            else:
                logger.warning(f"Malformed entry found in 'tracking' array for user {interaction.user.id}: {entry}")
    else:
        logger.warning(f"Player {interaction.user.id} has 'tracking' field that is not a list: {tracking_entries}")


    # --- Check /precheck entries (in the 'screenshots' array) ---
    screenshots_entries = player_doc.get("screenshots", [])
    if isinstance(screenshots_entries, list):
        for entry in screenshots_entries:
            # Ensure entry is a dictionary and has a name
            if isinstance(entry, dict) and entry.get("name"):
                start_url = entry.get("start")
                end_url = entry.get("end")

                if start_url is not None and end_url is None:
                    content_name = entry["name"]
                    open_precheck_entries.append(f"- **{content_name}** (Start URL: [link]({start_url}))")
                else:
                    if start_url is not None and end_url is not None:
                        logger.debug(f"Precheck entry '{entry.get('name')}' is completed for user {interaction.user.id}.")
                    else:
                         logger.debug(f"Precheck entry '{entry.get('name')}' for user {interaction.user.id} not considered open (no start or malformed).")
            else:
                logger.warning(f"Malformed entry found in 'screenshots' array for user {interaction.user.id}: {entry}")
    else:
        logger.warning(f"Player {interaction.user.id} has 'screenshots' field that is not a list: {screenshots_entries}")


    embed = Embed(
        title=f"{interaction.user.display_name}'s Open Tracking & Precheck Listings",
        color=discord.Color.dark_purple()
    )

    if not open_tracking_entries and not open_precheck_entries:
        embed.description = "You have no active tracking or precheck listings. Use `/tracking Start` or `/precheck Start` to begin!"
    else:
        if open_tracking_entries:
            embed.add_field(
                name="📊 Open Activity Tracking (`/tracking`):",
                value="\n".join(open_tracking_entries),
                inline=False
            )
        # Only add field if there are actual entries
        if open_precheck_entries:
            embed.add_field(
                name="📸 Open Prechecks (`/precheck`):",
                value="\n".join(open_precheck_entries),
                inline=False
            )

    embed.set_footer(text="To complete an entry, use /tracking End or /precheck End with the respective activity/content.")
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)

    await interaction.followup.send(embed=embed)

    
def setup(client: discord.Client, mongo_client: AsyncMongoClient | None):
    if mongo_client == None:
        return
    global mongo, db, if_coll, ic_coll, template_coll, player_coll
    mongo = mongo_client
    db = mongo["Frenzy"]
    if_coll = db["ironfoundry"]
    ic_coll = db["ironclad"]
    template_coll = db["Templates"]
    player_coll = db["Players"]
    #client.tree.add_command(list_source_multipliers, guild=client.selected_guild)
    #client.tree.add_command(tracking, guild=client.selected_guild)
    client.tree.add_command(submit, guild=client.selected_guild) # type: ignore
    #client.tree.add_command(precheck, guild=client.selected_guild)
    #client.tree.add_command(status, guild=client.selected_guild)