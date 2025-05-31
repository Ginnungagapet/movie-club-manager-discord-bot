"""
Administrator commands for movie club management
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdminCommands(commands.Cog):
    """Administrative commands for movie club management"""

    def __init__(self, bot):
        self.bot = bot
        self.rotation_service = bot.services["rotation"]
        self.movie_service = bot.services["movie"]
        self.rating_service = bot.services["rating"]

    @commands.command(name="setup_rotation")
    @commands.has_permissions(administrator=True)
    async def setup_rotation(self, ctx, *, user_list: str):
        """
        Setup the rotation order (Admin only)
        Usage: !setup_rotation user1:RealName1,user2:RealName2,user3:RealName3
        """
        try:
            # Parse the user list
            user_data = []

            for pair in user_list.split(","):
                if ":" in pair:
                    username, real_name = pair.strip().split(":", 1)
                    user_data.append((username.strip(), real_name.strip()))
                else:
                    username = pair.strip()
                    user_data.append((username, username))

            # Setup rotation with May 5th, 2025 as start date
            await self.rotation_service.setup_rotation(user_data)

            # Set the specific start date to May 5th, 2025
            may_5_2025 = datetime(2025, 5, 5)
            await self.rotation_service.update_rotation_start_date(may_5_2025)

            embed = discord.Embed(
                title="✅ Rotation Setup Complete",
                description=f"Set up rotation for {len(user_data)} members\nRotation started: May 5, 2025",
                color=0x00FF00,
            )

            for i, (username, real_name) in enumerate(user_data, 1):
                embed.add_field(
                    name=f"#{i} {real_name}", value=f"@{username}", inline=True
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error setting up rotation: {e}")
            await ctx.send(f"❌ Error setting up rotation: {str(e)}")

    @commands.command(name="advance_rotation")
    @commands.has_permissions(administrator=True)
    async def advance_rotation(self, ctx):
        """Manually advance to the next person in rotation (Admin only)"""
        await ctx.send(
            "❌ Manual rotation advancement is no longer supported. The rotation advances automatically based on time."
        )

    @commands.command(name="add_historical_pick")
    @commands.has_permissions(administrator=True)
    async def add_historical_pick(
        self,
        ctx,
        username: str,
        movie_title: str,
        movie_year: int = None,
        *,
        pick_date_str: str = None,
    ):
        """
        Add a historical movie pick (Admin only)
        Usage: !add_historical_pick paul "Event Horizon" 1997 "May 10, 2025"
               !add_historical_pick derek "Sunshine" 2007 "May 25, 2025"
        """
        try:
            # Parse the pick date if provided
            if pick_date_str:
                from utils.date_utils import parse_date

                pick_date = parse_date(pick_date_str)
                if not pick_date:
                    await ctx.send(
                        "❌ Invalid date format. Try: 'May 10, 2025' or '2025-05-10'"
                    )
                    return
            else:
                pick_date = datetime.now()

            # Get the user
            user = await self.rotation_service.get_user_by_username(username)
            if not user:
                await ctx.send(f"❌ User @{username} not found in rotation")
                return

            # Calculate which period this pick should belong to based on the date

            # Add historical pick with calculated period
            movie_pick = await self.rotation_service.add_historical_pick(
                username, movie_title, movie_year, pick_date
            )

            embed = discord.Embed(
                title="✅ Historical Pick Added",
                description=f"Added **{movie_title}**{f' ({movie_year})' if movie_year else ''} to history",
                color=0x00FF00,
            )

            embed.add_field(
                name="Picker",
                value=f"{user.real_name} (@{user.discord_username})",
                inline=True,
            )
            embed.add_field(
                name="Pick Date", value=pick_date.strftime("%b %d, %Y"), inline=True
            )
            embed.add_field(
                name="Movie Added",
                value=f"Use `!rate [1.0-10.0] {movie_pick.movie_title}` to rate this movie",
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error adding historical pick: {e}")
            await ctx.send(f"❌ Error adding historical pick: {str(e)}")

    @commands.command(name="delete_pick")
    @commands.has_permissions(administrator=True)
    async def delete_pick(self, ctx, movie_id: int):
        """Delete a movie pick by ID (Admin only)"""
        try:
            success = await self.rotation_service.delete_movie_pick(movie_id)

            if success:
                embed = discord.Embed(
                    title="✅ Movie Pick Deleted",
                    description=f"Deleted movie pick with ID {movie_id}",
                    color=0x00FF00,
                )
            else:
                embed = discord.Embed(
                    title="❌ Movie Pick Not Found",
                    description=f"No movie pick found with ID {movie_id}",
                    color=0xFF0000,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error deleting pick {movie_id}: {e}")
            await ctx.send(f"❌ Error deleting pick: {str(e)}")

    @commands.command(name="force_pick")
    @commands.has_permissions(administrator=True)
    async def force_pick(self, ctx, username: str, *, movie_input: str):
        """Force a movie pick for any user (Admin only)"""
        try:
            from utils.parsers import parse_movie_input

            # Parse movie input
            movie_name, year = parse_movie_input(movie_input)

            # Get user
            user = await self.rotation_service.get_user_by_username(username)
            if not user:
                await ctx.send(f"❌ User @{username} not found")
                return

            # Search for movie
            search_msg = await ctx.send(f"🔍 Searching for **{movie_name}**...")
            success, message, movie_details = await self.movie_service.search_movie(
                movie_name, year
            )

            if not success or not movie_details:
                await search_msg.edit(content=message)
                return

            # Extract movie info
            movie_info = self.movie_service.extract_movie_info(movie_details)

            # Determine the period for this user
            current_user, current_start, current_end = (
                await self.rotation_service.get_current_picker()
            )

            # Force the pick for the appropriate period
            if user.id == current_user.id:
                # Current picker
                movie_pick = await self.rotation_service.add_or_update_movie_pick(
                    username=username,
                    movie_title=movie_info["title"],
                    movie_year=movie_info["year"],
                    imdb_id=movie_info["imdb_id"],
                    movie_details=movie_info,
                    is_early_access=False,
                )
                period_text = "current period"
            else:
                # Check if they're next
                next_user, _, _ = await self.rotation_service.get_next_picker()
                if user.id == next_user.id:
                    movie_pick = await self.rotation_service.add_or_update_movie_pick(
                        username=username,
                        movie_title=movie_info["title"],
                        movie_year=movie_info["year"],
                        imdb_id=movie_info["imdb_id"],
                        movie_details=movie_info,
                        is_early_access=True,
                    )
                    period_text = "next period (early access)"
                else:
                    await search_msg.edit(
                        content=f"❌ {user.real_name} is not current or next in rotation. Use `!add_historical_pick` for past picks."
                    )
                    return

            embed = discord.Embed(
                title="✅ Movie Pick Forced",
                description=f"Set **{movie_info['title']}** as {user.real_name}'s pick for {period_text}",
                color=0x00FF00,
            )

            await search_msg.edit(content="", embed=embed)

        except Exception as e:
            logger.error(f"Error forcing pick: {e}")
            await ctx.send(f"❌ Error forcing pick: {str(e)}")

    @commands.command(name="reset_rotation")
    @commands.has_permissions(administrator=True)
    async def reset_rotation(self, ctx):
        """Reset the entire rotation (Admin only)"""
        # Require confirmation
        embed = discord.Embed(
            title="⚠️ Reset Rotation",
            description="This will delete ALL rotation data including picks and ratings!\n\nType `CONFIRM RESET` to proceed.",
            color=0xFF6600,
        )

        confirmation_msg = await ctx.send(embed=embed)

        def check(m):
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content == "CONFIRM RESET"
            )

        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except:
            await confirmation_msg.edit(
                content="❌ Reset cancelled (timed out)", embed=None
            )
            return

        try:
            await self.rotation_service.reset_all_data()

            embed = discord.Embed(
                title="✅ Rotation Reset Complete",
                description="All rotation data has been cleared. Use `!setup_rotation` to start fresh.",
                color=0x00FF00,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error resetting rotation: {e}")
            await ctx.send(f"❌ Error resetting rotation: {str(e)}")

    @commands.command(name="admin_stats")
    @commands.has_permissions(administrator=True)
    async def admin_stats(self, ctx):
        """Show admin statistics (Admin only)"""
        try:
            stats = await self.rotation_service.get_admin_stats()

            embed = discord.Embed(title="📊 Admin Statistics", color=0x0099FF)

            embed.add_field(
                name="Users",
                value=f"Total: {stats['total_users']}\nActive: {stats['active_users']}",
                inline=True,
            )

            embed.add_field(
                name="Movies",
                value=f"Total Picks: {stats['total_picks']}\nRated Movies: {stats['rated_movies']}",
                inline=True,
            )

            embed.add_field(
                name="Ratings",
                value=f"Total: {stats['total_ratings']}\nAvg Rating: {stats['average_rating']:.1f}/10",
                inline=True,
            )

            embed.add_field(
                name="Current Rotation",
                value=f"Period: {stats['current_period']}\nDays Remaining: {stats['days_remaining']}",
                inline=False,
            )

            # Add current movie info
            current_pick = await self.rotation_service.get_current_movie_pick()
            if current_pick:
                movie_text = current_pick.movie_title
                if current_pick.movie_year:
                    movie_text += f" ({current_pick.movie_year})"
                embed.add_field(name="Current Movie", value=movie_text, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            await ctx.send(f"❌ Error getting admin stats: {str(e)}")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(AdminCommands(bot))
