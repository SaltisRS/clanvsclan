from typing import Any, Dict, List, Optional
import discord
import os


from loguru import logger
from dotenv import load_dotenv
from discord import Embed, app_commands
from pymongo import AsyncMongoClient
from cachetools import TTLCache



IRONCLAD = ""
IRONFOUNDRY = ""
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

def get_template_collection(clan: str) -> AsyncMongoClient.collection:
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
        if role == IRONFOUNDRY:
            return "ironfoundry"
        elif role == IRONCLAD:
            return "ironclad"

    
async def find_item_in_template(collection, tier_name: str, source_name: str, item_name: str) -> Optional[Dict[str, Any]]:
    """Finds an item's data in a template collection based on tier, source, and item name."""
    try:
        template = await collection.find_one({}) # Assuming one template document per collection
        if not template:
            return None

        tiers = template.get("tiers", {})
        tier_data = tiers.get(tier_name) # Get the specific tier data

        if not tier_data:
            return None # Tier not found

        sources = tier_data.get("sources", [])
        for source_data in sources:
            if source_data.get("name") == source_name: # Match source name
                items = source_data.get("items", [])
                for item_data in items:
                    if item_data.get("name") == item_name: # Match item name
                        # Return the item data, source data, and tier name for context
                        return {"item": item_data, "source": source_data, "tier": tier_data, "tier_name": tier_name}

        return None # Item or source not found within the specified tier
    except Exception as e:
        logger.error(f"Error finding item '{item_name}' in source '{source_name}' ({tier_name}) in collection {collection.name}: {e}", exc_info=True)
        return None
    
    
    
async def build_submission_embed(
    interaction: discord.Interaction,
    found_item_info: Dict[str, Any],
    screenshot: discord.Attachment
) -> discord.Embed:
    """Builds the embed for submitting an item for review."""
    item_data = found_item_info["item"]
    source_data = found_item_info["source"]
    tier_name = found_item_info["tier_name"]

    embed = Embed(
        title=item_data.get("name", "Unnamed Item")
    )

    embed.set_thumbnail(url=item_data.get('icon_url'))
    embed.set_footer(text=f"Submitted by: {interaction.user.mention}")
    embed.add_field(name="Source", value=f"**{source_data.get('name', 'Unnamed Source')}** ({tier_name})", inline=True)
    embed.add_field(name="Points Value", value=f"**{item_data.get('points', 'N/A')}**", inline=True)
    embed.set_image(url=screenshot.url)
    
    return embed

async def get_permission(interaction: discord.Interaction):
    for role in interaction.user.roles:
        if role.id in IFPERM:
            return "ironfoundry"
        elif role.id in ICPERM:
            return "ironclad"
    return None
    
class SubmissionView(discord.ui.View):
     
    def __init__(self, template, tier, source, item, clan):
        super().__init__(timeout=None)
        self.template = template
        self.tier = tier
        self.source = source
        self.item = item
        self.clan = clan
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green) # type: ignore
    async def accept_button(self, interaction: discord.Interaction, button: discord.Button):
        user_perm = await get_permission(interaction)
        if user_perm != self.clan:
            await interaction.response.send_message("You do not have permission to approve this.", ephemeral=True)
            return
        await interaction.response.send_message("Approved!")
    
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red) # type: ignore
    async def deny_button(self, interaction: discord.Interaction, button: discord.Button):
        user_perm = await get_permission(interaction)
        if user_perm != self.clan:
            await interaction.response.send_message("You do not have permission to approve this.", ephemeral=True)
            return
        await interaction.response.send_message("Denied!")
    
    
@app_commands.command(name="submit", description="Submit an item obtained with screenshots for review.")
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source, item=autocomplete_item) # Assuming these still rely on tier parameter
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
        # 1. Get Clan Information
        player_clan = await get_clan_from_roles(interaction=interaction)
        if not player_clan:
            await interaction.followup.send("Could not determine your clan from your roles. Please ensure you have a valid clan role.", ephemeral=True)
            logger.warning(f"Clan role not found for user {interaction.user.id}.")
            return

        # 2. Determine Target Template Collection
        template_collection = get_template_collection(player_clan)
        if not template_collection:
            await interaction.followup.send("Could not determine your clan's template. Please contact an admin.", ephemeral=True)
            logger.error(f"Could not get template collection for clan '{player_clan}'.")
            return

        # 3. Find the Item in the Template (using provided tier, source, item)
        found_item_info = await find_item_in_template(template_collection, tier, source, item)

        if not found_item_info:
            await interaction.followup.send(f"Item '{item}' not found in source '{source}' ({tier}) in your clan's template. Please check the spelling or contact an admin if this is an error.", ephemeral=True)
            logger.warning(f"Submitted item '{item}' not found in source '{source}' ({tier}) for clan '{player_clan}'.")
            return

        # 4. Build the Embed
        submission_embed = await build_submission_embed(interaction, found_item_info, screenshot)
        view = SubmissionView(template_collection, tier, source, item, player_clan)
        
        await interaction.followup.send(embed=submission_embed, view=view)


    except Exception as e:
        logger.error(f"An unexpected error occurred during item submission: {e}", exc_info=True)
        await interaction.followup.send("An unexpected error occurred while processing your submission. Please try again later.", ephemeral=True)
    