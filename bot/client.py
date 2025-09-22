"""
Discord bot client setup and initialization
"""

import discord
from discord.ext import commands
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.settings import Settings

from services.movie_service import MovieService
from services.rotation_service import RotationService
from services.rating_service import RatingService
from services.wheel_service import WheelService

logger = logging.getLogger(__name__)


class MovieClubBot(commands.Bot):
    """Main Discord bot class for Movie Club Manager"""

    def __init__(self, settings: "Settings"):
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True

        # Initialize bot with settings
        super().__init__(
            command_prefix=settings.command_prefix,
            intents=intents,
            help_command=None,  # We'll create a custom help command
        )

        self.settings = settings

        # Initialize services
        self.movie_service = MovieService(settings)
        self.rotation_service = RotationService(settings)
        self.rating_service = RatingService(settings)
        self.wheel_service = WheelService(settings)

        # Store services for commands to access
        self.services = {
            "movie": self.movie_service,
            "rotation": self.rotation_service,
            "rating": self.rating_service,
            "wheel": self.wheel_service,
        }

    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up Movie Club Bot...")

        # Initialize database
        await self.rotation_service.initialize_database()

        # Load command modules
        await self._load_commands()

        logger.info("Bot setup complete!")

    async def _load_commands(self):
        """Load all command modules"""
        command_modules = [
            "bot.commands.rotation",
            "bot.commands.movies",
            "bot.commands.ratings",
            "bot.commands.admin",
            "bot.commands.wheel",
        ]

        for module in command_modules:
            try:
                await self.load_extension(module)
                logger.info(f"Loaded command module: {module}")
            except Exception as e:
                logger.error(f"Failed to load {module}: {e}")

    async def on_ready(self):
        """Called when bot is ready and connected"""
        logger.info(f"Bot is ready! Logged in as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} servers")

        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="for movie picks 🎬"
        )
        await self.change_presence(activity=activity)

    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
            return

        # Log unexpected errors
        logger.error(
            f"Unexpected error in command {ctx.command}: {error}", exc_info=error
        )
        await ctx.send("❌ An unexpected error occurred. Please try again later.")

    async def close(self):
        """Clean up when bot is shutting down"""
        logger.info("Cleaning up bot resources...")

        # Close service connections
        if hasattr(self.rotation_service, "close"):
            await self.rotation_service.close()

        await super().close()
