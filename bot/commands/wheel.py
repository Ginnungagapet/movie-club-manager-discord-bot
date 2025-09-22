"""
Wheel management commands
"""

import discord
from discord.ext import commands
import logging
import asyncio
import io

logger = logging.getLogger(__name__)


class WheelCommands(commands.Cog):
    """Commands for using the wheel"""

    def __init__(self, bot):
        self.bot = bot
        self.wheel_service = bot.services["wheel"]

    @commands.command(name="spin")
    async def spin_wheel(self, ctx: commands.Context) -> None:
        """Spin the wheel and select a random movie genre with GIF animation."""
        try:
            # Send initial message
            initial_msg = await ctx.send("🎡 Spinning the movie genre wheel...")

            # Select random genre and create animation
            selected_genre = self.wheel_service.spin_wheel()
            gif_data = self.wheel_service.create_wheel_gif(selected_genre)

            # Send the spinning GIF
            gif_file = discord.File(fp=gif_data, filename="wheel_spinning.gif")
            gif_msg = await ctx.send(file=gif_file)

            # Wait for the animation to finish (duration * frames + small buffer)
            animation_duration = (
                self.wheel_service.GIF_DURATION * self.wheel_service.ANIMATION_FRAMES
                + 1.0
            )
            await asyncio.sleep(animation_duration)

            # Create and send the final static wheel image
            final_angle = self.wheel_service._calculate_final_angle(selected_genre)
            final_wheel_image = self.wheel_service.create_wheel_image(final_angle)

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
            logger.error(f"Error in spin command: {e}")
            await ctx.send("❌ An unexpected error occurred while spinning the wheel.")

    @commands.command(name="add_genre")
    async def add_genre(self, ctx: commands.Context, *, genre: str) -> None:
        """Add a new genre to the wheel."""
        if not genre.strip():
            await ctx.send("❌ Please provide a genre name.")
            return

        if self.wheel_service.add_genre(genre):
            await ctx.send(f'✅ Added "{genre}" to the wheel!')
        else:
            await ctx.send(f'❌ "{genre}" is already on the wheel!')

    @commands.command(name="remove_genre")
    async def remove_genre(self, ctx: commands.Context, *, genre: str) -> None:
        """Remove a genre from the wheel."""
        if not genre.strip():
            await ctx.send("❌ Please provide a genre name.")
            return

        if self.wheel_service.remove_genre(genre):
            await ctx.send(f'✅ Removed "{genre}" from the wheel!')
        else:
            await ctx.send(f'❌ "{genre}" was not found on the wheel!')

    @commands.command(name="list_genres")
    async def list_genres(self, ctx: commands.Context) -> None:
        """List all genres currently on the wheel with visual representation."""
        genres = self.wheel_service.genre_list

        if not genres:
            await ctx.send("❌ No genres available on the wheel.")
            return

        genres_text = ", ".join(genres)

        # Create and send wheel image
        try:
            wheel_image = self.wheel_service.create_wheel_image()

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
            logger.error(f"Error generating wheel image: {e}")
            await ctx.send(
                f"**Movie Genres on the Wheel ({len(genres)} total)**:\n{genres_text}"
            )

    @commands.command(name="wheel_help")
    async def wheel_help(self, ctx: commands.Context) -> None:
        """Show help for wheel commands."""
        embed = discord.Embed(
            title="🎡 Wheel Commands Help",
            description="Spin the movie genre wheel to pick a random genre!",
            color=0xFF69B4,
        )

        embed.add_field(
            name="Wheel Commands",
            value=(
                "`!spin` - Spin the wheel with animation\n"
                "`!add_genre <genre>` - Add a new genre\n"
                "`!remove_genre <genre>` - Remove a genre\n"
                "`!list_genres` - Show all genres with wheel image"
            ),
            inline=False,
        )

        embed.add_field(
            name="Movie Picker Commands",
            value=(
                "`!pick_movie <title> <optional: year>` - Pick a movie. Only works if you're currently picking or up next.\n"
                "`!current_movie` - Show the current movie\n"
                "`!movie_status` - Show if a movie has been picked and what it is\n"
                "`!search_movie <title> <optional: year>` - Search for a movie in IMDB. Useful before picking."
            ),
            inline=False,
        )

        embed.add_field(
            name="Schedule Commands",
            value=(
                "`!schedule <periods, default=5>` - Show the upcoming rotation schedule, for the next <periods> users.\n"
                "`!who_picks` - Show the current picker\n"
                "`!history <num, default=10>` - Show the last <num> movie picks\n"
                "`!my_picks` - Show your movie pick history."
            ),
            inline=False,
        )

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(WheelCommands(bot))
