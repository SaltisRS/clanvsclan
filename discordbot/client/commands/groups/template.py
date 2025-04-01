from discord import app_commands



class TemplateGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="template", description="A template group")