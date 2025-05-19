import discord
import os

from loguru import logger
from discord import app_commands
from cachetools import TTLCache
from typing import Optional, Literal
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
async def sort_all_items(
    interaction: discord.Interaction,
    sort_by: Literal["name", "points", "duplicate_points"] = "points",
    sort_direction: Literal["asc", "desc"] = "asc"
):
    """Sorts all items across all tiers and sources in the database."""
    logger.info(f"Attempting to sort all items by: {sort_by} in {sort_direction} order")

    valid_sort_keys = ["name", "points", "duplicate_points"]
    valid_sort_directions = ["asc", "desc"]

    if sort_by not in valid_sort_keys or sort_direction not in valid_sort_directions:
         logger.warning(f"Invalid sort parameters: sort_by='{sort_by}', sort_direction='{sort_direction}'")
         await interaction.response.send_message("Invalid sort parameters.")
         return


    await interaction.response.defer()

    try:
        template = await coll.find_one({})

        if not template:
            logger.warning("Template document not found for sorting items.")
            await interaction.followup.send("Template not found.")
            return

        tiers = template.get("tiers", {})

        if not tiers:
            logger.info("No tiers found in the template for sorting.")
            await interaction.followup.send("No tiers found to sort items.")
            return

        items_to_sort = []
        # Collect all items from all sources and tiers
        for tier_name, tier_data in tiers.items():
            sources = tier_data.get("sources", [])
            for source in sources:
                items = source.get("items", [])
                for item in items:
                    # Store item data along with its original tier and source for re-insertion
                    items_to_sort.append(
                        {"tier": tier_name, "source": source.get("name"), "item": item}
                    )

        if not items_to_sort:
             logger.info("No items found across all tiers and sources to sort.")
             await interaction.followup.send("No items found across all tiers and sources to sort.")
             return

        # Determine the reverse value based on sort_direction
        is_reverse = True if sort_direction == "desc" else False

        # Sort the collected items
        items_to_sort.sort(
            key=lambda x: x["item"].get(sort_by, 0 if sort_by.endswith("points") else ""),
            reverse=is_reverse # Use the determined reverse value
        )

        # Reconstruct the tiers and sources with sorted items
        sorted_template = {"_id": template["_id"], "associated_team": template.get("associated_team", ""), "total_gained": template.get("total_gained", 0), "tiers": {}}

        for tier_name in tiers.keys():
             sorted_template["tiers"][tier_name] = {"points_gained": tiers[tier_name].get("points_gained", 0), "sources": []}
             for source_data in tiers[tier_name].get("sources", []):
                  sorted_template["tiers"][tier_name]["sources"].append({
                      "name": source_data.get("name"),
                      "source_gained": source_data.get("source_gained", 0),
                      "multipliers": source_data.get("multipliers", []),
                      "items": []
                  })


        # Distribute the sorted items back into the reconstructed structure
        for item_data in items_to_sort:
            tier_name = item_data["tier"]
            source_name = item_data["source"]
            item = item_data["item"]

            for source in sorted_template["tiers"][tier_name]["sources"]:
                 if source["name"] == source_name:
                      source["items"].append(item)
                      break


        # Replace the entire document in the database with the sorted one
        replace_result = await coll.replace_one({"_id": template["_id"]}, sorted_template)

        if replace_result.modified_count > 0:
            logger.info(f"Successfully sorted all items by '{sort_by}' in {sort_direction} order.")
            await interaction.followup.send(
                f"All items have been sorted by `{sort_by}` in `{sort_direction}` order."
            )
        else:
             logger.warning(
                "Replace operation did not modify the document during sorting. Document might have changed or been deleted."
            )
             await interaction.followup.send(
                "Could not sort all items (replace failed)."
            )

    except Exception as e:
        logger.error(
            f"An error occurred while sorting all items by '{sort_by}' in {sort_direction} order: {e}",
            exc_info=True,
        )
        await interaction.followup.send(
            "An error occurred while trying to sort all items."
        )


@group.command()
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source)
async def rename_source(
    interaction: discord.Interaction, tier: str, source: str, new_name: str
):
    """Renames a Source within a specific tier."""
    logger.info(
        f"Attempting to rename source '{source}' in tier '{tier}' to '{new_name}'"
    )

    # Defer the interaction response
    await interaction.response.defer()

    try:
        template = await coll.find_one({})

        if not template:
            logger.warning("Template document not found for renaming source.")
            await interaction.followup.send("Template not found.")
            return

        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template for renaming source.")
            await interaction.followup.send(f"Tier `{tier}` not found.")
            return

        sources = tier_data.get("sources", [])
        if not sources:
             logger.info(f"No sources found in tier '{tier}' for renaming.")
             await interaction.followup.send(f"No sources found in tier `{tier}`.")
             return

        source_to_rename = None

        # Find the source to rename
        for source_data in sources:
            if source_data.get("name") == source:
                source_to_rename = source_data
                break

        if source_to_rename is None:
            logger.warning(f"Source '{source}' not found in tier '{tier}' for renaming.")
            await interaction.followup.send(f"Source `{source}` not found in tier `{tier}`.")
            return

        # Check if a source with the new name already exists in the same tier
        for source_data in sources:
            if source_data.get("name") == new_name and source_data is not source_to_rename:
                logger.warning(
                    f"A source with the new name '{new_name}' already exists in tier '{tier}'."
                )
                await interaction.followup.send(
                    f"A source with the name `{new_name}` already exists in tier `{tier}`."
                )
                return

        # Rename the source in memory
        source_to_rename["name"] = new_name
        logger.info(f"Renamed source in memory from '{source}' to '{new_name}'.")

        # Replace the entire document in the database with the modified one
        replace_result = await coll.replace_one({"_id": template["_id"]}, template)

        if replace_result.modified_count > 0:
            logger.info(
                f"Successfully renamed source from '{source}' to '{new_name}' in tier '{tier}'."
            )
            await interaction.followup.send(
                f"Source `{source}` in tier `{tier}` renamed to `{new_name}`."
            )
        else:
            logger.warning(
                "Replace operation did not modify the document during source rename. Document might have changed or been deleted."
            )
            await interaction.followup.send(
                "Could not rename the source (replace failed)."
            )

    except Exception as e:
        logger.error(
            f"An error occurred while attempting to rename source '{source}': {e}",
            exc_info=True,
        )
        await interaction.followup.send(
            "An error occurred while trying to rename the source."
        )


@group.command()
@app_commands.autocomplete(
    tier=autocomplete_tier, source=autocomplete_source, item=autocomplete_item
)
async def remove_item(
    interaction: discord.Interaction, tier: str, source: str, item: str
):
    """Removes an Item from a specific Source and Tier."""
    logger.info(
        f"Attempting to remove item '{item}' from source '{source}' ({tier})"
    )

    # Defer the interaction response
    await interaction.response.defer()

    try:
        template = await coll.find_one({})

        if not template:
            logger.warning("Template document not found for removing item.")
            await interaction.followup.send("Template not found.")
            return

        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template for removing item.")
            await interaction.followup.send(f"Tier `{tier}` not found.")
            return

        sources = tier_data.get("sources", [])
        if not sources:
             logger.info(f"No sources found in tier '{tier}' for removing item.")
             await interaction.followup.send(f"No sources found in tier `{tier}`.")
             return

        target_source = None

        # Find the source containing the item
        for source_data in sources:
            if source_data.get("name") == source:
                target_source = source_data
                break

        if not target_source:
            logger.warning(f"Source '{source}' not found in tier '{tier}' for removing item.")
            await interaction.followup.send(f"Source `{source}` not found in tier `{tier}`.")
            return

        items = target_source.get("items", [])
        if not items:
            logger.debug(f"No items found in source '{source}' for removing item.")
            await interaction.followup.send(f"No items found in source `{source}`.")
            return

        item_to_remove_index = -1

        # Find the index of the item to remove
        for i, item_data in enumerate(items):
            if item_data.get("name") == item:
                item_to_remove_index = i
                break

        if item_to_remove_index == -1:
            logger.warning(f"Item '{item}' not found in source '{source}' ({tier}) for removal.")
            await interaction.followup.send(
                f"Item `{item}` not found in source `{source}` ({tier})."
            )
            return

        # Remove the item from the list in memory
        removed_item = items.pop(item_to_remove_index)
        logger.info(f"Removed item '{item}' from source '{source}' ({tier}) in memory.")

        # Replace the entire document in the database with the modified one
        replace_result = await coll.replace_one({"_id": template["_id"]}, template)

        if replace_result.modified_count > 0:
            logger.info(
                f"Successfully removed item '{item}' from source '{source}' ({tier})."
            )
            await interaction.followup.send(
                f"Item `{item}` removed from source `{source}` ({tier})."
            )
        else:
            logger.warning(
                "Replace operation did not modify the document during item removal. Document might have changed or been deleted."
            )
            await interaction.followup.send(
                "Could not remove the item (replace failed)."
            )

    except Exception as e:
        logger.error(
            f"An error occurred while attempting to remove item '{item}': {e}",
            exc_info=True,
        )
        await interaction.followup.send(
            "An error occurred while trying to remove the item."
        )


@group.command()
@app_commands.autocomplete(tier=autocomplete_tier, source=autocomplete_source)
async def remove_source(
    interaction: discord.Interaction, tier: str, source: str
):
    """Removes a Source from a specific tier."""
    logger.info(f"Attempting to remove source '{source}' from tier '{tier}'")

    # Defer the interaction response
    await interaction.response.defer()

    try:
        template = await coll.find_one({})

        if not template:
            logger.warning("Template document not found for removing source.")
            await interaction.followup.send("Template not found.")
            return

        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template for removing source.")
            await interaction.followup.send(f"Tier `{tier}` not found.")
            return

        sources = tier_data.get("sources", [])
        if not sources:
             logger.info(f"No sources found in tier '{tier}' for removal.")
             await interaction.followup.send(f"No sources found in tier `{tier}`.")
             return

        source_to_remove_index = -1

        # Find the index of the source to remove
        for i, source_data in enumerate(sources):
            if source_data.get("name") == source:
                source_to_remove_index = i
                break

        if source_to_remove_index == -1:
            logger.warning(f"Source '{source}' not found in tier '{tier}' for removal.")
            await interaction.followup.send(f"Source `{source}` not found in tier `{tier}`.")
            return

        # Remove the source from the list in memory
        removed_source = sources.pop(source_to_remove_index)
        logger.info(f"Removed source '{source}' from tier '{tier}' in memory.")

        # Replace the entire document in the database with the modified one
        replace_result = await coll.replace_one({"_id": template["_id"]}, template)

        if replace_result.modified_count > 0:
            logger.info(
                f"Successfully removed source '{source}' from tier '{tier}'."
            )
            await interaction.followup.send(
                f"Source `{source}` removed from tier `{tier}`."
            )
        else:
            logger.warning(
                "Replace operation did not modify the document during source removal. Document might have changed or been deleted."
            )
            await interaction.followup.send(
                "Could not remove the source (replace failed)."
            )

    except Exception as e:
        logger.error(
            f"An error occurred while attempting to remove source '{source}': {e}",
            exc_info=True,
        )
        await interaction.followup.send(
            "An error occurred while trying to remove the source."
        )


@group.command()
@app_commands.autocomplete(
    tier=autocomplete_tier, source=autocomplete_source, item=autocomplete_item
)
async def rename_item(
    interaction: discord.Interaction,
    tier: str,
    source: str,
    item: str,
    new_name: str,
):
    """Renames an Item within a specific Source and Tier."""
    logger.info(
        f"Attempting to rename item '{item}' in source '{source}' ({tier}) to '{new_name}'"
    )

    # Defer the interaction response
    await interaction.response.defer()

    try:
        template = await coll.find_one({})

        if not template:
            logger.warning("Template document not found for renaming item.")
            await interaction.followup.send("Template not found.")
            return

        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template for renaming item.")
            await interaction.followup.send(f"Tier `{tier}` not found.")
            return

        sources = tier_data.get("sources", [])
        if not sources:
             logger.info(f"No sources found in tier '{tier}' for renaming item.")
             await interaction.followup.send(f"No sources found in tier `{tier}`.")
             return

        target_source = None
        item_to_rename = None

        # Find the source containing the item
        for source_data in sources:
            if source_data.get("name") == source:
                target_source = source_data
                break

        if not target_source:
            logger.warning(f"Source '{source}' not found in tier '{tier}' for renaming item.")
            await interaction.followup.send(f"Source `{source}` not found in tier `{tier}`.")
            return

        items = target_source.get("items", [])
        if not items:
            logger.debug(f"No items found in source '{source}' for renaming item.")
            await interaction.followup.send(f"No items found in source `{source}`.")
            return

        # Find the item to rename within the target source
        for item_data in items:
            if item_data.get("name") == item:
                item_to_rename = item_data
                break

        if not item_to_rename:
            logger.warning(f"Item '{item}' not found in source '{source}' ({tier}) for renaming.")
            await interaction.followup.send(
                f"Item `{item}` not found in source `{source}` ({tier})."
            )
            return

        # Check if an item with the new name already exists in the same source
        for item_data in items:
            if item_data.get("name") == new_name and item_data is not item_to_rename:
                logger.warning(
                    f"An item with the new name '{new_name}' already exists in source '{source}' ({tier})."
                )
                await interaction.followup.send(
                    f"An item with the name `{new_name}` already exists in source `{source}` ({tier})."
                )
                return

        # Rename the item in memory
        item_to_rename["name"] = new_name
        logger.info(f"Renamed item in memory from '{item}' to '{new_name}'.")

        # Replace the entire document in the database with the modified one
        replace_result = await coll.replace_one({"_id": template["_id"]}, template)

        if replace_result.modified_count > 0:
            logger.info(
                f"Successfully renamed item from '{item}' to '{new_name}' in source '{source}' ({tier})."
            )
            await interaction.followup.send(
                f"Item `{item}` in source `{source}` ({tier}) renamed to `{new_name}`."
            )
        else:
            logger.warning(
                "Replace operation did not modify the document during item rename. Document might have changed or been deleted."
            )
            await interaction.followup.send(
                "Could not rename the item (replace failed)."
            )

    except Exception as e:
        logger.error(
            f"An error occurred while attempting to rename item '{item}': {e}",
            exc_info=True,
        )
        await interaction.followup.send(
            "An error occurred while trying to rename the item."
        )


@group.command()
@app_commands.autocomplete(tier=autocomplete_tier)
async def missing_icons(interaction: discord.Interaction, tier: str):
    """Lists items in a tier that are missing an icon URL, splitting into multiple messages if necessary."""
    logger.info(f"Checking for missing icons in tier: {tier}")

    # Defer the interaction response since sending multiple messages might take time
    await interaction.response.defer()

    try:
        template = await coll.find_one({})

        if not template:
            logger.warning("Template document not found for missing icons check.")
            await interaction.followup.send("Template not found.")
            return

        tier_data = template.get("tiers", {}).get(tier)

        if not tier_data:
            logger.warning(f"Tier '{tier}' not found in the template for missing icons check.")
            await interaction.followup.send(f"Tier `{tier}` not found.")
            return

        missing_icon_items = []

        # Iterate through sources and items to find missing icons
        sources = tier_data.get("sources", [])
        if not sources:
             logger.info(f"No sources found in tier '{tier}'.")
             await interaction.followup.send(f"No sources found in tier `{tier}`.")
             return

        for source in sources:
            items = source.get("items", [])
            if not items:
                 logger.debug(f"No items found in source '{source.get('name', 'Unknown Source')}' in tier '{tier}'.")
                 continue

            for item in items:
                icon_url = item.get("icon_url")
                if icon_url is None or icon_url == "":
                    missing_icon_items.append(
                        f"- **{item.get('name', 'Unnamed Item')}** in `{source.get('name', 'Unnamed Source')}`"
                    )

        if not missing_icon_items:
            await interaction.followup.send(
                f"All items in tier `{tier}` have an icon URL!"
            )
        else:
            # Split the list of missing items into chunks that fit within Discord's limit
            header = f"Items in tier `{tier}` missing an icon URL:"
            message_parts = [header]
            current_message = header

            for item_line in missing_icon_items:
                # Check if adding the next item would exceed the limit (with a little buffer)
                if len(current_message) + len(item_line) + 1 > 1950: # Use a buffer less than 2000
                    # Send the current message
                    await interaction.followup.send(current_message)
                    # Start a new message with the header
                    current_message = header
                    message_parts = [header] # Reset message parts for the new message

                # Add the item line to the current message and message parts
                current_message += "\n" + item_line
                message_parts.append(item_line)

            # Send the last accumulated message (if any items were added after the last split)
            if current_message != header: # Only send if something was added after the last header
                 await interaction.followup.send(current_message)

            logger.info(f"Sent {len(missing_icon_items)} missing icon items across {len(message_parts)} messages for tier '{tier}'.")


    except Exception as e:
        logger.error(
            f"An error occurred while checking for missing icons in tier '{tier}': {e}",
            exc_info=True,
        )
        # Use followup.send after deferring
        await interaction.followup.send(
            "An error occurred while trying to check for missing icons."
        )


    
    
    
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