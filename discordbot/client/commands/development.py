import discord
import os
import io
import pandas as pd
import asyncio

from loguru import logger
from pymongo import AsyncMongoClient
from dotenv import load_dotenv
from httpx import AsyncClient

from .groups.dev import DevGroup


load_dotenv()
group = DevGroup()
web = AsyncClient()
headers = {
            "x-api-key": "gdu9etkchtkvpbf1hgk3fnvo",
            "User-Agent": "saltis."
}

urls = ("https://api.wiseoldman.net/v2/groups/1500/csv", "https://api.wiseoldman.net/v2/groups/9403/csv")
mongo = AsyncMongoClient(host=os.getenv("MONGO_URI"))
db = mongo["Frenzy"]
players = db["Players"]
verify_set = set()

linked_role_id = 1369434992714842205

async def populate_verify_set():
    logger.info("Starting to populate verify_set...")
    verify_set.clear()
    try:
        for url in urls:
            response = await web.get(url, headers=headers)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))

            if 'Player' in df.columns:
                lowercase_players = [player.lower() for player in df['Player'].tolist()]
                verify_set.update(lowercase_players)
                logger.info(f"Added players from {url} to verify_set.")
            else:
                logger.warning(f"URL {url} did not contain a 'Player' column.")

        logger.info(f"verify_set populated with {len(verify_set)} players.")

    except Exception as e:
        logger.error(f"Error fetching or processing CSV data during startup or re-population: {e}")


async def update_db(discord_id: int, rsn: str):
    await players.update_one(
        {"discord_id": discord_id},
        {"$set": {"rsn": rsn.lower()}},
        upsert=True
    )
    logger.info(f"Database updated for Discord ID {discord_id} with RSN: {rsn.lower()}")


class LinkModal(discord.ui.Modal, title="Link RSN"):
    rsn: discord.ui.TextInput = discord.ui.TextInput(
                                                label="The account you want to use for the event.",
                                                style=discord.TextStyle.short,
                                                placeholder="CowSlayer1337",
                                                required=True,
                                                max_length=12
                                                )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Checking RSN against clan accounts...", ephemeral=True, delete_after=15)
        submitted_rsn_lower = self.rsn.value.lower()

        if submitted_rsn_lower in verify_set:
            await interaction.followup.send(f"RSN `{self.rsn.value}` found, you are now linked!", ephemeral=True)
            await interaction.user.add_roles(*[discord.Object(id=1369434992714842205)])
            logger.info(f"User {interaction.user.id} submitted valid RSN: {self.rsn.value}")
            await update_db(interaction.user.id, self.rsn.value)
            await interaction.user.edit(nick=self.rsn.value)
        else:
            logger.info(f"RSN `{self.rsn.value}` not found initially. Re-populating verify_set...")
            await populate_verify_set()

            if submitted_rsn_lower in verify_set:
                await interaction.followup.send(f"RSN `{self.rsn.value}` found after re-checking, you are now linked!", ephemeral=True)
                await interaction.user.add_roles(*[discord.Object(id=1369434992714842205)])
                logger.info(f"User {interaction.user.id} submitted valid RSN after re-check: {self.rsn.value}")
                await update_db(interaction.user.id, self.rsn.value)
                await interaction.user.edit(nick=self.rsn.value)
            else:
                await interaction.followup.send(
                    f"RSN `{self.rsn.value}` not found in either clan's groups.\nPlease double check your spelling and ensure you are added onto your clan's WiseOldMan page before retrying."
                    , ephemeral=True
                )
                logger.info(f"User {interaction.user.id} submitted invalid RSN after re-check: {self.rsn.value}")


class LinkView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(style=discord.ButtonStyle.primary, label="Link RSN", custom_id="LinkButton")
    async def link_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LinkModal())

@group.command()
async def force_rename_all(interaction: discord.Interaction, strict: bool = False):
    await interaction.response.defer(thinking=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send("This command can only be used in a server.")
        return
    db_players_data = {
        "users": []
    }
    docs = players.find({})
    async for doc in docs:
        member = {
            "rsn": doc["rsn"],
            "id": doc["discord_id"]
        }
        logger.info(member)
        db_players_data["users"].append(member)

    db_player_lookup = {user["id"]: user["rsn"] for user in db_players_data["users"]}

    renamed_count = 0
    failed_to_rename = 0
    
    if interaction.client.user is None:
        return

    for member in guild.members:
        if member.id == interaction.client.user.id:
            continue

        try:
            if member.id in db_player_lookup:
                rsn = db_player_lookup[member.id]
                if member.display_name != rsn:
                    await member.edit(nick=rsn)
                    renamed_count += 1
                    logger.info(f"Renamed {member.display_name} ({member.id}) to {rsn}")
            else:
                # 5. If not present, set their server name to "link to join"
                link_name = "link to join"
                 # Check if the current nickname is already "link to join"
                if member.display_name != link_name:
                    await member.edit(nick=link_name)
                    renamed_count += 1 # Count as renamed even though it's a placeholder
                    logger.info(f"Renamed {member.display_name} ({member.id}) to '{link_name}'")
            await asyncio.sleep(3)

        except discord.Forbidden:
            # The bot doesn't have permissions to change nicknames for this member
            logger.warning(f"Missing permissions to rename member: {member.display_name} ({member.id})")
            failed_to_rename += 1
        except Exception as e:
            # Catch other potential errors during renaming
            logger.error(f"Error renaming member {member.display_name} ({member.id}): {e}")
            failed_to_rename += 1

    await interaction.followup.send(
        f"Finished renaming members.\n"
        f"Successfully processed members: {renamed_count}\n"
        f"Failed to rename members (likely due to permissions): {failed_to_rename}"
    )

@group.command()
async def send_link_message(interaction: discord.Interaction):
    embed = discord.Embed(title="Link Your RSN", color=discord.Color.teal())
    embed.description = "Link your RSN of the active account to be used in the event.\nThis is a requirement to participate and is checked against WiseOldMan."
    await interaction.response.send_message("Sending...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=LinkView())#type: ignore


async def setup(client: discord.Client):
    await populate_verify_set()
    client.tree.add_command(group, guild=client.selected_guild) 
    client.add_view(LinkView())
