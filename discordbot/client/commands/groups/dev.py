from discord import app_commands



class DevGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="dev", description="Development group")