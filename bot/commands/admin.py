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

    @commands.command(name="skip_current_pick")
    @commands.has_permissions(administrator=True)
    async def skip_current_pick(self, ctx, *, reason: str = None):
        """
        Skip the current picker in the rotation (Admin only)
        The next person will become the current picker immediately.

        Usage: !skip_current_pick
            !skip_current_pick [reason]

        Example: !skip_current_pick Paul is sick
        """
        try:
            # Get current situation before skip
            current_user, current_start, current_end = (
                await self.rotation_service.get_current_picker()
            )

            # Get who will become the new current picker
            next_user, next_start, next_end = (
                await self.rotation_service.get_next_picker()
            )

            # Confirm the skip action
            confirm_embed = discord.Embed(
                title="⚠️ Confirm Skip Current Picker",
                description=(
                    f"This will skip **{current_user.real_name}**'s CURRENT period "
                    f"({current_start.strftime('%b %d')} - {current_end.strftime('%b %d')})\n\n"
                    f"**{next_user.real_name}** will become the current picker immediately."
                ),
                color=0xFF6600,
            )

            # Check if they've already picked
            user_pick = await self.rotation_service.get_user_active_pick(
                current_user.discord_username
            )
            if user_pick:
                movie_title = user_pick.movie_title
                if user_pick.movie_year:
                    movie_title += f" ({user_pick.movie_year})"
                confirm_embed.add_field(
                    name="⚠️ Warning",
                    value=f"{current_user.real_name} has already picked: **{movie_title}**\nThis movie selection will be deleted!",
                    inline=False,
                )

            confirm_embed.add_field(
                name="Type to confirm",
                value="Type `CONFIRM SKIP` within 30 seconds to proceed",
                inline=False,
            )

            if reason:
                confirm_embed.add_field(
                    name="Reason", value=reason, inline=False)

            confirmation_msg = await ctx.send(embed=confirm_embed)

            def check(m):
                return (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content == "CONFIRM SKIP"
                )

            try:
                await self.bot.wait_for("message", check=check, timeout=30.0)
            except:
                await confirmation_msg.edit(
                    content="❌ Skip cancelled (timed out)", embed=None
                )
                return

            # Perform the skip
            success, message, details = await self.rotation_service.skip_picker(
                skipped_by=ctx.author.name, who="current", reason=reason
            )

            if success:
                # Create success embed
                result_embed = discord.Embed(
                    title="✅ Current Picker Skipped",
                    description=message,
                    color=0x00FF00,
                )

                result_embed.add_field(
                    name="Skipped",
                    value=f"{details['skipped_user']}\n{details['skipped_period']}",
                    inline=True,
                )

                # For current skip, show new current picker
                if "new_current_user" in details:
                    result_embed.add_field(
                        name="New Current Picker",
                        value=f"{details['new_current_user']}\n{details.get('new_current_period', '')}",
                        inline=True,
                    )

                if reason:
                    result_embed.add_field(
                        name="Reason", value=reason, inline=False)

                # Show updated schedule
                result_embed.add_field(
                    name="View Updated Schedule",
                    value="Use `!schedule` to see the updated rotation",
                    inline=False,
                )

                await ctx.send(embed=result_embed)

                # Log the skip
                logger.info(
                    f"{ctx.author.name} skipped {details['skipped_user']}'s current period{f' (reason: {reason})' if reason else ''}"
                )

            else:
                error_embed = discord.Embed(
                    title="❌ Skip Failed", description=message, color=0xFF0000
                )
                await ctx.send(embed=error_embed)

        except Exception as e:
            logger.error(f"Error in skip_current_pick command: {e}")
            await ctx.send(f"❌ Error processing skip: {str(e)}")

    @commands.command(name="skip_next_pick")
    @commands.has_permissions(administrator=True)
    async def skip_next_pick(self, ctx, *, reason: str = None):
        """
        Skip the next picker in the rotation (Admin only)
        The person after them will become the next picker instead.

        Usage: !skip_next_pick
            !skip_next_pick [reason]

        Example: !skip_next_pick Derek is out of town
        """
        try:
            # Get current situation
            current_user, current_start, current_end = (
                await self.rotation_service.get_current_picker()
            )

            # Get who would normally be next (before skip)
            next_user, next_start, next_end = (
                await self.rotation_service.get_next_picker()
            )

            # Confirm the skip action
            confirm_embed = discord.Embed(
                title="⚠️ Confirm Skip Next Picker",
                description=(
                    f"This will skip **{next_user.real_name}**'s upcoming period "
                    f"({next_start.strftime('%b %d')} - {next_end.strftime('%b %d')})\n\n"
                    f"The person after them will become the next picker."
                ),
                color=0xFF6600,
            )

            # Check if they've already picked
            user_pick = await self.rotation_service.get_user_active_pick(
                next_user.discord_username
            )
            if user_pick:
                movie_title = user_pick.movie_title
                if user_pick.movie_year:
                    movie_title += f" ({user_pick.movie_year})"
                confirm_embed.add_field(
                    name="⚠️ Warning",
                    value=f"{next_user.real_name} has already picked: **{movie_title}**\nThis movie selection will be deleted!",
                    inline=False,
                )

            confirm_embed.add_field(
                name="Type to confirm",
                value="Type `CONFIRM SKIP` within 30 seconds to proceed",
                inline=False,
            )

            if reason:
                confirm_embed.add_field(
                    name="Reason", value=reason, inline=False)

            confirmation_msg = await ctx.send(embed=confirm_embed)

            def check(m):
                return (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content == "CONFIRM SKIP"
                )

            try:
                await self.bot.wait_for("message", check=check, timeout=30.0)
            except:
                await confirmation_msg.edit(
                    content="❌ Skip cancelled (timed out)", embed=None
                )
                return

            # Perform the skip
            success, message, details = await self.rotation_service.skip_picker(
                skipped_by=ctx.author.name, who="next", reason=reason
            )

            if success:
                # Create success embed
                result_embed = discord.Embed(
                    title="✅ Next Picker Skipped", description=message, color=0x00FF00
                )

                result_embed.add_field(
                    name="Skipped",
                    value=f"{details['skipped_user']}\n{details['skipped_period']}",
                    inline=True,
                )

                result_embed.add_field(
                    name="New Next Picker",
                    value=f"{details['new_next_user']}\n{details['new_next_period']}",
                    inline=True,
                )

                if reason:
                    result_embed.add_field(
                        name="Reason", value=reason, inline=False)

                # Show updated schedule
                result_embed.add_field(
                    name="View Updated Schedule",
                    value="Use `!schedule` to see the updated rotation",
                    inline=False,
                )

                await ctx.send(embed=result_embed)

                # Log the skip
                logger.info(
                    f"{ctx.author.name} skipped {details['skipped_user']}'s upcoming period{f' (reason: {reason})' if reason else ''}"
                )

            else:
                error_embed = discord.Embed(
                    title="❌ Skip Failed", description=message, color=0xFF0000
                )
                await ctx.send(embed=error_embed)

        except Exception as e:
            logger.error(f"Error in skip_next_pick command: {e}")
            await ctx.send(f"❌ Error processing skip: {str(e)}")

    @commands.command(name="list_skips")
    @commands.has_permissions(administrator=True)
    async def list_skips(self, ctx):
        """
        List all skipped periods (Admin only)
        """
        session = self.rotation_service.db.get_session()
        try:
            from models.database import RotationSkip

            skips = (
                session.query(RotationSkip)
                .order_by(RotationSkip.original_start_date.desc())
                .all()
            )

            if not skips:
                await ctx.send("No skipped periods in the rotation history.")
                return

            embed = discord.Embed(
                title="⏭️ Skipped Periods",
                description=f"Total skips: {len(skips)}",
                color=0xFF6600,
            )

            for skip in skips[:10]:  # Show last 10 skips
                skip_info = (
                    f"Period: {skip.original_start_date.strftime('%b %d')} - "
                    f"{skip.original_end_date.strftime('%b %d, %Y')}\n"
                    f"Skipped by: {skip.skipped_by}\n"
                    f"When: {skip.skipped_at.strftime('%b %d, %Y')}"
                )

                if skip.skip_reason:
                    skip_info += f"\nReason: {skip.skip_reason}"

                embed.add_field(
                    name=f"{skip.skipped_user.real_name}", value=skip_info, inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing skips: {e}")
            await ctx.send(f"❌ Error listing skips: {str(e)}")
        finally:
            session.close()

    @commands.command(name="undo_skip")
    @commands.has_permissions(administrator=True)
    async def undo_skip(self, ctx, username: str):
        """
        Undo a skip for a specific user's next skipped period (Admin only)
        Usage: !undo_skip derek
        """
        session = self.rotation_service.db.get_session()
        try:
            from models.database import User, RotationSkip

            # Find the user
            user = session.query(User).filter(
                User.discord_username == username).first()
            if not user:
                await ctx.send(f"❌ User @{username} not found")
                return

            # Find the most recent future skip for this user
            now = datetime.now()
            skip = (
                session.query(RotationSkip)
                .filter(
                    RotationSkip.skipped_user_id == user.id,
                    RotationSkip.original_end_date >= now.date(),
                )
                .order_by(RotationSkip.original_start_date)
                .first()
            )

            if not skip:
                await ctx.send(
                    f"❌ No upcoming skipped periods found for {user.real_name}"
                )
                return

            # Remove the skip
            period_str = f"{skip.original_start_date.strftime('%b %d')} - {skip.original_end_date.strftime('%b %d')}"
            session.delete(skip)
            session.commit()

            embed = discord.Embed(
                title="✅ Skip Removed",
                description=f"Restored {user.real_name}'s period: {period_str}",
                color=0x00FF00,
            )

            embed.add_field(
                name="Note",
                value="The schedule has been updated. Use `!schedule` to view changes.",
                inline=False,
            )

            await ctx.send(embed=embed)
            logger.info(
                f"{ctx.author.name} removed skip for {user.real_name}'s period {period_str}"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error undoing skip: {e}")
            await ctx.send(f"❌ Error undoing skip: {str(e)}")
        finally:
            session.close()

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
                embed.add_field(name="Current Movie",
                                value=movie_text, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            await ctx.send(f"❌ Error getting admin stats: {str(e)}")

    @commands.command(name="add_user")
    @commands.has_permissions(administrator=True)
    async def add_user(self, ctx, discord_tag: str, *, real_name: str):
        """
        Add a new user to the end of the rotation (Admin only)

        Usage: !add_user @username "Real Name"
            !add_user username "Real Name"

        Example: !add_user @john "John Smith"
                !add_user john "John Smith"
        """
        try:
            # Clean up the discord tag (remove @ and any <@> wrapper)
            discord_username = discord_tag.strip()
            if discord_username.startswith("<@") and discord_username.endswith(">"):
                # This is a mention, we need to get the actual username
                user_id = (
                    discord_username.replace(
                        "<@", "").replace(">", "").replace("!", "")
                )
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    discord_username = user.name
                except:
                    await ctx.send(
                        f"❌ Could not find user with that mention. Try using their username directly."
                    )
                    return
            else:
                # Remove @ if present
                discord_username = discord_username.lstrip("@")

            # Validate inputs
            if not discord_username:
                await ctx.send("❌ Please provide a Discord username")
                return

            if not real_name or len(real_name.strip()) < 2:
                await ctx.send("❌ Please provide a valid real name")
                return

            real_name = real_name.strip()

            # Add user to rotation
            success, message, details = (
                await self.rotation_service.add_user_to_rotation(
                    discord_username=discord_username, real_name=real_name
                )
            )

            if success:
                embed = discord.Embed(
                    title="✅ User Added to Rotation",
                    description=message,
                    color=0x00FF00,
                )

                embed.add_field(
                    name="Discord", value=f"@{discord_username}", inline=True
                )

                embed.add_field(name="Name", value=real_name, inline=True)

                embed.add_field(
                    name="Position",
                    value=f"#{details['position']} of {details['total_users']}",
                    inline=True,
                )

                if details.get("first_turn") != "Rotation not started":
                    embed.add_field(
                        name="First Turn", value=details["first_turn"], inline=False
                    )

                embed.add_field(
                    name="Note",
                    value="The new user has been added to the end of the current rotation cycle.",
                    inline=False,
                )

                await ctx.send(embed=embed)

                logger.info(
                    f"{ctx.author.name} added {real_name} (@{discord_username}) to rotation"
                )

            else:
                embed = discord.Embed(
                    title="❌ Failed to Add User", description=message, color=0xFF0000
                )
                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in add_user command: {e}")
            await ctx.send(f"❌ Error adding user: {str(e)}")

    @commands.command(name="remove_user")
    @commands.has_permissions(administrator=True)
    async def remove_user(self, ctx, discord_tag: str):
        """
        Remove a user from active rotation while preserving their historical data (Admin only)
        Their past picks and ratings will be kept for historical records.

        Usage: !remove_user @username
            !remove_user username

        Example: !remove_user @john
                !remove_user john
        """
        try:
            # Clean up the discord tag
            discord_username = discord_tag.strip()
            if discord_username.startswith("<@") and discord_username.endswith(">"):
                # This is a mention, get the actual username
                user_id = (
                    discord_username.replace(
                        "<@", "").replace(">", "").replace("!", "")
                )
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    discord_username = user.name
                except:
                    await ctx.send(
                        f"❌ Could not find user with that mention. Try using their username directly."
                    )
                    return
            else:
                discord_username = discord_username.lstrip("@")

            # Get user info before removal for confirmation
            user_to_remove = await self.rotation_service.get_user_by_username(
                discord_username
            )
            if not user_to_remove:
                await ctx.send(f"❌ User @{discord_username} not found in rotation")
                return

            # Confirmation embed
            confirm_embed = discord.Embed(
                title="⚠️ Confirm User Removal from Active Rotation",
                description=(
                    f"This will remove **{user_to_remove.real_name}** "
                    f"(@{discord_username}) from the active rotation.\n\n"
                    f"**What will happen:**\n"
                    f"• They will be removed from the rotation schedule\n"
                    f"• All subsequent users will shift up one position\n"
                    f"• Any future skips will be removed\n\n"
                    f"**What will be preserved:**\n"
                    f"• ✅ All their movie picks remain in history\n"
                    f"• ✅ All their ratings are kept\n"
                    f"• ✅ Historical records are maintained\n\n"
                    f"They can be reactivated later if needed."
                ),
                color=0xFF6600,
            )

            confirm_embed.add_field(
                name="Type to confirm",
                value="Type `CONFIRM REMOVE` within 30 seconds to proceed",
                inline=False,
            )

            confirmation_msg = await ctx.send(embed=confirm_embed)

            def check(m):
                return (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and m.content == "CONFIRM REMOVE"
                )

            try:
                await self.bot.wait_for("message", check=check, timeout=30.0)
            except:
                await confirmation_msg.edit(
                    content="❌ Removal cancelled (timed out)", embed=None
                )
                return

            # Perform the removal
            success, message, details = (
                await self.rotation_service.remove_user_from_rotation(
                    discord_username=discord_username
                )
            )

            if success:
                result_embed = discord.Embed(
                    title="✅ User Removed from Active Rotation",
                    description=message,
                    color=0x00FF00,
                )

                result_embed.add_field(
                    name="Removed User",
                    value=f"{details['removed_user']} (was position #{details['removed_position']})",
                    inline=False,
                )

                result_embed.add_field(
                    name="Historical Data Preserved",
                    value=(
                        f"• {details['picks_preserved']} movie picks\n"
                        f"• {details['ratings_preserved']} ratings"
                    ),
                    inline=True,
                )

                result_embed.add_field(
                    name="Active Members",
                    value=str(details["remaining_active_users"]),
                    inline=True,
                )

                if details.get("was_current"):
                    result_embed.add_field(
                        name="⚠️ Note",
                        value="This user was the current picker. Run `!who_picks` to see the new current picker.",
                        inline=False,
                    )
                elif details.get("was_next"):
                    result_embed.add_field(
                        name="⚠️ Note",
                        value="This user was the next picker. The schedule has been updated.",
                        inline=False,
                    )
                else:
                    result_embed.add_field(
                        name="Note",
                        value="All users after this position have been shifted up.",
                        inline=False,
                    )

                await ctx.send(embed=result_embed)

                logger.info(
                    f"{ctx.author.name} removed {details['removed_user']} from active rotation"
                )

            else:
                error_embed = discord.Embed(
                    title="❌ Failed to Remove User",
                    description=message,
                    color=0xFF0000,
                )
                await ctx.send(embed=error_embed)

        except Exception as e:
            logger.error(f"Error in remove_user command: {e}")
            await ctx.send(f"❌ Error removing user: {str(e)}")

    @commands.command(name="reactivate_user")
    @commands.has_permissions(administrator=True)
    async def reactivate_user(self, ctx, discord_tag: str, position: int = None):
        """
        Reactivate a previously removed user back into the rotation (Admin only)

        Usage: !reactivate_user @username [position]
            !reactivate_user username [position]

        Example: !reactivate_user @john       # Adds to end
                !reactivate_user @john 3     # Inserts at position 3
        """
        try:
            # Clean up the discord tag
            discord_username = discord_tag.strip()
            if discord_username.startswith("<@") and discord_username.endswith(">"):
                user_id = (
                    discord_username.replace(
                        "<@", "").replace(">", "").replace("!", "")
                )
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    discord_username = user.name
                except:
                    await ctx.send(
                        f"❌ Could not find user with that mention. Try using their username directly."
                    )
                    return
            else:
                discord_username = discord_username.lstrip("@")

            # Convert position to 0-based if provided
            if position is not None:
                if position < 1:
                    await ctx.send("❌ Position must be 1 or greater")
                    return
                position = position - 1  # Convert to 0-based

            # Reactivate the user
            success, message, details = await self.rotation_service.reactivate_user(
                discord_username=discord_username, position=position
            )

            if success:
                embed = discord.Embed(
                    title="✅ User Reactivated", description=message, color=0x00FF00
                )

                embed.add_field(
                    name="User",
                    value=f"{details['real_name']} (@{details['username']})",
                    inline=True,
                )

                embed.add_field(
                    name="New Position",
                    value=f"#{details['position']} of {details['total_active']}",
                    inline=True,
                )

                if details["historical_picks"] > 0:
                    embed.add_field(
                        name="Historical Data",
                        value=f"{details['historical_picks']} previous picks retained",
                        inline=False,
                    )

                embed.add_field(
                    name="Note",
                    value="User has been added back to active rotation. Use `!schedule` to see updated schedule.",
                    inline=False,
                )

                await ctx.send(embed=embed)

                logger.info(
                    f"{ctx.author.name} reactivated {details['real_name']} to position {details['position']}"
                )

            else:
                embed = discord.Embed(
                    title="❌ Failed to Reactivate User",
                    description=message,
                    color=0xFF0000,
                )
                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in reactivate_user command: {e}")
            await ctx.send(f"❌ Error reactivating user: {str(e)}")

    @commands.command(name="list_inactive")
    @commands.has_permissions(administrator=True)
    async def list_inactive(self, ctx):
        """
        List all inactive users who have been removed but have historical data (Admin only)
        """
        try:
            inactive_users = await self.rotation_service.list_inactive_users()

            if not inactive_users:
                await ctx.send("No inactive users with preserved history.")
                return

            embed = discord.Embed(
                title="📋 Inactive Users (Removed from Rotation)",
                description=f"Total: {len(inactive_users)} inactive members with preserved history",
                color=0x808080,
            )

            for user in inactive_users:
                value = f"@{user['username']}"
                if user["picks"] > 0 or user["ratings"] > 0:
                    value += f"\n📊 {user['picks']} picks, {user['ratings']} ratings"

                embed.add_field(name=user["real_name"],
                                value=value, inline=True)

            embed.add_field(
                name="Reactivation",
                value="Use `!reactivate_user @username` to add them back to rotation",
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing inactive users: {e}")
            await ctx.send(f"❌ Error listing inactive users: {str(e)}")

    @commands.command(name="list_users")
    @commands.has_permissions(administrator=True)
    async def list_users(self, ctx):
        """
        List all users in the rotation with their positions (Admin only)
        """
        session = self.rotation_service.db.get_session()
        try:
            # Import models here
            from models.database import User, MoviePick

            users = session.query(User).order_by(User.rotation_position).all()

            if not users:
                await ctx.send(
                    "❌ No users in rotation. Use `!setup_rotation` to add users."
                )
                return

            embed = discord.Embed(
                title="👥 Rotation Members",
                description=f"Total: {len(users)} members",
                color=0x0099FF,
            )

            # Get current and next picker for context
            try:
                current_user, _, _ = await self.rotation_service.get_current_picker()
                next_user, _, _ = await self.rotation_service.get_next_picker()
            except:
                current_user = None
                next_user = None

            for user in users:
                status = ""
                if current_user and user.id == current_user.id:
                    status = " 🎯 **CURRENT**"
                elif next_user and user.id == next_user.id:
                    status = " ⏭️ *Next*"

                # Get pick count for this user
                pick_count = (
                    session.query(MoviePick)
                    .filter(MoviePick.picker_user_id == user.id)
                    .count()
                )

                value = f"@{user.discord_username}"
                if pick_count > 0:
                    value += f"\n📊 {pick_count} pick{'s' if pick_count != 1 else ''}"

                embed.add_field(
                    name=f"#{user.rotation_position + 1}. {user.real_name}{status}",
                    value=value,
                    inline=True,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing users: {e}")
            await ctx.send(f"❌ Error listing users: {str(e)}")
        finally:
            session.close()

    @commands.command(name="swap_users")
    @commands.has_permissions(administrator=True)
    async def swap_users(self, ctx, user1: str, user2: str):
        """
        Swap the rotation positions of two users (Admin only)

        Usage: !swap_users @user1 @user2
            !swap_users username1 username2

        Example: !swap_users @john @jane
                !swap_users john jane
        """
        session = self.rotation_service.db.get_session()
        try:
            # Import User model here
            from models.database import User

            # Clean up usernames
            username1 = user1.strip().lstrip("@")
            username2 = user2.strip().lstrip("@")

            # Handle mentions
            if username1.startswith("<@") and username1.endswith(">"):
                user_id = username1.replace(
                    "<@", "").replace(">", "").replace("!", "")
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username1 = user.name
                except:
                    await ctx.send(f"❌ Could not find first user")
                    return

            if username2.startswith("<@") and username2.endswith(">"):
                user_id = username2.replace(
                    "<@", "").replace(">", "").replace("!", "")
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username2 = user.name
                except:
                    await ctx.send(f"❌ Could not find second user")
                    return

            # Find both users
            user1_obj = (
                session.query(User).filter(
                    User.discord_username == username1).first()
            )
            user2_obj = (
                session.query(User).filter(
                    User.discord_username == username2).first()
            )

            if not user1_obj:
                await ctx.send(f"❌ User @{username1} not found in rotation")
                return

            if not user2_obj:
                await ctx.send(f"❌ User @{username2} not found in rotation")
                return

            # Swap their positions
            pos1 = user1_obj.rotation_position
            pos2 = user2_obj.rotation_position

            user1_obj.rotation_position = pos2
            user2_obj.rotation_position = pos1

            session.commit()

            embed = discord.Embed(
                title="✅ Users Swapped",
                description="Successfully swapped rotation positions",
                color=0x00FF00,
            )

            embed.add_field(
                name=f"{user1_obj.real_name}",
                value=f"Position #{pos1 + 1} → #{pos2 + 1}",
                inline=True,
            )

            embed.add_field(
                name=f"{user2_obj.real_name}",
                value=f"Position #{pos2 + 1} → #{pos1 + 1}",
                inline=True,
            )

            embed.add_field(
                name="Note",
                value="Use `!schedule` to see the updated rotation order",
                inline=False,
            )

            await ctx.send(embed=embed)

            logger.info(
                f"{ctx.author.name} swapped positions of {user1_obj.real_name} and {user2_obj.real_name}"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error swapping users: {e}")
            await ctx.send(f"❌ Error swapping users: {str(e)}")
        finally:
            session.close()

    @commands.command(name="fix_rotation_order")
    @commands.has_permissions(administrator=True)
    async def fix_rotation_order(self, ctx, *, new_order: str):
        """
        Manually fix the rotation order by specifying the correct sequence (Admin only)
        This preserves all historical data and only updates rotation positions.

        Usage: !fix_rotation_order username1,username2,username3,...

        Example: !fix_rotation_order j,kyle,dennis,paul,derek,greg,gavin,baldo
        """
        session = self.rotation_service.db.get_session()
        try:
            # Import User model from database
            from models.database import User

            # Parse the new order
            usernames = [u.strip().lower() for u in new_order.split(",")]

            if len(usernames) < 2:
                await ctx.send(
                    "❌ Please provide at least 2 users in the rotation order"
                )
                return

            # Verify all users exist
            all_users = (
                session.query(User).filter(
                    User.rotation_position.isnot(None)).all()
            )
            existing_usernames = {
                u.discord_username.lower(): u for u in all_users}

            # Check for missing users
            for username in usernames:
                if username not in existing_usernames:
                    await ctx.send(f"❌ User @{username} not found in active rotation")
                    return

            # Check if we're missing anyone
            missing = []
            for existing_username in existing_usernames:
                if existing_username not in usernames:
                    missing.append(existing_username)

            if missing:
                await ctx.send(
                    f"⚠️ These active users were not included: {', '.join(missing)}\nContinue anyway? Type `YES` to proceed"
                )

                def check(m):
                    return (
                        m.author == ctx.author
                        and m.channel == ctx.channel
                        and m.content == "YES"
                    )

                try:
                    await self.bot.wait_for("message", check=check, timeout=30.0)
                except:
                    await ctx.send("❌ Operation cancelled")
                    return

            # Update rotation positions
            for new_position, username in enumerate(usernames):
                user = existing_usernames[username]
                user.rotation_position = new_position

            session.commit()

            # Create confirmation embed
            embed = discord.Embed(
                title="✅ Rotation Order Fixed",
                description=f"Updated rotation positions for {len(usernames)} users",
                color=0x00FF00,
            )

            # Show the new order
            order_text = ""
            for i, username in enumerate(usernames, 1):
                user = existing_usernames[username]
                order_text += f"#{i}. {user.real_name} (@{user.discord_username})\n"

            embed.add_field(
                name="New Rotation Order",
                value=order_text[:1024],  # Truncate if too long
                inline=False,
            )

            embed.add_field(
                name="Important",
                value="Run `!schedule` to verify the rotation looks correct",
                inline=False,
            )

            await ctx.send(embed=embed)

            logger.info(f"{ctx.author.name} manually fixed rotation order")

        except Exception as e:
            session.rollback()
            logger.error(f"Error fixing rotation order: {e}")
            await ctx.send(f"❌ Error fixing rotation order: {str(e)}")
        finally:
            session.close()

    @commands.command(name="set_rotation_date")
    @commands.has_permissions(administrator=True)
    async def set_rotation_date(self, ctx, *, date_str: str):
        """
        Manually set the rotation start date (Admin only)
        This is useful for fixing timing issues.

        Usage: !set_rotation_date October 6, 2025
            !set_rotation_date 2025-10-06
        """
        try:
            from utils.date_utils import parse_date

            new_date = parse_date(date_str)
            if not new_date:
                await ctx.send(
                    "❌ Invalid date format. Try: 'October 6, 2025' or '2025-10-06'"
                )
                return

            # Update the rotation start date
            await self.rotation_service.update_rotation_start_date(new_date)

            embed = discord.Embed(
                title="✅ Rotation Start Date Updated",
                description=f"Rotation now starts on {new_date.strftime('%B %d, %Y')}",
                color=0x00FF00,
            )

            embed.add_field(
                name="Note",
                value="Run `!schedule` to see the updated schedule",
                inline=False,
            )

            await ctx.send(embed=embed)

            logger.info(
                f"{ctx.author.name} set rotation start date to {new_date}")

        except Exception as e:
            logger.error(f"Error setting rotation date: {e}")
            await ctx.send(f"❌ Error setting rotation date: {str(e)}")


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(AdminCommands(bot))
