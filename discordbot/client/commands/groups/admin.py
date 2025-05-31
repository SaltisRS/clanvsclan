from discord import app_commands



class AdminGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="admin", description="Admin Group")