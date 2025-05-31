
from typing import Optional
import discord

from loguru import logger
from discord import app_commands
from cachetools import TTLCache
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from dotenv import load_dotenv

from .groups.template import TemplateGroup

mongo: Optional[AsyncMongoClient] = None
db: Optional[AsyncDatabase] = None
coll: Optional[AsyncCollection] = None
load_dotenv()

group = TemplateGroup()
autocomplete_cache = TTLCache(maxsize=512, ttl=30) 
    
async def autocomplete_tier(interaction: discord.Interaction, current: str):
    if coll == None:
        return
    
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
    if coll == None:
        return
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


async def autocomplete_item(interaction: discord.Interaction, current: str):
    if coll == None:
        return
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
    if coll == None:
        return
    global autocomplete_cache
    autocomplete_cache.clear()

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

def get_item_color(item):
    """Returns the appropriate color based on obtained/duplicate_obtained flags."""
    if item.get("obtained") and item.get("duplicate_obtained"):
        return "\u001b[0;32m"  # Green
    elif item.get("obtained") and not item.get("duplicate_obtained"):
        return "\u001b[0;33m"  # Yellow
    else:
        return "\u001b[0;31m"  # Red

        
@group.command()
async def molebor(interaction: discord.Interaction):
    await interaction.response.send_message("https://tenor.com/view/gnomed-gnome-glow-effect-shaking-gif-17863812")


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

async def create_tier_options() -> list[discord.SelectOption] | None:
    if coll == None:
        return
    options = []
    template: dict | None = await coll.find_one({})
    if not template: return [discord.SelectOption(label="No Data Matched")]
    
    for tier in template["tiers"]:
        options.append(discord.SelectOption(label=str(tier), value=str(tier)))
        logger.info(f"Adding '{tier}' to options.")
    return options

async def create_source_options(tier: str) -> list[discord.SelectOption] | None:
    if coll == None:
        return
    options = []
    template: dict | None = await coll.find_one({})
    if not template: return [discord.SelectOption(label="No Data Matched")]
    
    for source in template["tiers"][tier]["sources"]:
        options.append(discord.SelectOption(label=source["name"], value=source["name"]))
        logger.info(f"Adding '{source["name"]}' to options.")
    
    return options

async def parse_tier(source: str) -> str | None:
    if coll == None:
        return
    template: dict | None = await coll.find_one({})
    if not template:
        return ""
    
    for tier_name, tier_data in template["tiers"].items():  # Correctly unpack tier name and data
        for idx in tier_data["sources"]:  # Access the correct dictionary level
            if source in idx["name"]:
                logger.info(f"Tier found: {tier_name}")
                return tier_name  # Return the tier name instead of the whole tier object
        

def setup(client: discord.Client, mongo_client: AsyncMongoClient | None):
    if mongo_client == None:
        return
    global mongo, db, coll
    mongo = mongo_client
    db = mongo["Frenzy"]
    coll = db["Templates"]
    if (mongo, db, coll) == None:
        return
    client.tree.add_command(group, guild=client.selected_guild) # type: ignore