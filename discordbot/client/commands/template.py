import discord
import os

from loguru import logger
from discord import app_commands
from cachetools import TTLCache
from typing import Optional
from pymongo import AsyncMongoClient
from dotenv import load_dotenv

from .groups.template import TemplateGroup


load_dotenv()
group = TemplateGroup()
mongo = AsyncMongoClient(host=os.getenv("MONGO_URI"))
db = mongo["Frenzy"]
coll = db["Templates"]
gallery = db["Gallery"]
autocomplete_cache = TTLCache(maxsize=512, ttl=30)


async def autocomplete_tier(interaction: discord.Interaction, current: str):
    if "tiers" not in autocomplete_cache:
        template = await coll.find_one({})
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
        template = await coll.find_one({})
        if not template or tier not in template.get("tiers", {}):
            return []

        sources = template["tiers"][tier].get("sources", [])
        autocomplete_cache[cache_key] = [source["name"] for source in sources]

    return [
        discord.app_commands.Choice(name=source, value=source)
        for source in autocomplete_cache[cache_key]
        if current.lower() in source.lower()
    ][:25]

async def autocomplete_multiplier(interaction: discord.Interaction, current: str):
    tier = getattr(interaction.namespace, "tier", None)
    source = getattr(interaction.namespace, "source", None)
    if not tier or not source:
        return []

    cache_key = f"multipliers_{tier}_{source}"
    if cache_key not in autocomplete_cache:
        template = await coll.find_one({})
        if not template or tier not in template.get("tiers", {}):
            return []

        sources = template["tiers"][tier].get("sources", [])
        source_data = next((s for s in sources if s["name"] == source), None)
        if not source_data:
            return []

        multipliers = [m["name"] for m in source_data.get("multipliers", [])]
        autocomplete_cache[cache_key] = multipliers

    return [
        discord.app_commands.Choice(name=multiplier, value=multiplier)
        for multiplier in autocomplete_cache[cache_key]
        if current.lower() in multiplier.lower()
    ][:25]


async def autocomplete_item(interaction: discord.Interaction, current: str):
    tier = getattr(interaction.namespace, "tier", None)
    source = getattr(interaction.namespace, "source", None)
    if not tier or not source:
        return []

    cache_key = f"items_{tier}_{source}"
    if cache_key not in autocomplete_cache:
        template = await coll.find_one({})
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

@group.command()
async def refresh_cache(interaction: discord.Interaction):
    global autocomplete_cache
    autocomplete_cache.clear()  # Clear existing cache

    template = await coll.find_one({})
    if not template:
        await interaction.response.send_message("Template not found.", ephemeral=True)
        return

    # Rebuild the cache from scratch
    autocomplete_cache["tiers"] = list(template.get("tiers", {}).keys())

    for tier_name, tier_data in template.get("tiers", {}).items():
        sources = tier_data.get("sources", [])
        autocomplete_cache[f"sources_{tier_name}"] = [source["name"] for source in sources]

        for source in sources:
            autocomplete_cache[f"items_{tier_name}_{source['name']}"] = [
                item["name"] for item in source.get("items", [])
            ]

    await interaction.response.send_message("Autocomplete cache refreshed.", ephemeral=True)

@group.command()
async def get_tiers(interaction: discord.Interaction):
    template = await coll.find_one({})

    if not template:
        await interaction.response.send_message("Template not found.")
        return

    tiers = template.get("tiers", {})
    tier_list = "\n".join([f"**{tier}**" for tier in tiers.keys()])
    await interaction.response.send_message(f"**Tiers**\n{tier_list}")

@group.command()
@app_commands.autocomplete(tier=autocomplete_tier)
async def get_sources_simple(interaction: discord.Interaction, tier: str):
    template = await coll.find_one({})

    if not template:
        await interaction.response.send_message("Template not found.")
        return

    sources = template.get("tiers", {}).get(tier, {}).get("sources", [])
    source_list = "\n".join([f"**{source['name']}**" for source in sources])
    await interaction.response.send_message(f"**Sources**\n{source_list}")
    

@group.command()
@app_commands.autocomplete(tier=autocomplete_tier)
async def get_sources_detailed(interaction: discord.Interaction, tier: str):
    logger.info(f"Command triggered: get_sources_detailed | Tier: {tier}")

    try:
        template = await coll.find_one({})
        if not template:
            logger.warning("Template not found.")
            await interaction.response.send_message("Template not found.")
            return

        sources = template.get("tiers", {}).get(tier, {}).get("sources", [])
        logger.info(f"Found {len(sources)} sources for tier: {tier}")

        embed = discord.Embed(title=f"Sources for {tier}")

        #colors = ["\u001b[0;31m", "\u001b[0;32m", "\u001b[0;33m"]  # Red, Green, Yellow
        reset = "\u001b[0m"

        for source in sources:
            logger.debug(f"Processing source: {source['name']}")

            multipliers = "\n".join([f"{m['name']} (x{m['factor']:.2f})" for m in source.get("multipliers", [])])
            items_list = source.get("items", [])

            logger.debug(f"Multipliers: {multipliers if multipliers else 'None'}")
            logger.debug(f"Found {len(items_list)} items for {source['name']}")

            # Alternate ANSI colors based on obtained/duplicate_obtained flags
            items_formatted = "\n".join(
                f"{get_item_color(item)}{item['name']} ({item['points']}){reset}"
                for item in items_list
            ) if items_list else "None"

            embed.add_field(
                name=source["name"],
                value=f">>> __Multipliers__\n`{multipliers if multipliers else 'None'}`\n__Items__\n```ansi\n{items_formatted}\n```",
                inline=False
            )

        logger.info("Attempting to send embed response...")
        await interaction.response.send_message(embed=embed)
        logger.success("Embed sent successfully!")

    except Exception as e:
        logger.error(f"Failed to send embed: {e}")
        await interaction.response.send_message("An error occurred while generating the embed.")


def get_item_color(item):
    """Returns the appropriate color based on obtained/duplicate_obtained flags."""
    if item.get("obtained") and item.get("duplicate_obtained"):
        return "\u001b[0;32m"  # Green
    elif item.get("obtained") and not item.get("duplicate_obtained"):
        return "\u001b[0;33m"  # Yellow
    else:
        return "\u001b[0;31m"  # Red





@group.command()
async def add_tier(interaction: discord.Interaction, name: str):
    template = await coll.find_one({})
    
    if not template:
        await interaction.response.send_message("Template not found.")
        return

    tier = {
        name: {
            "points_gained": 0,
            "sources": []
        }
    }

    result = await coll.update_one(
        {"_id": template["_id"]},
        {"$set": {f"tiers.{name}": tier[name]}}
    )

    if result.modified_count > 0:
        await interaction.response.send_message(f"Tier `{name}` added.")
    else:
        await interaction.response.send_message("Tier could not be added.")
        

@group.command()
@app_commands.autocomplete(tier=autocomplete_tier)
async def add_source(interaction: discord.Interaction, tier: str, source: str):
    template = await coll.find_one({})
    
    if not template:
        await interaction.response.send_message("Template not found.")
        return

    source_data = {
        "name": source,
        "source_gained": 0,
        "multipliers": [],
        "items": []
    }

    result = await coll.update_one(
        {"_id": template["_id"]},
        {"$push": {f"tiers.{tier}.sources": source_data}}
    )

    if result.modified_count > 0:
        await interaction.response.send_message(f"Source `{source}` added to `{tier}` tier.")
    else:
        await interaction.response.send_message("Tier not found.")

@group.command()
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source)
async def add_multiplier(interaction: discord.Interaction, tier: str, source: str, name: str, factor: float, required_items: str):
    template = await coll.find_one({})
    
    if not template:
        await interaction.response.send_message("Template not found.")
        return

    multiplier = {
        "name": name,
        "factor": factor,
        "required_items": required_items.split(","),
        "unlocked": False
    }

    result = await coll.update_one(
        {"_id": template["_id"], f"tiers.{tier}.sources.name": source},
        {"$push": {f"tiers.{tier}.sources.$.multipliers": multiplier}}
    )

    if result.modified_count > 0:
        await interaction.response.send_message(f"Multiplier `{name}` added to `{source}` in `{tier}` tier.")
    else:
        await interaction.response.send_message("Tier or source not found.")

    
@group.command()
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source)
async def add_item(interaction: discord.Interaction, tier: str, source: str, name: str, points: float, icon_url: Optional[str] = None):
    template = await coll.find_one({})
    
    if not template:
        await interaction.response.send_message("Template not found.")
        return

    item = {
        "name": name,
        "points": points,
        "duplicate_points": points / 2 if points != 0 else 0,
        "obtained": False,
        "duplicate_obtained": False,
        "icon_url": icon_url
    }

    result = await coll.update_one(
        {"_id": template["_id"], f"tiers.{tier}.sources.name": source},
        {"$push": {f"tiers.{tier}.sources.$.items": item}}
    )

    if result.modified_count > 0:
        await interaction.response.send_message(f"Item `{name}` added to `{source}` in `{tier}` tier.")
    else:
        await interaction.response.send_message("Tier or source not found.")
from loguru import logger


@group.command()
@app_commands.autocomplete(
    tier=autocomplete_tier,
    target_tier=autocomplete_tier,
    source=autocomplete_source,
)
async def move_source(
    interaction: discord.Interaction,
    tier: str,
    target_tier: str,
    source: str,
):
    """Moves a Source from one tier to another."""
    logger.info(
        f"Attempting to move source '{source}' from tier '{tier}' to tier '{target_tier}'"
    )

    if tier == target_tier:
        await interaction.response.send_message(
            "Original tier and target tier cannot be the same."
        )
        return

    # Fetch the entire document
    template = await coll.find_one({})

    if not template:
        logger.warning("Template document not found in the collection.")
        await interaction.response.send_message("Template not found.")
        return

    try:
        tier_data = template.get("tiers", {}).get(tier)
        target_tier_data = template.get("tiers", {}).get(target_tier)

        if not tier_data:
            logger.warning(f"Original tier '{tier}' not found in the template.")
            await interaction.response.send_message(
                f"Original tier `{tier}` not found."
            )
            return

        if not target_tier_data:
            logger.warning(f"Target tier '{target_tier}' not found in the template.")
            await interaction.response.send_message(
                f"Target tier `{target_tier}` not found."
            )
            return

        original_sources = tier_data.get("sources", [])
        target_sources = target_tier_data.get("sources", [])

        source_to_move = None
        source_index_to_remove = -1

        # Find the source in the original tier
        for i, source_data in enumerate(original_sources):
            if source_data.get("name") == source:
                source_to_move = source_data
                source_index_to_remove = i
                break

        if source_to_move is None:
            logger.warning(
                f"Source '{source}' not found in original tier '{tier}'."
            )
            await interaction.response.send_message(
                f"Source `{source}` not found in original tier `{tier}`."
            )
            return

        # Check if a source with the same name already exists in the target tier
        for source_data in target_sources:
            if source_data.get("name") == source:
                logger.warning(
                    f"Source '{source}' already exists in target tier '{target_tier}'."
                )
                await interaction.response.send_message(
                    f"Source `{source}` already exists in target tier `{target_tier}`."
                )
                return

        # Remove the source from the original tier's sources list in memory
        original_sources.pop(source_index_to_remove)
        logger.info(f"Removed source '{source}' from original tier in memory.")

        # Add the source to the target tier's sources list in memory
        target_sources.append(source_to_move)
        logger.info(f"Added source '{source}' to target tier in memory.")

        # Replace the entire document in the database with the modified one
        replace_result = await coll.replace_one({"_id": template["_id"]}, template)

        if replace_result.modified_count > 0:
            logger.info(
                f"Successfully moved source '{source}' from '{tier}' to '{target_tier}'."
            )
            await interaction.response.send_message(
                f"Source `{source}` moved from `{tier}` to `{target_tier}`."
            )
        else:
            logger.warning(
                "Replace operation did not modify the document during source move. Document might have changed or been deleted."
            )
            await interaction.response.send_message(
                "Could not move the source (replace failed)."
            )

    except Exception as e:
        logger.error(
            f"An error occurred while attempting to move source '{source}': {e}",
            exc_info=True,
        )
        await interaction.response.send_message(
            "An error occurred while trying to move the source."
        )

@group.command()
async def molebor(interaction: discord.Interaction):
    await interaction.response.send_message("https://tenor.com/view/gnomed-gnome-glow-effect-shaking-gif-17863812")


@group.command()
#@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source)
async def add(interaction: discord.Interaction, identifier: str,
              t1_value: int, t1_points: float,
              t2_value: int, t2_points: float,
              t3_value: int, t3_points: float,
              t4_value: int, t4_points: float):
    await interaction.response.send_message("NOT IMPLEMENTED")
    
@group.command()
async def add_pet(interaction: discord.Interaction, pet: str, points: float):
    await interaction.response.send_message("NOT IMPLEMENTED")
    
@group.command()
@app_commands.autocomplete(tier=autocomplete_tier)
async def missing_icons(interaction: discord.Interaction, tier: str):
    
    item_list = list()
    template = coll.find({})
    
    if not template:
        await interaction.response.send_message("Template not found")
        
    try:
        tier_data = await template.get("tiers", {}).get(tier)
        source_data = tier_data.get("sources", [])
        
    except Exception as e:
        await interaction.response.send_message(e)
    
    for source in source_data:
        for item in source["Items"]:
            if item["icon_url"] is None or "":
                item_list.append(f"{item["name"]}: Missing IconURL\n")
            else:
                continue
    
    await interaction.response.send_message(item_list)
    
    
    
@group.command()
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source, item=autocomplete_item)
async def upload_item_icon(interaction: discord.Interaction, tier: str, source: str, item: str, icon_link: str):
    logger.info(
        f"Attempting to upload icon for item '{item}' in source '{source}' ({tier}) with URL: {icon_link}"
    )

    template = await coll.find_one({})

    if not template:
        logger.warning("Template document not found in the collection.")
        await interaction.response.send_message("Template not found.")
        return

    try:
        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template.")
            await interaction.response.send_message(f"Tier `{tier}` not found.")
            return

        source_found = False
        item_found = False

        for source_data in tier_data.get("sources", []):
            if source_data.get("name") == source:
                source_found = True
                for item_data in source_data.get("items", []):
                    if item_data.get("name") == item:
                        item_found = True
                        item_data["icon_url"] = icon_link
                        logger.info(f"Modified item '{item}' in memory.")
                        break  # Item found and modified, no need to check other items

                if source_found and item_found:
                    break  # Source and item found, no need to check other sources

        if source_found and item_found:
            replace_result = await coll.replace_one({"_id": template["_id"]}, template)

            if replace_result.modified_count > 0:
                logger.info(
                    f"Successfully replaced document with updated item icon for '{item}'."
                )
                await interaction.response.send_message(
                    f"Icon for item `{item}` in `{source}` ({tier}) updated/added successfully."
                )
            else:
                logger.warning(
                    "Replace operation did not modify the document. Document might have changed or been deleted."
                )
                await interaction.response.send_message(
                    "Could not update the item icon (replace failed)."
                )
        else:
            if not source_found:
                logger.warning(
                    f"Source '{source}' not found within tier '{tier}'."
                )
                await interaction.response.send_message(
                    f"Source `{source}` not found within tier `{tier}`."
                )
            elif not item_found:
                 logger.warning(
                    f"Item '{item}' not found within source '{source}' in tier '{tier}'."
                )
                 await interaction.response.send_message(
                    f"Item `{item}` not found within source `{source}` in tier `{tier}`."
                )
            else:
                # Should not reach here if logic is correct, but as a fallback
                 logger.warning("Could not find the specified tier, source, or item (general failure).")
                 await interaction.response.send_message("Could not find the specified tier, source, or item.")


    except Exception as e:
        logger.error(
            f"An error occurred while attempting to update item icon in memory or replace the document for '{item}': {e}",
            exc_info=True,
        )
        await interaction.response.send_message(
            "An error occurred while trying to update the item icon."
        )

@group.command()
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source, item=autocomplete_item)
async def update_item_points(
    interaction: discord.Interaction,
    tier: str,
    source: str,
    item: str,
    new_points: float,
):
    """Updates the points value for a specific item."""
    logger.info(
        f"Attempting to update points for item '{item}' in source '{source}' ({tier}) to {new_points}"
    )

    # Fetch the entire document
    template = await coll.find_one({})

    if not template:
        logger.warning("Template document not found in the collection.")
        await interaction.response.send_message("Template not found.")
        return

    try:
        # Navigate through the document structure to find the target item
        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template.")
            await interaction.response.send_message(f"Tier `{tier}` not found.")
            return

        source_found = False
        item_found = False

        # Iterate through sources in the tier
        for source_data in tier_data.get("sources", []):
            if source_data.get("name") == source:
                source_found = True
                # Iterate through items in the source
                for item_data in source_data.get("items", []):
                    if item_data.get("name") == item:
                        item_found = True
                        # Modify the points data in memory
                        item_data["points"] = new_points
                        # Also update duplicate_points if it exists and is half of points
                        # This handles cases where duplicate_points might not have been added yet
                        if "duplicate_points" in item_data or item_data.get("duplicate_points") == item_data.get("points", 0) / 2:
                             item_data["duplicate_points"] = new_points / 2 if new_points != 0 else 0

                        logger.info(f"Modified points for item '{item}' to {new_points} in memory.")
                        break  # Item found and modified, no need to check other items

                if source_found and item_found:
                    break  # Source and item found, no need to check other sources

        if source_found and item_found:
            # If the item was found and modified in memory, replace the entire document
            replace_result = await coll.replace_one({"_id": template["_id"]}, template)

            if replace_result.modified_count > 0:
                logger.info(
                    f"Successfully replaced document with updated points for item '{item}'."
                )
                await interaction.response.send_message(
                    f"Points for item `{item}` in `{source}` ({tier}) updated to `{new_points}`."
                )
            else:
                 logger.warning(
                    "Replace operation did not modify the document for points update. Document might have changed or been deleted."
                )
                 await interaction.response.send_message(
                    "Could not update the item points (replace failed)."
                )
        else:
            # If we iterated through all sources/items and didn't find the target
            if not source_found:
                logger.warning(
                    f"Source '{source}' not found within tier '{tier}' for points update."
                )
                await interaction.response.send_message(
                    f"Source `{source}` not found within tier `{tier}`."
                )
            elif not item_found:
                 logger.warning(
                    f"Item '{item}' not found within source '{source}' in tier '{tier}' for points update."
                )
                 await interaction.response.send_message(
                    f"Item `{item}` not found within source `{source}` in tier `{tier}`."
                )
            else:
                 logger.warning("Could not find the specified tier, source, or item for points update (general failure).")
                 await interaction.response.send_message("Could not find the specified tier, source, or item.")


    except Exception as e:
        logger.error(
            f"An error occurred while attempting to update item points in memory or replace the document for '{item}': {e}",
            exc_info=True,
        )
        await interaction.response.send_message(
            "An error occurred while trying to update the item points."
        )


@group.command()
async def mock_submission(interaction: discord.Interaction):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.success))
    view.add_item(discord.ui.Button(label="Reject", style=discord.ButtonStyle.danger))
    embed = discord.Embed(title="Hill Giant Club")
    embed.set_thumbnail(url="https://oldschool.runescape.wiki/images/thumb/Hill_giant_club_detail.png/150px-Hill_giant_club_detail.png?53073")
    embed.set_footer(text="Submitted by: @User#0000 : Ironfoundry", icon_url="https://i.imgur.com/9aModKk.png")
    embed.add_field(name="Obor", value="**Points:** 22.50")
    embed.add_field(name="(1/1) items collected", value="**Unlocks:** 1.50x Multiplier")
    embed.set_image(url="https://oldschool.runescape.wiki/images/Fighting_Obor.png?5197d")
    await interaction.response.send_message(embed=embed, view=view)

async def get_clan(interaction: discord.Interaction):
    for role in interaction.user.roles: # type: ignore
        if role.id == 1343921208948953128:
            return "Ironclad"
        if role.id == 1343921101687750716:
            return "Iron Foundry"

async def create_tier_options() -> list[discord.SelectOption]:
    options = []
    template: dict | None = await coll.find_one({})
    if not template: return [discord.SelectOption(label="No Data Matched")]
    
    for tier in template["tiers"]:
        options.append(discord.SelectOption(label=str(tier), value=str(tier)))
        logger.info(f"Adding '{tier}' to options.")
    return options

async def create_source_options(tier: str) -> list[discord.SelectOption]:
    options = []
    template: dict | None = await coll.find_one({})
    if not template: return [discord.SelectOption(label="No Data Matched")]
    
    for source in template["tiers"][tier]["sources"]:
        options.append(discord.SelectOption(label=source["name"], value=source["name"]))
        logger.info(f"Adding '{source["name"]}' to options.")
    
    return options

async def parse_tier(source: str) -> str: # type: ignore
    template: dict | None = await coll.find_one({})
    if not template:
        return ""
    
    for tier_name, tier_data in template["tiers"].items():  # Correctly unpack tier name and data
        for idx in tier_data["sources"]:  # Access the correct dictionary level
            if source in idx["name"]:
                logger.info(f"Tier found: {tier_name}")
                return tier_name  # Return the tier name instead of the whole tier object

    

async def submit_to_db(interaction: discord.Interaction, tier: str, source: str, item: str, points: float):
    template = await coll.find_one({})
    
    if not template:
        await interaction.response.send_message("Template not found.", ephemeral=True)
        return
    
    _item = {
        "name": item,
        "points": points,
        "duplicate_points": points / 2 if points != 0 else 0,
        "obtained": False,
        "duplicate_obtained": False,
        "icon_url": None
    }
    result = await coll.update_one(
        {"_id": template["_id"], f"tiers.{tier}.sources.name": source},
        {"$push": {f"tiers.{tier}.sources.$.items": _item}}
    )
    logger.info(_item)
    logger.info(source)
    logger.info(tier)
    if result.modified_count > 0:
        await interaction.response.send_message(f"Item `{item}` added to `{source}` in `{tier}` tier.", ephemeral=True, delete_after=30)
    else:
        await interaction.response.send_message("```Tier or source not found.```", ephemeral=True, delete_after=30)
    
    
class DBmodal(discord.ui.Modal, title="Add new item"):
    item_name = discord.ui.TextInput(label="Item Name")
    point_value = discord.ui.TextInput(label="Assigned Points")
    def __init__(self, tier, source):
        super().__init__(timeout=None)
        self.tier = tier
        self.source = source
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await submit_to_db(interaction, self.tier, self.source, self.item_name.value, float(self.point_value.value))
        

class TierSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="Select a tier", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message(content="```Select a source and click 'Add'```",
                                                    ephemeral=True, 
                                                    view=SourceView(
                                                        options=await create_source_options(self.values[0]),
                                                        tier=self.values[0]))
        except Exception as e:
            logger.error(e)
            
class SourceSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="Select a source", options=options)

    async def callback(self, interaction: discord.Interaction):
        source = self.values[0]
        self.view.source = source # type: ignore
        await interaction.response.send_message(f"```Selected: {source.capitalize()}```", ephemeral=True, delete_after=2)
        

class InitialView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(timeout=None)
        self.add_item(TierSelect(options))
        
class SourceView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption], tier: str):
        super().__init__(timeout=None)
        self.tier = tier
        self.source = None
        self.add_item(SourceSelect(options))
    
    @discord.ui.button(label="Add", style=discord.ButtonStyle.success, row=2)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.source == None: await interaction.response.send_message("```Please Select a Source first.```")
        try:
            await interaction.response.send_modal(DBmodal(tier=self.tier, source=self.source))
        except Exception as e:
            logger.info(e)
        
@group.command()
async def helpsalt(interaction: discord.Interaction):
    view = InitialView(options=await create_tier_options())
    await interaction.response.send_message("```Select a tier to continue```", view=view)
    

def setup(client: discord.Client):
    client.tree.add_command(group, guild=client.selected_guild) # type: ignore