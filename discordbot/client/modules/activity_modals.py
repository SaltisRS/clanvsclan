# modules/activity_modals.py
import discord
from discord import ui, app_commands
from typing import Dict, Any, Optional, List
from loguru import logger

DefaultSingleMetricModal = ""
BarbarianAssaultModal = ""
ClueCasketModal = ""
LastManStandingModal = ""
MageTrainingArenaModal = ""
MasteringMixologyModal = ""



ACTIVITY_MODAL_MAP = {
    "Aerial Fishing": DefaultSingleMetricModal,
    "Barbarian Assault": BarbarianAssaultModal,
    "Brimhaven Agility Arena": DefaultSingleMetricModal,
    "Castle Wars": DefaultSingleMetricModal,
    "Chompy Bird Hunting": DefaultSingleMetricModal,
    "Clue Caskets": ClueCasketModal,
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

# ... (MODAL_TYPE_MAP) ...

# Helper function to get the correct modal class (uses the simplified map)
def get_activity_modal_class(activity: str):
    modal_class = ACTIVITY_MODAL_MAP.get(activity)


    if not modal_class:
         logger.error(f"No modal class found in ACTIVITY_MODAL_MAP for activity '{activity}'.")
         return None

    return modal_class

# Autocomplete for activity names (uses the keys of the simplified map)
async def autocomplete_activity(interaction: discord.Interaction, current: str):
     """Autocomplete for activity names based on ACTIVITY_MODAL_MAP keys."""
     from modules.activity_modals import ACTIVITY_MODAL_MAP # Ensure import if needed
     return [
         discord.app_commands.Choice(name=activity, value=activity)
         for activity in ACTIVITY_MODAL_MAP.keys()
         if current.lower() in activity.lower()
     ][:25]


# --- Base Modal Class (Now it doesn't know the metrics list in __init__) ---
class BaseActivityModal(ui.Modal):
    def __init__(self, action: str, activity: str, screenshot_url: str, player_coll, get_player_info_func, title: str, **kwargs):
        super().__init__(title=title, **kwargs)
        self.action = action
        self.activity = activity
        self.screenshot_url = screenshot_url
        # self.metrics is removed - specific modals define inputs
        self.player_coll = player_coll
        self.get_player_info_func = get_player_info_func
        self.custom_id = f"activity_modal:{action}:{activity}"


    async def process_modal_submission(self, interaction: discord.Interaction, metric_values: Dict[str, Any]):
        """Common logic to process submitted metric values and update player data."""
        logger.info(f"Processing modal submission for {interaction.user.id} ({self.activity}, {self.action}). Metrics: {metric_values}")

        # Refetch player document
        player_document = await self.get_player_info_func(interaction.user.id)
        if not player_document:
             logger.error(f"Player data not found for {interaction.user.id} during modal submission processing.")
             await interaction.followup.send("Error processing your data. Player data not found.", ephemeral=True)
             return

        if "screenshots" not in player_document:
            player_document["screenshots"] = []

        # Find the tracking entry for this activity (logic depends on action)
        tracking_entry = None
        tracking_entry_index = -1

        # We need to find the entry for this activity where *not all* end screenshots are populated.
        # The BaseActivityModal doesn't know the list of metrics for this activity anymore.
        # This requires the specific modal class to provide the list of its metrics
        # or the Base class needs a way to determine the metrics from the inputs in on_submit.
        # Let's pass the list of metrics from the specific modal's __init__ to the base class.

        # This logic needs to be adjusted to handle the case where the list of metrics
        # is passed down or determined differently. For now, assume self.metrics is available.
        # A better approach: find the entry first, then use the metrics from that entry's start data.
        # But on 'start', there's no existing entry.
        # Simplest for this minimalist structure: Assume all submitted metrics are the relevant ones for state check.
        submitted_metric_names = list(metric_values.keys())


        if self.action == "start":
            # For 'start', check if an in-progress entry already exists with ANY end screenshot missing
            # We need to iterate through ALL screenshots and find one for this activity
            # where at least one end screenshot (from any metric) is missing.
            for i, entry in enumerate(player_document["screenshots"]):
                 if entry.get("activity") == self.activity:
                      # Check if ANY end screenshot is populated in this entry
                      any_end_populated = any(url for url in entry.get("end_screenshots", {}).values())
                      if not any_end_populated: # If no end screenshots are populated, it's in progress
                           tracking_entry = entry
                           tracking_entry_index = i
                           break

            if tracking_entry is not None:
                 await interaction.followup.send(f"You already have an in-progress tracking entry for **{self.activity}**.", ephemeral=True)
                 logger.warning(f"Modal submitted to start '{self.activity}' tracking while one was in progress for {interaction.user.id}.")
                 return

            # --- Create New Tracking Entry ---
            new_tracking_entry = {
                 "activity": self.activity,
                 "pre_screenshots": {metric: self.screenshot_url for metric in submitted_metric_names}, # Use submitted metric names
                 "pre_counts": metric_values,
                 "end_screenshots": {metric: "" for metric in submitted_metric_names}, # Initialize end fields
                 "end_counts": {metric: 0 for metric in submitted_metric_names}
            }
            player_document["screenshots"].append(new_tracking_entry)
            logger.debug(f"Created new tracking entry for activity '{self.activity}'.")
            feedback_message = f"✅ Started tracking **{self.activity}**. Start counts: {', '.join([f'{m}: {v}' for m, v in metric_values.items()])}"


        elif self.action == "end":
             # For 'end', find the in-progress entry (where ANY end screenshot is missing)
             for i, entry in enumerate(player_document["screenshots"]):
                 if entry.get("activity") == self.activity:
                      any_end_populated = any(url for url in entry.get("end_screenshots", {}).values())
                      if not any_end_populated: # If no end screenshots are populated, it's in progress
                           tracking_entry = entry
                           tracking_entry_index = i
                           break


             if tracking_entry is None:
                  await interaction.followup.send(f"Could not find an active tracking entry for **{self.activity}**.")
