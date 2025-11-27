#!/usr/bin/env python3
"""
Movie Club Discord Bot - Main Entry Point
"""

import asyncio
import logging
from config.settings import Settings
from bot.client import MovieClubBot

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the bot"""
    try:
        # Load configuration
        settings = Settings()

        # Initialize and run the bot
        bot = MovieClubBot(settings)
        await bot.start(settings.discord_token)

    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        logger.info("Bot shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
