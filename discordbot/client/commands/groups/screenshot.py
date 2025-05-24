from discord import app_commands



class ScreenshotGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="screenshot", description="Group of commands for managing screenshots for untracked things.")