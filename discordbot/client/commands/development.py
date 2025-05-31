from typing import Any, Dict, List, Optional
import discord
import os
import io
import pandas as pd
import asyncio

from loguru import logger
from pymongo import AsyncmongoClient
from dotenv import load_dotenv
from httpx import AsyncClient
from discord import Embed, Object

from .groups.dev import DevGroup


load_dotenv()
group = DevGroup()
web = AsyncClient()
headers = {
            "x-api-key": "gdu9etkchtkvpbf1hgk3fnvo",
            "User-Agent": "saltis."
}

urls = ("https://api.wiseoldman.net/v2/groups/1500/csv", "https://api.wiseoldman.net/v2/groups/9403/csv")
db = Optional
players = Optional
verify_set = set()
linked_role_id = 1369434992714842205
IC_roleid = 1343921208948953128
IF_roleid = 1343921101687750716

async def get_player_info(discord_id: int):
    """Fetches a player's document from the Players collection."""
    try:
        player_document = await players.find_one({"discord_id": discord_id})
        return player_document
    except Exception as e:
        logger.error(f"Error fetching player info for {discord_id}: {e}", exc_info=True)
        return None

notif_roles: dict[str, dict] = {
    "toa": {"role": Object(id=1370919773256421480), "icon": "<:toa_e:1371626690869985360>"},
    "cox": {"role": Object(id=1370919825915777074), "icon": "<:cox:1371626699304997005>"},
    "tob": {"role": Object(id=1370919886515081376), "icon": "<:tob:1371626695261421588>"},
    "yama": {"role": Object(id=1370919920879276113), "icon": "<:obor:1371626696780021800>"},
    "nightmare": {"role": Object(id=1370919940911267930), "icon": "<:nightmare:1371626709714993192>"},
    "nex": {"role": Object(id=1370919965825437846), "icon": "<:nex:1371626708310036480>"},
    "royal titans": {"role": Object(id=1370920827435880590), "icon": "<:the_royal_titans:1371626688848592978>"},
    "zalcano": {"role": Object(id=1371106993208823928), "icon": "<:zalcano:1371626691922759681>"},
    "hueycoatl": {"role": Object(id=1371266895281393717), "icon": "<:hueycoatl:1371626687258824824>"},
    "wilderness": {"role": Object(id=1371265502302830683), "icon": "<:callisto:1371626697967009855>"},
    "minigames": {"role": Object(id=1370919995609190400), "icon": "<:gotr:1371626703238991943>"}
}

class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.create_buttons()

    def create_buttons(self):
        for key, data in notif_roles.items():
            button = discord.ui.Button(
                label=key.title(),
                custom_id=f"role_toggle_{key}",
                style=discord.ButtonStyle.green,
                emoji=data.get("icon")
            )
            button.callback = self.role_button_callback
            self.add_item(button)

    async def role_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        custom_id = interaction.data["custom_id"]#type: ignore
        role_key = custom_id.replace("role_toggle_", "")

        role_data = notif_roles.get(role_key)

        if not role_data:
            await interaction.followup.send("Error: Invalid button clicked.", ephemeral=True)
            return

        role_id = role_data["role"].id
        guild = interaction.guild

        if not guild:
            await interaction.followup.send("Error: Could not determine the guild.", ephemeral=True)
            return

        role = guild.get_role(role_id)
        member = interaction.user

        if not role:
            await interaction.followup.send(f"Error: Could not find the '{role_key.title()}' role in this server.", ephemeral=True)
            return

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.followup.send(f"Removed the **{role.name}** role.", ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.followup.send(f"Added the **{role.name}** role.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("Error: I don't have permission to manage roles.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
        
        
        

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
async def force_rename_all(interaction: discord.Interaction):
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

            _db_linked = ""
            for user in db_players_data["users"]:
                _db_linked += f"\n<@{user.id}> : {user.rsn}"
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
async def get_inactive_players(interaction: discord.Interaction, point_threshold: int = 0):
    players_cursor = players.find({"total_gained": {"$lte": point_threshold}})
    if not players_cursor:
        await interaction.response.send_message("None")
        return
    
    
    inactive_players = await players_cursor.to_list()
    
    if not inactive_players:
        await interaction.response.send_message(f"No players under: {point_threshold} found.")

    message = f"# Inactive Players =< '{point_threshold}'\n"
    
    for player in inactive_players:
        message += f"`{player.get('rsn', 'Unknown')}` - <@{player.get('discord_id', 'Unknown')}> : {player.get('total_gained', 0)}pts\n"
    
    await interaction.response.send_message(message)



@group.command()
async def send_link_message(interaction: discord.Interaction):
    embed = discord.Embed(title="Link Your RSN", color=discord.Color.teal())
    embed.description = "Link your RSN of the active account to be used in the event.\nThis is a requirement to participate and is checked against WiseOldMan."
    await interaction.response.send_message("Sending...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=LinkView())#type: ignore

@group.command()
async def send_role_select(interaction: discord.Interaction):
    embed = Embed(title="Notification Roles")
    embed.description = "Click any button below to toggle between recieving notifications for the related content!"
    await interaction.response.send_message("sending...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=RoleView())#type: ignore
    
def get_clan_from_role_list(roles: List[discord.Role]) -> Optional[str]:
    """Determines the clan string from a list of Discord roles."""
    for role in roles:
        if role.id == IF_roleid:
            return "ironfoundry"
        elif role.id == IC_roleid:
            return "ironclad"
    return None

# --- New Command: Update Player Clans ---
@group.command(name="update_player_clans", description="Updates the clan field for all members based on roles.")
async def update_player_clans(interaction: discord.Interaction):
    logger.info(f"Update player clans command initiated by {interaction.user.id} ({interaction.user.name}).")
    await interaction.response.defer() # Defer as this can take time

    guild = interaction.guild # Get the server the command was run in
    if not guild:
        await interaction.followup.send("This command must be run in a server.", ephemeral=True)
        return

    updated_count = 0
    created_count = 0 # Count for players whose documents are created if they don't exist
    errors_count = 0

    # You might want to exclude bots from this process
    members_to_process = [member for member in guild.members if not member.bot]

    logger.info(f"Processing {len(members_to_process)} members in guild {guild.id} for clan updates.")

    for member in members_to_process:
        try:
            # Determine the member's clan based on their roles
            member_clan = get_clan_from_role_list(member.roles)

            # Fetch the player document for this member
            player_document = await get_player_info(member.id)

            if player_document:
                # Player document exists, update the clan field if it's different
                current_clan_in_db = player_document.get("clan")
                if current_clan_in_db != member_clan:
                    player_document["clan"] = member_clan # Update the clan field
                    update_result = await players.replace_one({"_id": player_document["_id"]}, player_document)
                    if update_result.modified_count > 0:
                        updated_count += 1
                        logger.debug(f"Updated clan for {member.id} ({member.name}) from '{current_clan_in_db}' to '{member_clan}'.")
                    else:
                         # This might happen if the document was modified concurrently,
                         # or if the update didn't result in a change (e.g., both None).
                         # It's not necessarily an error, but worth noting.
                         logger.debug(f"Player {member.id} clan in DB already matched determined clan or no change needed.")

            else:
                # Player document does not exist, create a new one
                if member_clan: # Only create if they have a clan role
                    new_player_document: Dict[str, Any] = {
                        "discord_id": member.id,
                        "rsn": "", # Initialize RSN (might need a separate command to set this)
                        "submissions": [],
                        "clan": member_clan, # Set the determined clan
                        "screenshots": [], # Or remove if not needed at this level
                        "total_gained": 0.0,
                        "obtained_items": {} # Initialize obtained items structure
                    }
                    insert_result = await players.insert_one(new_player_document)
                    if insert_result.inserted_id:
                        created_count += 1
                        logger.debug(f"Created player document for {member.id} ({member.name}) with clan '{member_clan}'.")
                    else:
                         logger.error(f"Failed to create player document for {member.id}.")
                         errors_count += 1
                else:
                     # Member doesn't have a recognized clan role and no player document exists.
                     # Do nothing in this case.
                     logger.debug(f"Member {member.id} has no clan role and no existing player document. Skipping creation.")


        except Exception as e:
            logger.error(f"An error occurred while processing member {member.id} ({member.name}): {e}", exc_info=True)
            errors_count += 1

    # Send a summary message after processing all members
    summary_message = f"Finished updating player clans.\n"
    summary_message += f"Updated {updated_count} existing player documents.\n"
    summary_message += f"Created {created_count} new player documents.\n"
    if errors_count > 0:
        summary_message += f"Encountered {errors_count} errors."

    await interaction.followup.send(summary_message)
    logger.info(f"Update player clans command finished. Updated: {updated_count}, Created: {created_count}, Errors: {errors_count}.")
    

async def setup(client: discord.Client, mongo_client: AsyncmongoClient | None):
    if mongo_client == None:
        return
    global mongo, db, players
    mongo = mongo_client
    db = mongo["Frenzy"]
    players = db["Players"] # type: ignore
    await populate_verify_set()
    client.tree.add_command(group, guild=client.selected_guild) 
    client.add_view(LinkView())
