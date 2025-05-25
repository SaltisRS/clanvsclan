# modules/activity_modals.py
import discord
import os

from io import BytesIO
from upyloadthing import AsyncUTApi, UTApiOptions
from dotenv import load_dotenv
from loguru import logger
from typing import Dict, Any
from loguru import logger
from pymongo import AsyncMongoClient


load_dotenv()
UPLOADTHING_TOKEN = os.getenv("UPLOADTHING_TOKEN")
mongo = AsyncMongoClient(host=os.getenv("MONGO_URI"))
db = mongo["Frenzy"]
players_coll = db["Players"]

async def upload_screenshot(screenshot: discord.Attachment):
    url = None
    _screenshot = BytesIO()
    await screenshot.read()
    api = AsyncUTApi(UTApiOptions(token=UPLOADTHING_TOKEN))
    result = api.upload_files(_screenshot)
    if result:
        for res in await result:
            url = res.url
            break
    return url
            
    
async def insert_activity_data(activity_data: Dict[str, Any], interaction: discord.Interaction):
    """Handles the insertion/update of activity tracking data in the player document."""
    user_id = activity_data.get("user_id")
    action = activity_data.get("action")
    activity = activity_data.get("activity")
    screenshot_url = activity_data.get("screenshot_url")
    metric_values = activity_data.get("metric_values", {})

    logger.info(f"Insertion handler called for {user_id}, Activity: '{activity}', Action: '{action}', Metrics: {metric_values}")

    player_document = await get_player_info(user_id) # type: ignore
    if not player_document:
         logger.error(f"Player data not found for {user_id} during insertion handler.")
         await interaction.followup.send("Error saving your data. Player data not found.", ephemeral=True)
         return

    if "tracking" not in player_document:
        player_document["tracking"] = []

    in_progress_entry = None
    for _, entry in enumerate(player_document["tracking"]):
         if entry.get("name") == activity:
                in_progress_entry = entry
                break

    if action == "Start":
        if in_progress_entry is not None:
             logger.warning(f"Insertion handler received 'start' for '{activity}' while one was in progress for {user_id}. This shouldn't happen if command logic is correct.")
             await interaction.followup.send(f"You already have an in-progress tracking entry for **{activity}**.", ephemeral=True)
             return

        new_tracking_entry = {
             "name": activity,
             "start": {
                 "screenshot": screenshot_url,
                 "values": metric_values,
                 "timestamp": discord.utils.utcnow()
             },
             "end": {
                 "screenshot": "",
                 "values": {},
                 "timestamp": None
             }
        }
        player_document["tracking"].append(new_tracking_entry)
        logger.debug(f"Insertion handler created new tracking entry for activity '{activity}'.")
        feedback_message = f"✅ Started tracking **{activity}**. Start counts: {', '.join([f'{m}: {v}' for m, v in metric_values.items()])}"


    elif action == "End":
         if in_progress_entry is None:
              logger.warning(f"Insertion handler received 'end' for '{activity}' without an active start entry for {user_id}. This shouldn't happen if command logic is correct.")
              await interaction.followup.send(f"Error: Could not find an active tracking entry for **{activity}**, start one before retrying.", ephemeral=True)
              return

        # --- Update the In-Progress Tracking Entry with End Data ---
         in_progress_entry["end"] = {
             "screenshot": screenshot_url,
             "values": metric_values, # Use the values submitted in the end modal
             "timestamp": discord.utils.utcnow() # Add timestamp for end
         }

         feedback_message = f"✅ Updated tracking for **{activity}**. Updated counts: {', '.join([f'{m}: {v}' for m, v in metric_values.items()])}"

    try:
        await players_coll.replace_one({"_id": player_document["_id"]}, player_document)

        logger.info(f"Player {user_id} successfully saved data via insertion handler for '{activity}'.")
        await interaction.followup.send(feedback_message, ephemeral=True)

    except Exception as e:
        logger.error(f"Failed to save player document via insertion handler for '{activity}' for {user_id}: {e}", exc_info=True)
        await interaction.followup.send("Error saving your tracking data. Please try again.", ephemeral=True)



class DefaultSingleMetricModal(discord.ui.Modal, title="Single Input Modal"):
    count = discord.ui.TextInput(label="Amount of Keys/Points/Kc etc..", placeholder="Only Numbers", required=True)
    custom_id = "default_modal"
    
    def __init__(self, action: str, activity: str, screenshot: discord.Attachment):
        super().__init__(timeout=None, custom_id="mastering_mixology_modal")
        self.action = action
        self.activity = activity
        self.screenshot = screenshot
    
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted.")

        metric_values: Dict[str, Any] = {}
        try:
            metric_values[SingleMetricMappings.get(self.activity, "Unknown")] = int(self.count.value)
        except ValueError:
             await interaction.followup.send("Invalid input for 'count' metric. Please enter numbers.", ephemeral=True)
             return
        
        self.screenshot_url = await upload_screenshot(self.screenshot)
        
        activity_data = {
            "user_id": interaction.user.id,
            "action": self.action,
            "activity": self.activity,
            "screenshot_url": self.screenshot_url,
            "metric_values": metric_values
        }

        try:
            await insert_activity_data(
                activity_data=activity_data,
                interaction=interaction
            )
        except Exception as e:
            logger.error(f"Error calling insertion handler from Modal ({self.activity}, {self.action}): {e}", exc_info=True)
            await interaction.followup.send("An error occurred while processing your data.", ephemeral=True)


class BarbarianAssaultModal(discord.ui.Modal, title="Barbarian Assault"):
    defender = discord.ui.TextInput(label="Defender Points", placeholder="Only Numbers.", required=True)
    healer = discord.ui.TextInput(label="Healer Points", placeholder="Only Numbers", required=True)
    collector = discord.ui.TextInput(label="Collector Points", placeholder="Only Numbers", required=True)
    attacker = discord.ui.TextInput(label="Attacker Points", placeholder="Only Numbers", required=True)

    
    def __init__(self, action: str, activity: str, screenshot: discord.Attachment):
        super().__init__(timeout=None, custom_id="barbarian_assault_modal")
        self.action = action
        self.activity = activity
        self.screenshot = screenshot
    
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted.")

        metric_values: Dict[str, Any] = {}
        try:
            metric_values[self.defender.label] = int(self.defender.value)
            metric_values[self.healer.label] = int(self.healer.value)
            metric_values[self.collector.label] = int(self.collector.value)
            metric_values[self.attacker.label] = int(self.attacker.value)
        except ValueError:
             await interaction.followup.send("Invalid input for one or more metrics. Please enter numbers.", ephemeral=True)
             return
        
        self.screenshot_url = await upload_screenshot(self.screenshot)
        
        activity_data = {
            "user_id": interaction.user.id,
            "action": self.action,
            "activity": self.activity,
            "screenshot_url": self.screenshot_url,
            "metric_values": metric_values
        }

        try:
            await insert_activity_data(
                activity_data=activity_data,
                interaction=interaction
            )
        except Exception as e:
            logger.error(f"Error calling insertion handler from Modal ({self.activity}, {self.action}): {e}", exc_info=True)
            await interaction.followup.send("An error occurred while processing your data.", ephemeral=True)
            

class LastManStandingModal(discord.ui.Modal, title="Last Man Standing"):
    wins = discord.ui.TextInput(label="Victories", placeholder="Only Numbers", required=True)
    points = discord.ui.TextInput(label="Points", placeholder="Only Numbers", required=True)
    
    def __init__(self, action: str, activity: str, screenshot: discord.Attachment):
        super().__init__(timeout=None, custom_id="lms_modal")
        self.action = action
        self.activity = activity
        self.screenshot = screenshot
    
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted.")

        metric_values: Dict[str, Any] = {}
        try:
            metric_values[self.wins.label] = int(self.wins.value)
            metric_values[self.points.label] = int(self.points.value)
        except ValueError:
             await interaction.followup.send("Invalid input for one or more metrics. Please enter numbers.", ephemeral=True)
             return
        
        self.screenshot_url = await upload_screenshot(self.screenshot)
        
        activity_data = {
            "user_id": interaction.user.id,
            "action": self.action,
            "activity": self.activity,
            "screenshot_url": self.screenshot_url,
            "metric_values": metric_values
        }

        try:
            await insert_activity_data(
                activity_data=activity_data,
                interaction=interaction
            )
        except Exception as e:
            logger.error(f"Error calling insertion handler from Modal ({self.activity}, {self.action}): {e}", exc_info=True)
            await interaction.followup.send("An error occurred while processing your data.", ephemeral=True)
    
class MageTrainingArenaModal(discord.ui.Modal, title="Mage Training Arena"):
    alchemy = discord.ui.TextInput(label="Alchemy Points", placeholder="Only Numbers", required=True)
    telekinetic = discord.ui.TextInput(label="Telekinetic Points", placeholder="Only Numbers", required=True)
    graveyard = discord.ui.TextInput(label="Graveyard Points", placeholder="Only Numbers", required=True)
    enchantment = discord.ui.TextInput(label="Enchantment Points", placeholder="Only Numbers", required=True)
    custom_id = "mta_modal"
    
    def __init__(self, action: str, activity: str, screenshot: discord.Attachment):
        super().__init__(timeout=None, custom_id="mta_modal")
        self.action = action
        self.activity = activity
        self.screenshot = screenshot
    
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted.")

        metric_values: Dict[str, Any] = {}
        try:
            metric_values[self.alchemy.label] = int(self.alchemy.value)
            metric_values[self.telekinetic.label] = int(self.telekinetic.value)
            metric_values[self.graveyard.label] = int(self.graveyard.value)
            metric_values[self.enchantment.label] = int(self.enchantment.value)
        except ValueError:
             await interaction.followup.send("Invalid input for one or more metrics. Please enter numbers.", ephemeral=True)
             return
        
        self.screenshot_url = await upload_screenshot(self.screenshot)
        
        activity_data = {
            "user_id": interaction.user.id,
            "action": self.action,
            "activity": self.activity,
            "screenshot_url": self.screenshot_url,
            "metric_values": metric_values
        }

        try:
            await insert_activity_data(
                activity_data=activity_data,
                interaction=interaction
            )
        except Exception as e:
            logger.error(f"Error calling insertion handler from Modal ({self.activity}, {self.action}): {e}", exc_info=True)
            await interaction.followup.send("An error occurred while processing your data.", ephemeral=True)
    
class MasteringMixologyModal(discord.ui.Modal, title="Mastering Mixology"):
    aga = discord.ui.TextInput(label="Aga Resin", placeholder="Only Numbers", required=True)
    lye = discord.ui.TextInput(label="Lye Resin", placeholder="Only Numbers", required=True)
    mox = discord.ui.TextInput(label="Mox Resin", placeholder="Only Numbers", required=True)

    
    def __init__(self, action: str, activity: str, screenshot: discord.Attachment):
        super().__init__(timeout=None, custom_id="mastering_mixology_modal")
        self.action = action
        self.activity = activity
        self.screenshot = screenshot
    
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Submitted.")

        metric_values: Dict[str, Any] = {}
        try:
            metric_values[self.aga.label] = int(self.aga.value)
            metric_values[self.lye.label] = int(self.lye.value)
            metric_values[self.mox.label] = int(self.mox.value)
        except ValueError:
             await interaction.followup.send("Invalid input for one or more metrics. Please enter numbers.", ephemeral=True)
             return
        
        self.screenshot_url = await upload_screenshot(self.screenshot)
        
        activity_data = {
            "user_id": interaction.user.id,
            "action": self.action,
            "activity": self.activity,
            "screenshot_url": self.screenshot_url,
            "metric_values": metric_values
        }

        try:
            await insert_activity_data(
                activity_data=activity_data,
                interaction=interaction
            )
        except Exception as e:
            logger.error(f"Error calling insertion handler from Modal ({self.activity}, {self.action}): {e}", exc_info=True)
            await interaction.followup.send("An error occurred while processing your data.", ephemeral=True)
    
    
ACTIVITY_MODAL_MAP = {
    "Aerial Fishing": DefaultSingleMetricModal,
    "Barbarian Assault": BarbarianAssaultModal,
    "Brimhaven Agility Arena": DefaultSingleMetricModal,
    "Castle Wars": DefaultSingleMetricModal,
    "Chompy Bird Hunting": DefaultSingleMetricModal,
    "Forestry": DefaultSingleMetricModal,
    "Giants' Foundry": DefaultSingleMetricModal,
    "Hallowed Sepulchre": DefaultSingleMetricModal,
    "Herbiboar Hunting": DefaultSingleMetricModal,
    "Last Man Standing": LastManStandingModal,
    "Mahogany Homes": DefaultSingleMetricModal,
    "Mage Training Arena": MageTrainingArenaModal,
    "Mastering Mixology": MasteringMixologyModal,
    "Motherlode Mine": DefaultSingleMetricModal,
    "Pest Control": DefaultSingleMetricModal,
    "Shooting Stars": DefaultSingleMetricModal,
    "Soul Wars": DefaultSingleMetricModal,
    "Tithe Farm": DefaultSingleMetricModal,
    "Trouble Brewing": DefaultSingleMetricModal,
    "Unidentified Minerals": DefaultSingleMetricModal,
    "Volcanic Mine": DefaultSingleMetricModal,
    "Colossal Wyrm Agility": DefaultSingleMetricModal,
    "Ape Atoll Agility Course": DefaultSingleMetricModal,
    "Agility Pyramid": DefaultSingleMetricModal,
    "Dorgesh Kaan Agility Course": DefaultSingleMetricModal,
    "Penguin Agility Course": DefaultSingleMetricModal,
    "Prifddinas Agility Course": DefaultSingleMetricModal,
    "Wilderness Agility Course": DefaultSingleMetricModal,
    "Canifis Rooftop Course": DefaultSingleMetricModal,
    "Seers' Village Rooftop Course": DefaultSingleMetricModal,
    "Pollnivneach Rooftop Course": DefaultSingleMetricModal,
    "Rellekka Rooftop Course": DefaultSingleMetricModal,
    "Ardougne Rooftop Course": DefaultSingleMetricModal
}

SingleMetricMappings = {
    "Aerial Fishing": "Molch Pearls",
    "Brimhaven Agility Arena": "Tickets",
    "Castle Wars": "Tickets",
    "Chompy Bird Hunting": "Chompy Birds",
    "Forestry": "Anima-Infused Bark",
    "Giants' Foundry": "Points",
    "Hallowed Sepulchre": "Hallowed Marks",
    "Herbiboar Hunting": "Herbiboars",
    "Mahogany Homes": "Points",
    "Motherlode Mine": "Gold Nuggets",
    "Pest Control": "Points",
    "Shooting Stars": "Stardust",
    "Soul Wars": "Zeal",
    "Tithe Farm": "Points",
    "Trouble Brewing": "Pieces of Eight",
    "Unidentified Minerals": "Minerals",
    "Volcanic Mine": "Points",
    "Colossal Wyrm Agility": "Termites",
    "Ape Atoll Agility Course": "Laps",
    "Agility Pyramid": "Laps",
    "Dorgesh Kaan Agility Course": "Laps",
    "Penguin Agility Course": "Laps",
    "Prifddinas Agility Course": "Laps",
    "Wilderness Agility Course": "Laps",
    "Canifis Rooftop Course": "Laps",
    "Seers' Village Rooftop Course": "Laps",
    "Pollnivneach Rooftop Course": "Laps",
    "Rellekka Rooftop Course": "Laps",
    "Ardougne Rooftop Course": "Laps"
}

async def get_player_info(discord_id: int):
    """Fetches a player's document from the Players collection."""
    try:
        player_document = await players_coll.find_one({"discord_id": discord_id})
        return player_document
    except Exception as e:
        logger.error(f"Error fetching player info for {discord_id}: {e}", exc_info=True)
        return None

def get_activity_modal_class(activity: str):
    modal_class = ACTIVITY_MODAL_MAP.get(activity)

    if not modal_class:
         logger.error(f"No modal class found in ACTIVITY_MODAL_MAP for activity '{activity}'.")
         return None

    return modal_class


