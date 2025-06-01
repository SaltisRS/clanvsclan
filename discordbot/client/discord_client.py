import discord
import os

from loguru import logger
from discord import app_commands
from dotenv import load_dotenv
from pymongo import AsyncMongoClient


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
        
        self.mongo_client = None

        MONGO_URI = os.getenv("MONGO_URI")
        if not MONGO_URI:
            logger.error("MONGO_URI not found in environment variables! Database will not be connected.")
        else:
            try:
                self.mongo_client = AsyncMongoClient(host=MONGO_URI, maxPoolSize=None, maxIdleTimeMS=60000 * 5, maxConnecting=10)
                logger.info("MongoDB connection initialized successfully.")

            except Exception as e:
                logger.error(f"Failed to initialize MongoDB connection: {e}", exc_info=True)
                self.mongo_client = None
        
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
    
    
    async def load_modules(self):
        ...
        
    async def load_commands(self):
        TemplateTools(self, mongo_client=self.mongo_client)
        SubmitSetup(self, mongo_client=self.mongo_client)
        await DevSetup(self, mongo_client=self.mongo_client)
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

