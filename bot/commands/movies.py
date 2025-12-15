"""
Movie selection and management commands (Updated - No Movie ID references)
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
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
        Pick a movie (only allowed during your turn or early access)
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
                movie_info = self.movie_service.extract_movie_info(
                    movie_details)

                # Determine if this is an early access pick
                current_user, current_start, current_end = (
                    await self.rotation_service.get_current_picker()
                )
                user = await self.rotation_service.get_user_by_username(username)

                is_early_access = (
                    user.id != current_user.id and "Early access" in reason
                )

                # Add or update movie pick
                movie_pick = await self.rotation_service.add_or_update_movie_pick(
                    username=username,
                    movie_title=movie_info["title"],
                    movie_year=movie_info["year"],
                    imdb_id=movie_info["imdb_id"],
                    movie_details=movie_info,
                    is_early_access=is_early_access,
                )

                # Get user's real name
                real_name = user.real_name if user else username

                # Create movie embed
                embed_title = (
                    "🎬 Movie Selected!"
                    if not is_early_access
                    else "🎬 Movie Pre-Selected!"
                )
                embed = create_movie_embed(movie_details, embed_title)

                # Update footer to show how to rate
                movie_title_for_rating = movie_info["title"]
                if is_early_access:
                    embed.set_footer(
                        text=f"This movie will be set when your period starts. You can still change it before then."
                    )
                else:
                    embed.set_footer(
                        text=f"Rate this movie: !rate [1.0-10.0] {movie_title_for_rating}"
                    )

                await search_msg.edit(content="", embed=embed)

                # Show appropriate message
                if is_early_access:
                    next_user, next_start, next_end = (
                        await self.rotation_service.get_next_picker()
                    )
                    days_until = (next_start - datetime.now()).days

                    congrats_embed = discord.Embed(
                        title="🎉 Movie Pre-Selected!",
                        description=f"Thanks for using early access, {real_name}!\n\nYour movie will be set as the current pick in {days_until} days when your period starts.\n\nYou can change your selection anytime before then by using `!pick_movie` again.",
                        color=0x00FF00,
                    )
                else:
                    congrats_embed = discord.Embed(
                        title="🎉 Movie Selected!",
                        description=f"Thanks for your pick, {real_name}!\n\nOthers can now rate this movie using `!rate [rating] {movie_title_for_rating}`",
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
        try:
            # Get the current picker's movie
            current_movie_pick = await self.rotation_service.get_current_movie_pick()

            if not current_movie_pick:
                current_user, _, _ = await self.rotation_service.get_current_picker()
                await ctx.send(
                    f"No movie has been selected yet. {current_user.real_name} (@{current_user.discord_username}) needs to pick a movie!\n"
                    f"Use `!pick_movie [name]` to pick one!"
                )
                return

            # Get movie details from the pick
            movie_details = current_movie_pick.movie_details

            if movie_details:
                # Convert stored movie details to format expected by create_movie_embed
                embed = create_movie_embed(movie_details, "🎬 Current Movie")
                # Add rating instruction
                embed.set_footer(
                    text=f"Rate this movie: !rate [1.0-10.0] {current_movie_pick.movie_title}"
                )

                # Add picker info
                picker_text = f"Picked by {current_movie_pick.picker.real_name}"
                if current_movie_pick.pick_date:
                    picker_text += (
                        f" on {current_movie_pick.pick_date.strftime('%b %d, %Y')}"
                    )
                embed.add_field(name="Selected By",
                                value=picker_text, inline=False)

                await ctx.send(embed=embed)
            else:
                # Fallback if no detailed info
                movie_title = current_movie_pick.movie_title
                if current_movie_pick.movie_year:
                    movie_title += f" ({current_movie_pick.movie_year})"

                embed = discord.Embed(
                    title="🎬 Current Movie",
                    description=f"**{movie_title}**",
                    color=0x00FF00,
                )
                embed.add_field(
                    name="Selected By",
                    value=f"{current_movie_pick.picker.real_name}",
                    inline=False,
                )
                embed.set_footer(
                    text=f"Rate this movie: !rate [1.0-10.0] {current_movie_pick.movie_title}"
                )

                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing current movie: {e}")
            await ctx.send(f"❌ Error showing current movie: {str(e)}")

    @commands.command(name="movie_status")
    async def movie_status(self, ctx):
        """Quick status of current movie"""
        try:
            current_movie_pick = await self.rotation_service.get_current_movie_pick()

            if current_movie_pick:
                movie_title = current_movie_pick.movie_title
                if current_movie_pick.movie_year:
                    movie_title += f" ({current_movie_pick.movie_year})"
                await ctx.send(
                    f"🎬 Current: **{movie_title}** (picked by {current_movie_pick.picker.real_name})"
                )
            else:
                current_user, _, _ = await self.rotation_service.get_current_picker()
                await ctx.send(
                    f"🎬 No movie selected - waiting for {current_user.real_name} to pick"
                )
        except Exception as e:
            logger.error(f"Error getting movie status: {e}")
            await ctx.send("❌ Error getting movie status")

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
                embed.set_footer(text="Movie information from IMDB")
                await search_msg.edit(content="", embed=embed)
            else:
                await search_msg.edit(content=message)

        except Exception as e:
            logger.error(f"Error searching movie: {e}")
            await search_msg.edit(content=f"❌ Error searching for movie: {str(e)}")

    @commands.command(name="my_pick")
    async def my_pick(self, ctx):
        """Show your current/upcoming movie pick"""
        username = ctx.author.name

        try:
            # Get user's active pick (either current or future)
            user_pick = await self.rotation_service.get_user_active_pick(username)

            if not user_pick:
                await ctx.send(
                    "You haven't picked a movie for your current/upcoming period."
                )
                return

            movie_title = user_pick.movie_title
            if user_pick.movie_year:
                movie_title += f" ({user_pick.movie_year})"

            # Check if it's a future pick
            current_user, _, _ = await self.rotation_service.get_current_picker()
            user = await self.rotation_service.get_user_by_username(username)

            if user.id != current_user.id:
                # It's a future pick
                embed = discord.Embed(
                    title="🎬 Your Upcoming Pick",
                    description=f"**{movie_title}**",
                    color=0x0099FF,
                )
                embed.add_field(
                    name="Status",
                    value="Pre-selected during early access. This will become the current movie when your period starts.",
                    inline=False,
                )
                embed.add_field(
                    name="Want to change it?",
                    value="Use `!pick_movie [new movie]` to select a different movie.",
                    inline=False,
                )
            else:
                # It's the current pick
                embed = discord.Embed(
                    title="🎬 Your Current Pick",
                    description=f"**{movie_title}**",
                    color=0x00FF00,
                )
                embed.add_field(
                    name="Status",
                    value="This is the current movie for the club!",
                    inline=False,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing user pick: {e}")
            await ctx.send(f"❌ Error showing your pick: {str(e)}")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(MovieCommands(bot))
