import discord
import os

from loguru import logger
from discord import app_commands
from dotenv import load_dotenv
from discord.ext.tasks import loop

from .modules.invite_checks import InviteTracker
from .modules.activity_updater import activity_update as task1
from .modules.milestone_updater import milestone_update as task2
from .commands.template import setup as TemplateTools
from .commands.development import setup as DevSetup
from .commands.submit import setup as SubmitSetup




class DiscordClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        load_dotenv()
        self.tree = app_commands.CommandTree(self)
        self.token = os.getenv("DISCORD_TOKEN")
        self.preset_guild_id = os.getenv("GUILD_ID")
        self.selected_guild = None
        
    
    
    
    async def set_guild(self):
        try:
            self.selected_guild = await self.fetch_guild(self.preset_guild_id) # type: ignore
        except discord.errors.Forbidden:
            logger.error("Bot does not have access to the guild")
            return
        if self.selected_guild is None:
            logger.error("Guild not found")
            return
        logger.info(f"Guild set to {self.selected_guild}")
    
    @loop(minutes=5)
    async def tasks(self):
        logger.info("Starting Task loop...")
        await task1()
        await task2()
    
    async def load_modules(self):
        self.invite_tracker = InviteTracker(self, self.selected_guild) # type: ignore
        await self.invite_tracker.startup_cache()
        
    async def load_commands(self):
        TemplateTools(self)
        SubmitSetup(self)
        await DevSetup(self)
        commands = await self.tree.sync(guild=self.selected_guild)
        logger.info(f"Loading commands: {commands}")
        
    async def setup_hook(self):
        await self.set_guild()
        await self.load_commands()
        await self.load_modules()
    
    async def on_member_join(self, member: discord.Member):
        logger.info(f"{member} has joined the server")
        await self.invite_tracker.new_member(member)
        
        
    async def on_ready(self):
        logger.info("Bot is ready as {0.user}".format(self))
        await self.setup_hook()
        await self.tasks.start()