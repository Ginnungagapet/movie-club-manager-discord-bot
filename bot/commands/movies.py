"""
Movie selection and management commands
"""

import discord
from discord.ext import commands
import logging
from utils.parsers import parse_movie_input
from utils.embeds import create_movie_embed

logger = logging.getLogger(__name__)


class MovieCommands(commands.Cog):
    """Commands for movie selection and management"""

    def __init__(self, bot):
        self.bot = bot
        self.movie_service = bot.services["movie"]
        self.rotation_service = bot.services["rotation"]

    @commands.command(name="pick_movie")
    async def pick_movie(self, ctx, *, movie_input: str):
        """
        Pick a movie (only allowed during your turn)
        Usage: !pick_movie The Matrix
               !pick_movie The Matrix 1999
        """
        username = ctx.author.name

        # Check if user can pick
        can_pick, reason = await self.rotation_service.can_user_pick(username)

        if not can_pick:
            embed = discord.Embed(
                title="❌ Cannot Pick Movie", description=reason, color=0xFF0000
            )
            embed.add_field(
                name="Check Your Turn",
                value="Use `!my_turn` to see when you can pick",
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        if not movie_input:
            await ctx.send("Please provide a movie name!")
            return

        # Parse movie name and optional year
        movie_name, year = parse_movie_input(movie_input)

        # Show searching message
        search_text = f"**{movie_name}**{f' ({year})' if year else ''}"
        search_msg = await ctx.send(f"🔍 Searching for {search_text}...")

        try:
            # Search for movie
            success, message, movie_details = await self.movie_service.search_movie(
                movie_name, year
            )

            if success and movie_details:
                # Extract movie info for database
                movie_info = self.movie_service.extract_movie_info(movie_details)

                # Add to rotation database
                movie_pick = await self.rotation_service.add_movie_pick(
                    username=username,
                    movie_title=movie_info["title"],
                    movie_year=movie_info["year"],
                    imdb_id=movie_info["imdb_id"],
                    movie_details=movie_info,
                )

                # Get user's real name
                user = await self.rotation_service.get_user_by_username(username)
                real_name = user.real_name if user else username

                # Create movie embed
                embed = create_movie_embed(
                    movie_details, f"🎬 Movie Selected by {real_name}!"
                )
                embed.set_footer(
                    text=f"Movie ID: {movie_pick.id} • Use !rate {movie_pick.id} [1-10] to rate this movie"
                )

                await search_msg.edit(content="", embed=embed)

                # Show congratulations message
                congrats_embed = discord.Embed(
                    title="🎉 Movie Selected!",
                    description=f"Thanks for your pick, {real_name}!\n\nOthers can now rate this movie using `!rate {movie_pick.id} [rating]`",
                    color=0x00FF00,
                )
                await ctx.send(embed=congrats_embed)

            else:
                await search_msg.edit(content=message)

        except Exception as e:
            logger.error(f"Error picking movie for {username}: {e}")
            await search_msg.edit(content=f"❌ Error picking movie: {str(e)}")

    @commands.command(name="current_movie")
    async def current_movie(self, ctx):
        """Display the currently selected movie with details"""
        current = self.movie_service.get_current_movie()

        if not current:
            await ctx.send(
                "No movie has been selected yet. Use `!pick_movie [name]` to pick one!"
            )
            return

        movie_details = self.movie_service.get_current_movie_details()

        if movie_details:
            embed = create_movie_embed(movie_details, "🎬 Current Movie")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"🎬 Current movie: **{current}**")

    @commands.command(name="clear_movie")
    async def clear_movie(self, ctx):
        """Clear the currently selected movie"""
        self.movie_service.clear_current_movie()
        await ctx.send("🗑️ Movie selection cleared!")

    @commands.command(name="movie_status")
    async def movie_status(self, ctx):
        """Quick status of current movie"""
        current = self.movie_service.get_current_movie()

        if current:
            await ctx.send(f"🎬 Current: **{current}**")
        else:
            await ctx.send("🎬 No movie selected")

    @commands.command(name="search_movie")
    async def search_movie(self, ctx, *, movie_input: str):
        """
        Search for a movie without picking it
        Usage: !search_movie The Matrix
               !search_movie The Matrix 1999
        """
        if not movie_input:
            await ctx.send("Please provide a movie name!")
            return

        # Parse movie name and optional year
        movie_name, year = parse_movie_input(movie_input)

        # Show searching message
        search_text = f"**{movie_name}**{f' ({year})' if year else ''}"
        search_msg = await ctx.send(f"🔍 Searching for {search_text}...")

        try:
            # Search for movie
            success, message, movie_details = await self.movie_service.search_movie(
                movie_name, year
            )

            if success and movie_details:
                embed = create_movie_embed(movie_details, "🎬 Movie Found")
                await search_msg.edit(content="", embed=embed)
            else:
                await search_msg.edit(content=message)

        except Exception as e:
            logger.error(f"Error searching movie: {e}")
            await search_msg.edit(content=f"❌ Error searching for movie: {str(e)}")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(MovieCommands(bot))
