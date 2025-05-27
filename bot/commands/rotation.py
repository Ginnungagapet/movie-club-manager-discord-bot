"""
Rotation management commands
"""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class RotationCommands(commands.Cog):
    """Commands for managing movie club rotation"""

    def __init__(self, bot):
        self.bot = bot
        self.rotation_service = bot.services["rotation"]

    @commands.command(name="schedule")
    async def show_schedule(self, ctx, periods: int = 5):
        """Show the upcoming rotation schedule"""
        try:
            embed = await self.rotation_service.create_schedule_embed(periods)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error showing schedule: {e}")
            await ctx.send(f"❌ Error showing schedule: {str(e)}")

    @commands.command(name="who_picks")
    async def who_picks(self, ctx):
        """Show who is currently supposed to pick"""
        try:
            current_user, current_start, current_end = (
                await self.rotation_service.get_current_picker()
            )
            next_user, next_start, next_end = (
                await self.rotation_service.get_next_picker()
            )

            embed = discord.Embed(title="🎯 Current Picker", color=0x00FF00)

            embed.add_field(
                name="Current Period",
                value=f"**{current_user.real_name}**\n📅 {current_start.strftime('%b %d')} - {current_end.strftime('%b %d, %Y')}",
                inline=False,
            )

            # Check if next person has early access
            can_pick_next, reason = await self.rotation_service.can_user_pick(
                next_user.discord_username
            )
            next_status = ""
            if can_pick_next and "Early access" in reason:
                next_status = " 🚪 *Early Access Open*"

            embed.add_field(
                name="Next Up",
                value=f"**{next_user.real_name}**{next_status}\n📅 {next_start.strftime('%b %d')} - {next_end.strftime('%b %d, %Y')}",
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error getting picker info: {e}")
            await ctx.send(f"❌ Error getting picker info: {str(e)}")

    @commands.command(name="my_turn")
    async def check_my_turn(self, ctx):
        """Check if it's your turn to pick"""
        username = ctx.author.name

        try:
            can_pick, reason = await self.rotation_service.can_user_pick(username)

            if can_pick:
                embed = discord.Embed(
                    title="🎯 Your Turn!", description=f"✅ {reason}", color=0x00FF00
                )
                embed.add_field(
                    name="How to Pick",
                    value="Use `!pick_movie [movie name]` to select your movie!",
                    inline=False,
                )
            else:
                embed = discord.Embed(
                    title="⏰ Not Your Turn", description=f"❌ {reason}", color=0xFF6600
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error checking turn for {username}: {e}")
            await ctx.send(f"❌ Error checking turn: {str(e)}")

    @commands.command(name="history")
    async def show_history(self, ctx, limit: int = 10):
        """Show recent movie pick history with ratings"""
        try:
            embed = await self.rotation_service.create_history_embed(limit)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error showing history: {e}")
            await ctx.send(f"❌ Error showing history: {str(e)}")

    @commands.command(name="my_picks")
    async def show_my_picks(self, ctx):
        """Show your movie pick history"""
        username = ctx.author.name

        try:
            picks = await self.rotation_service.get_user_pick_history(username)

            if not picks:
                await ctx.send("You haven't picked any movies yet!")
                return

            embed = discord.Embed(title=f"🎬 Your Movie Picks", color=0x0099FF)

            for pick in picks[:10]:  # Show last 10 picks
                movie_title = pick.movie_title
                if pick.movie_year:
                    movie_title += f" ({pick.movie_year})"

                rating_info = ""
                if hasattr(pick, "average_rating") and pick.average_rating:
                    rating_info = f" ⭐ {pick.average_rating:.1f}/10"

                embed.add_field(
                    name=f"🎬 {movie_title}{rating_info}",
                    value=f"📅 {pick.pick_date.strftime('%b %d, %Y')}",
                    inline=True,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing picks for {username}: {e}")
            await ctx.send(f"❌ Error showing your picks: {str(e)}")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(RotationCommands(bot))
