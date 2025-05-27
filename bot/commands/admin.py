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
        try:
            success = await self.rotation_service.advance_rotation()

            if success:
                current_user, current_start, current_end = (
                    await self.rotation_service.get_current_picker()
                )

                embed = discord.Embed(
                    title="⏭️ Rotation Advanced",
                    description=f"Now it's **{current_user.real_name}**'s turn (@{current_user.discord_username})",
                    color=0x00FF00,
                )
                embed.add_field(
                    name="Period",
                    value=f"{current_start.strftime('%b %d')} - {current_end.strftime('%b %d, %Y')}",
                    inline=False,
                )

                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Error advancing rotation")

        except Exception as e:
            logger.error(f"Error advancing rotation: {e}")
            await ctx.send(f"❌ Error advancing rotation: {str(e)}")

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

            # Add historical pick
            movie_pick = await self.rotation_service.add_historical_pick(
                username, movie_title, movie_year, pick_date
            )

            user = await self.rotation_service.get_user_by_username(username)

            embed = discord.Embed(
                title="✅ Historical Pick Added",
                description=f"Added **{movie_title}**{f' ({movie_year})' if movie_year else ''} to history",
                color=0x00FF00,
            )

            embed.add_field(
                name="Picker",
                value=(
                    f"{user.real_name} (@{user.discord_username})" if user else username
                ),
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
        """Delete a movie pick (Admin only)"""
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

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            await ctx.send(f"❌ Error getting admin stats: {str(e)}")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(AdminCommands(bot))
