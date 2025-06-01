"""
Wheel management commands
"""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class WheelCommands(commands.Cog):
    """Commands for using the wheel"""

    def __init__(self, bot):
        self.bot = bot
        self.wheel_service = bot.services["wheel"]

    @bot.command(name="spin")
    async def spin_wheel(ctx: commands.Context) -> None:
        """Spin the wheel and select a random movie genre with GIF animation."""
        try:
            # Send initial message
            initial_msg = await ctx.send("🎡 Spinning the movie genre wheel...")

            # Select random genre and create animation
            selected_genre = bot.wheel.spin_wheel()
            gif_data = bot.wheel.create_wheel_gif(selected_genre)

            # Send the spinning GIF
            gif_file = discord.File(fp=gif_data, filename="wheel_spinning.gif")
            gif_msg = await ctx.send(file=gif_file)

            # Wait for the animation to finish (duration * frames + small buffer)
            animation_duration = (
                bot.wheel.GIF_DURATION * bot.wheel.ANIMATION_FRAMES + 1.0
            )
            await asyncio.sleep(animation_duration)

            # Create and send the final static wheel image
            final_angle = bot.wheel._calculate_final_angle(selected_genre)
            final_wheel_image = bot.wheel.create_wheel_image(final_angle)

            with io.BytesIO() as image_buffer:
                final_wheel_image.save(image_buffer, "PNG")
                image_buffer.seek(0)

                final_image_file = discord.File(
                    fp=image_buffer, filename="final_wheel.png"
                )

                # Delete the GIF and replace with static image
                await gif_msg.delete()
                await ctx.send(file=final_image_file)

            # Send the result message
            await initial_msg.edit(
                content=f"🎡 The wheel has stopped! Tonight's movie genre is: **{selected_genre}**"
            )

        except ValueError as e:
            await ctx.send(f"❌ Error: {e}")
        except Exception as e:
            await ctx.send("❌ An unexpected error occurred while spinning the wheel.")
            print(f"Error in spin command: {e}")

    @bot.command(name="add_genre")
    async def add_genre(ctx: commands.Context, *, genre: str) -> None:
        """Add a new genre to the wheel."""
        if not genre.strip():
            await ctx.send("❌ Please provide a genre name.")
            return

        if bot.wheel.add_genre(genre):
            await ctx.send(f'✅ Added "{genre}" to the wheel!')
        else:
            await ctx.send(f'❌ "{genre}" is already on the wheel!')

    @bot.command(name="remove_genre")
    async def remove_genre(ctx: commands.Context, *, genre: str) -> None:
        """Remove a genre from the wheel."""
        if not genre.strip():
            await ctx.send("❌ Please provide a genre name.")
            return

        if bot.wheel.remove_genre(genre):
            await ctx.send(f'✅ Removed "{genre}" from the wheel!')
        else:
            await ctx.send(f'❌ "{genre}" was not found on the wheel!')

    @bot.command(name="list_genres")
    async def list_genres(ctx: commands.Context) -> None:
        """List all genres currently on the wheel with visual representation."""
        genres = bot.wheel.genre_list

        if not genres:
            await ctx.send("❌ No genres available on the wheel.")
            return

        genres_text = ", ".join(genres)

        # Create and send wheel image
        try:
            wheel_image = bot.wheel.create_wheel_image()

            with io.BytesIO() as image_buffer:
                wheel_image.save(image_buffer, "PNG")
                image_buffer.seek(0)

                image_file = discord.File(fp=image_buffer, filename="wheel.png")
                await ctx.send(
                    f"**Movie Genres on the Wheel ({len(genres)} total)**:\n{genres_text}",
                    file=image_file,
                )
        except Exception as e:
            # Fallback to text-only if image generation fails
            await ctx.send(
                f"**Movie Genres on the Wheel ({len(genres)} total)**:\n{genres_text}"
            )
            print(f"Error generating wheel image: {e}")
