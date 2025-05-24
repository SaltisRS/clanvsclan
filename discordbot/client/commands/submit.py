import math
from typing import Any, Dict, List, Optional, Tuple
import discord
import os


from loguru import logger
from dotenv import load_dotenv
from discord import Embed, app_commands
from pymongo import AsyncMongoClient
from cachetools import TTLCache


IC_roleid = 1343921208948953128
If_roleid = 1343921101687750716
ICPERM = [1369428787342737488, 1369428819907448832]
IFPERM = [1369428706161852436, 1369428754773840082]
load_dotenv()
mongo = AsyncMongoClient(host=os.getenv("MONGO_URI"))
autocomplete_cache = TTLCache(maxsize=512, ttl=30)
db = mongo["Frenzy"]
if_coll = db["ironfoundry"]
ic_coll = db["ironclad"]
template_coll = db["Templates"]
player_coll = db["Players"]

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

async def calculate_points():
    ...

async def get_clan_from_roles(interaction: discord.Interaction):
    for role in interaction.user.roles:
        if role.id == If_roleid:
            return "ironfoundry"
        if role.id == IC_roleid:
            return "ironclad"

    return None


    
async def find_item_in_template_doc(template_doc: Dict[str, Any], tier_name: str, source_name: str, item_name: str) -> Optional[Dict[str, Any]]:
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

def calculate_points_gained_from_this_submission(
    item_template_data: Dict[str, Any],
    old_obtained_count: int, # obtained count BEFORE this submission
    new_obtained_count: int  # obtained count AFTER this submission (old_obtained_count + 1)
) -> float:
    """
    Calculates points gained from THIS specific submission,
    considering unique, half-unique, and one-time duplicate set points,
    without relying on database flags for awarded points.
    """
    points_gained_now = 0.0
    base_points = float(item_template_data.get("points", 0))
    duplicate_item_points = float(item_template_data.get("duplicate_points", 0))
    unique_required = int(item_template_data.get("required", 1))
    # How many additional items are needed for the first duplicate set after unique
    duplicate_items_for_set = int(item_template_data.get("duplicate_required", 1))

    if unique_required <= 0: unique_required = 1
    if duplicate_items_for_set <= 0: duplicate_items_for_set = 1

    half_unique_threshold = math.ceil(unique_required / 2)
    unique_threshold = unique_required
    first_duplicate_set_threshold = unique_required + duplicate_items_for_set

    # Check for Half Unique Points
    # Awarded if this submission crosses the half_unique_threshold but not yet the unique_threshold
    if old_obtained_count < half_unique_threshold and new_obtained_count >= half_unique_threshold:
        points_gained_now += base_points / 2
        logger.debug(f"Awarding half unique points for {item_template_data['name']}")

    # Check for Full Unique Points
    # Awarded if this submission crosses the unique_threshold
    if old_obtained_count < unique_threshold and new_obtained_count >= unique_threshold:
        # If half points were just awarded in this same transaction, only add the remaining half
        if new_obtained_count >= half_unique_threshold and old_obtained_count < half_unique_threshold : # Check if half was just crossed
            points_gained_now += base_points / 2 # Add the other half
        else: # Otherwise, if half was crossed previously or not applicable, award full points
            points_gained_now += base_points
        logger.debug(f"Awarding full unique points for {item_template_data['name']}")


    # Check for First Duplicate Set Points
    # Awarded if this submission crosses the first_duplicate_set_threshold
    if old_obtained_count < first_duplicate_set_threshold and new_obtained_count >= first_duplicate_set_threshold:
        points_gained_now += duplicate_item_points
        logger.debug(f"Awarding first duplicate set points for {item_template_data['name']}")

    return points_gained_now

# --- Function to calculate total points an item contributes based on its current obtained count (No DB Flags) ---
def get_total_points_for_item_no_flags(item_data: Dict[str, Any]) -> float:
    """
    Calculates the total points an item should contribute based on its current 'obtained' count,
    without relying on database flags.
    """
    total_item_points = 0.0
    current_obtained = int(item_data.get("obtained", 0))
    base_points = float(item_data.get("points", 0))
    duplicate_item_points = float(item_data.get("duplicate_points", 0))
    unique_required = int(item_data.get("required", 1))
    duplicate_items_for_set = int(item_data.get("duplicate_required", 1))

    if unique_required <= 0: unique_required = 1
    if duplicate_items_for_set <= 0: duplicate_items_for_set = 1

    half_unique_threshold = math.ceil(unique_required / 2)
    unique_threshold = unique_required
    first_duplicate_set_threshold = unique_required + duplicate_items_for_set

    # Points from unique obtainment
    if current_obtained >= unique_threshold:
        total_item_points += base_points
    elif current_obtained >= half_unique_threshold: # Only half points if unique not fully met
        total_item_points += base_points / 2

    # Points from the first duplicate set
    if current_obtained >= first_duplicate_set_threshold:
        total_item_points += duplicate_item_points

    return total_item_points


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


    # --- Refactored Helper Methods for accept_button ---
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

    def _recalculate_template_points(self, template_doc: Dict[str, Any]):
        """Recalculates aggregated points in the template document."""
        template_doc["total_gained"] = 0.0
        for t_data in template_doc.get("tiers", {}).values():
            t_data["points_gained"] = 0.0
            for s_data in t_data.get("sources", []):
                s_data["source_gained"] = 0.0
                for i_data in s_data.get("items", []):
                    item_total_points = get_total_points_for_item_no_flags(i_data)
                    s_data["source_gained"] += item_total_points
                t_data["points_gained"] += s_data["source_gained"]
            template_doc["total_gained"] += t_data["points_gained"]
        logger.info(f"Template: Recalculated total_gained to {template_doc['total_gained']} for clan '{self.clan_of_submission}'.")

    async def _update_player_data(self, player_document: Dict[str, Any], points_gained_this_submission: float, new_obtained_count_template: int):
        """Updates the player's total points and their obtained items record."""
        player_document["total_gained"] = float(player_document.get("total_gained", 0.0)) + points_gained_this_submission
        logger.info(f"Player {self.submitter_id}: Updated total_gained to {player_document['total_gained']}.")

        player_obtained_items = player_document.get("obtained_items", {})
        item_key = f"{self.tier_name}.{self.source_name}.{self.item_name}"
        player_obtained_items[item_key] = player_obtained_items.get(item_key, 0) + 1 # Increment player's count for this item
        player_document["obtained_items"] = player_obtained_items
        logger.debug(f"Player {self.submitter_id}: Updated obtained_items for '{item_key}' to count {player_obtained_items[item_key]}.")


        if "submissions" not in player_document: player_document["submissions"] = []
        player_document["submissions"].append({
            "item": self.item_name, "source": self.source_name, "tier": self.tier_name,
            "status": "accepted", "accepted_by": self.original_interaction_id, # Or interaction.user.id if interaction is passed
            "timestamp": discord.utils.utcnow(), "points_awarded": points_gained_this_submission
        })

    async def _send_acceptance_feedback(self, interaction: discord.Interaction, button: discord.ui.Button, points_gained: float, player_total_points: float):
        """Sends feedback messages and disables buttons."""
        button.disabled = True
        button.label = "Accepted"
        if len(self.children) > 1 and isinstance(self.children[1], discord.ui.Button): # Check if deny button exists
            self.children[1].disabled = True
            self.children[1].label = "Accepted"
        await interaction.message.edit(view=self) # type: ignore

        await interaction.followup.send(
            f"Submission for '{self.item_name}' by <@{self.submitter_id}> accepted by {interaction.user.mention}.\n"
            f"Points Gained from this submission: {points_gained:.2f}\n"
            f"Submitter's New Total Points: {player_total_points:.2f}",
            ephemeral=True
        )
        submitter_user = interaction.client.get_user(self.submitter_id)
        if submitter_user:
            try:
                await submitter_user.send(f"Your submission for '{self.item_name}' has been accepted! You gained {points_gained:.2f} points.")
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
        item_info = await find_item_in_template_doc(template_doc, self.tier_name, self.source_name, self.item_name)
        if not item_info:
            await interaction.followup.send(f"Error: Item '{self.item_name}' no longer found in template.", ephemeral=True)
            return
        item_template_data = item_info["item"]

        # 3. Check for Rejection
        old_obtained_count_template = int(item_template_data.get("obtained", 0))
        if await self._check_submission_rejection(item_template_data, old_obtained_count_template):
            button.disabled = True
            if len(self.children) > 1 and isinstance(self.children[1], discord.ui.Button): self.children[1].disabled = True
            await interaction.message.edit(view=self) # type: ignore
            await interaction.followup.send(
                f"Submission for '{self.item_name}' by <@{self.submitter_id}> rejected by {interaction.user.mention}.\n"
                f"Reason: Item has already reached its maximum point award threshold.",
                ephemeral=False
            )
            # DM logic for rejection can be added here too
            return

        # 4. Update Item Obtained Count
        new_obtained_count_template = self._update_item_obtained_count(item_template_data)

        # 5. Calculate Points Gained from This Submission
        points_gained_this_submission = calculate_points_gained_from_this_submission(
            item_template_data, old_obtained_count_template, new_obtained_count_template
        )

        # 6. Recalculate Template Points
        self._recalculate_template_points(template_doc)

        # 7. Update Player Data
        await self._update_player_data(player_document, points_gained_this_submission, new_obtained_count_template)

        # 8. Save Changes to DB
        template_replace_result = await template_collection.replace_one({"_id": template_doc["_id"]}, template_doc)
        player_update_result = await player_coll.replace_one({"_id": player_document["_id"]}, player_document)

        # 9. Send Feedback
        if template_replace_result.modified_count > 0 and player_update_result.modified_count > 0:
            await self._send_acceptance_feedback(interaction, button, points_gained_this_submission, player_document["total_gained"])
        else:
            await interaction.followup.send("Error: Failed to save updates to the database.", ephemeral=True)
            logger.error(f"DB update failed on accept. Template mod: {template_replace_result.modified_count}, Player mod: {player_update_result.modified_count}")
    
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
    interaction: discord.Interaction, # Pass the original interaction for user info
    item_data: Dict[str, Any],
    source_data: Dict[str, Any],
    tier_name: str,
    screenshot: discord.Attachment
) -> discord.Embed:
    """Builds the embed for submitting an item for review."""
    embed = Embed(
        title=item_data.get("name", "Unnamed Item")
    )
    embed.set_thumbnail(url=item_data.get('icon_url')) # Use item icon for thumbnail
    embed.set_footer(text=f"Submitted by: {interaction.user.display_name} ({interaction.user.name})") # Use display_name
    embed.add_field(name="Source", value=f"**{source_data.get('name', 'Unnamed Source')}** ({tier_name})", inline=True)
    embed.add_field(name="Points Value", value=f"**{item_data.get('points', 'N/A')}**", inline=True)
    embed.set_image(url=screenshot.url) # Screenshot as main image
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
    # ... (initial logging and defer as before) ...
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

        # Fetch template once to pass to find_item_in_template_doc
        template_doc_for_find = await template_collection.find_one({})
        if not template_doc_for_find:
            await interaction.followup.send(f"Template for clan '{player_clan}' not found.", ephemeral=True)
            return

        found_item_info = await find_item_in_template_doc(template_doc_for_find, tier, source, item)

        if not found_item_info:
            await interaction.followup.send(f"Item '{item}' not found in source '{source}' ({tier}) in your clan's template. Please check the spelling or contact an admin if this is an error.", ephemeral=True)
            return

        submission_embed = await build_submission_embed(interaction, found_item_info["item"], found_item_info["source"], found_item_info["tier_name"], screenshot)
        view = SubmissionView(
            submitter_id=interaction.user.id,
            original_interaction_id=interaction.id,
            clan_of_submission=player_clan,
            tier_name=tier, # Use the tier from the command
            source_name=source,
            item_name=item
        )

        await interaction.followup.send(embed=submission_embed, view=view)

    except Exception as e:
        logger.error(f"An unexpected error occurred during item submission: {e}", exc_info=True)
        await interaction.followup.send("An unexpected error occurred while processing your submission. Please try again later.", ephemeral=True)
    
    
def setup(client: discord.Client):
    client.tree.add_command(submit, guild=client.selected_guild) # type: ignore