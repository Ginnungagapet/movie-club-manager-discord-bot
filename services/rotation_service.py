"""
Rotation service for managing movie club scheduling (FIXED)
"""

import discord
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from models.database import DatabaseManager, User, MoviePick, MovieRating, RotationState

logger = logging.getLogger(__name__)


class RotationService:
    """Service for managing movie club rotation logic"""

    def __init__(self, settings):
        self.settings = settings
        self.db = DatabaseManager(settings.database_url_corrected)

    async def initialize_database(self):
        """Initialize database tables and state"""
        try:
            self.db.create_tables()
            self.db.init_rotation_state()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def setup_rotation(self, user_data: List[Tuple[str, str]]):
        """Set up the rotation with user data"""
        session = self.db.get_session()
        try:
            # Clear existing users
            session.query(User).delete()

            # Add new users with rotation positions
            for position, (username, real_name) in enumerate(user_data):
                user = User(
                    discord_username=username,
                    real_name=real_name,
                    rotation_position=position,
                )
                session.add(user)

            session.commit()
            logger.info(f"Set up rotation with {len(user_data)} users")

        except Exception as e:
            session.rollback()
            logger.error(f"Error setting up rotation: {e}")
            raise
        finally:
            session.close()

    async def update_rotation_start_date(self, start_date: datetime):
        """Update the rotation start date"""
        session = self.db.get_session()
        try:
            # Get users ordered by rotation position
            users = session.query(User).order_by(User.rotation_position).all()
            if not users:
                raise ValueError("No users in rotation")

            # Update rotation state
            rotation_state = session.query(RotationState).first()
            if not rotation_state:
                rotation_state = RotationState(id=1)
                session.add(rotation_state)

            rotation_state.rotation_start_date = start_date
            rotation_state.current_user_id = users[0].id

            session.commit()
            logger.info(f"Updated rotation start date to {start_date}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating start date: {e}")
            raise
        finally:
            session.close()

    async def skip_picker(
        self, skipped_by: str, who: str, reason: str = None
    ) -> tuple[bool, str, dict]:
        """
        Skip the current or next picker in the rotation

        Args:
            skipped_by: Discord username of person initiating skip
            who: "current" or "next" - which picker to skip
            reason: Optional reason for the skip

        Returns:
            Tuple of (success, message, details_dict)
        """
        session = self.db.get_session()
        try:
            from models.database import RotationSkip

            # Get current and next pickers
            current_user, current_start, current_end = await self.get_current_picker()
            users = session.query(User).order_by(User.rotation_position).all()

            if not users:
                return False, "No users in rotation", {}

            if who == "current":
                # Skip the current picker
                user_to_skip = current_user
                skip_start = current_start
                skip_end = current_end

                # Store the user's name before we commit
                skipped_user_name = user_to_skip.real_name

            elif who == "next":
                # Skip the next picker
                next_user, next_start, next_end = await self.get_next_picker()
                user_to_skip = next_user
                skip_start = next_start
                skip_end = next_end

                # Store the user's name before we commit
                skipped_user_name = user_to_skip.real_name

            else:
                return False, "Must specify 'current' or 'next' for who parameter", {}

            # Get the user from our session (not from the other method's session)
            user_to_skip_in_session = (
                session.query(User).filter(User.id == user_to_skip.id).first()
            )

            if not user_to_skip_in_session:
                return False, f"User not found in database", {}

            # Check if this period is already skipped
            existing_skip = (
                session.query(RotationSkip)
                .filter(
                    RotationSkip.skipped_user_id == user_to_skip_in_session.id,
                    RotationSkip.original_start_date == skip_start.date(),
                    RotationSkip.original_end_date == skip_end.date(),
                )
                .first()
            )

            if existing_skip:
                return (
                    False,
                    f"{skipped_user_name}'s period is already skipped",
                    {},
                )

            # Check if the user has already picked for the period being skipped
            existing_pick = (
                session.query(MoviePick)
                .filter(
                    MoviePick.picker_user_id == user_to_skip_in_session.id,
                    MoviePick.period_start_date == skip_start.date(),
                    MoviePick.period_end_date == skip_end.date(),
                )
                .first()
            )

            if existing_pick:
                movie_title = existing_pick.movie_title
                if existing_pick.movie_year:
                    movie_title += f" ({existing_pick.movie_year})"

                # Delete the pick since we're skipping this period
                session.delete(existing_pick)
                logger.info(f"Deleted movie pick '{movie_title}' due to skip")

            # Create the skip record
            skip_record = RotationSkip(
                skipped_user_id=user_to_skip_in_session.id,
                original_start_date=skip_start.date(),
                original_end_date=skip_end.date(),
                skip_reason=reason,
                skipped_by=skipped_by,
            )

            session.add(skip_record)
            session.commit()

            # Store the skip period info before closing session
            skip_period_str = (
                f"{skip_start.strftime('%b %d')} - {skip_end.strftime('%b %d')}"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error skipping picker: {e}")
            return False, f"Error skipping picker: {str(e)}", {}
        finally:
            session.close()

        # Now get the new picker info in a fresh session/query
        try:
            if who == "current":
                # After skipping current, get the new current picker
                new_current_user, new_current_start, new_current_end = (
                    await self.get_current_picker()
                )

                details = {
                    "skipped_user": skipped_user_name,
                    "skipped_period": skip_period_str,
                    "new_current_user": new_current_user.real_name,
                    "new_current_period": f"{new_current_start.strftime('%b %d')} - {new_current_end.strftime('%b %d')}",
                }

                message = (
                    f"✅ Skipped {skipped_user_name}'s current period.\n"
                    f"Current picker is now {new_current_user.real_name}"
                )

            else:  # who == "next"
                # After skipping next, get the new next picker
                new_next_user, new_next_start, new_next_end = (
                    await self.get_next_picker()
                )

                details = {
                    "skipped_user": skipped_user_name,
                    "skipped_period": skip_period_str,
                    "new_next_user": new_next_user.real_name,
                    "new_next_period": f"{new_next_start.strftime('%b %d')} - {new_next_end.strftime('%b %d')}",
                }

                message = (
                    f"✅ Skipped {skipped_user_name}'s upcoming period.\n"
                    f"Next picker is now {new_next_user.real_name}"
                )

            logger.info(f"Skipped {skipped_user_name}'s period ({skip_period_str})")
            return True, message, details

        except Exception as e:
            logger.error(f"Error getting new picker info after skip: {e}")
            # Even if we can't get the new picker info, the skip was successful
            return (
                True,
                f"✅ Skip successful, but could not retrieve new picker info",
                {"skipped_user": skipped_user_name, "skipped_period": skip_period_str},
            )

    async def get_skips_for_period(
        self, start_date: datetime, end_date: datetime
    ) -> list:
        """Get all skips that affect periods before the given date range"""
        session = self.db.get_session()
        try:
            from models.database import RotationSkip

            skips = (
                session.query(RotationSkip)
                .filter(RotationSkip.original_start_date <= end_date.date())
                .all()
            )

            return skips
        finally:
            session.close()

    async def count_skips_before_position(
        self, position: int, periods_elapsed: int
    ) -> int:
        """Count how many skips have occurred that affect the rotation up to this point"""
        session = self.db.get_session()
        try:
            from models.database import RotationSkip

            rotation_state = session.query(RotationState).first()
            if not rotation_state or not rotation_state.rotation_start_date:
                return 0

            start_date = rotation_state.rotation_start_date
            users = session.query(User).order_by(User.rotation_position).all()

            if not users:
                return 0

            total_skips = 0

            # Check each period up to the current one for skips
            for period_num in range(periods_elapsed + 1):
                period_start = start_date + timedelta(days=period_num * 14)
                period_end = period_start + timedelta(days=14)

                # Check if this period was skipped
                skip_exists = (
                    session.query(RotationSkip)
                    .filter(
                        RotationSkip.original_start_date == period_start.date(),
                        RotationSkip.original_end_date == period_end.date(),
                    )
                    .first()
                )

                if skip_exists:
                    total_skips += 1

            return total_skips

        finally:
            session.close()

    async def get_current_picker(self) -> Tuple[User, datetime, datetime]:
        """Get current picker information, accounting for skips"""
        session = self.db.get_session()
        try:
            from models.database import RotationSkip

            rotation_state = session.query(RotationState).first()
            if not rotation_state or not rotation_state.rotation_start_date:
                raise ValueError("No rotation state set up")

            now = datetime.now()
            start_date = rotation_state.rotation_start_date
            days_since_start = (now - start_date).days

            users = session.query(User).order_by(User.rotation_position).all()
            if not users:
                raise ValueError("No users in rotation")

            # We need to figure out who the current picker is by checking each period
            # and accounting for skips
            current_period_start = start_date
            position_index = 0

            while current_period_start <= now:
                current_period_end = current_period_start + timedelta(days=14)
                current_user = users[position_index % len(users)]

                # Check if this period was skipped
                skip_exists = (
                    session.query(RotationSkip)
                    .filter(
                        RotationSkip.skipped_user_id == current_user.id,
                        RotationSkip.original_start_date == current_period_start.date(),
                        RotationSkip.original_end_date == current_period_end.date(),
                    )
                    .first()
                )

                if not skip_exists and current_period_start <= now < current_period_end:
                    # This is our current period
                    if rotation_state.current_user_id != current_user.id:
                        rotation_state.current_user_id = current_user.id
                        session.commit()

                    return current_user, current_period_start, current_period_end

                # Move to next period
                if not skip_exists:
                    # Only advance the position if this period wasn't skipped
                    current_period_start = current_period_end
                position_index += 1

            # Shouldn't reach here, but fallback to calculated position
            periods_passed = days_since_start // 14
            current_position = periods_passed % len(users)
            current_user = users[current_position]
            current_period_start = start_date + timedelta(days=periods_passed * 14)
            current_period_end = current_period_start + timedelta(days=14)

            return current_user, current_period_start, current_period_end

        finally:
            session.close()

    async def get_next_picker(self) -> Tuple[User, datetime, datetime]:
        """Get next picker information, accounting for skips"""
        session = self.db.get_session()
        try:
            from models.database import RotationSkip

            current_user, _, current_end = await self.get_current_picker()
            users = session.query(User).order_by(User.rotation_position).all()

            if not users:
                raise ValueError("No users in rotation")

            # Start checking from the next position after current
            check_position = (current_user.rotation_position + 1) % len(users)
            check_start = current_end

            # Keep checking until we find a non-skipped period
            attempts = 0  # Prevent infinite loop
            while attempts < len(users) * 2:
                check_end = check_start + timedelta(days=14)
                check_user = users[check_position % len(users)]

                # Check if this period is skipped
                skip_exists = (
                    session.query(RotationSkip)
                    .filter(
                        RotationSkip.skipped_user_id == check_user.id,
                        RotationSkip.original_start_date == check_start.date(),
                        RotationSkip.original_end_date == check_end.date(),
                    )
                    .first()
                )

                if not skip_exists:
                    # Found the next non-skipped period
                    return check_user, check_start, check_end

                # This period is skipped, move to next
                check_position = (check_position + 1) % len(users)
                attempts += 1

            # Fallback (shouldn't happen)
            raise ValueError("Unable to find next picker after checking all positions")

        finally:
            session.close()

    async def can_user_pick(self, username: str) -> Tuple[bool, str]:
        """Check if user can pick a movie right now"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return False, f"User {username} is not in the rotation"

            current_user, current_start, current_end = await self.get_current_picker()
            next_user, next_start, next_end = await self.get_next_picker()

            now = datetime.now()

            # Current picker can always pick during their period
            if user.id == current_user.id and current_start <= now <= current_end:
                return True, "You are the current picker"

            # Next picker can pick during early access window
            if user.id == next_user.id:
                early_access_start = next_start - timedelta(days=7)
                if early_access_start <= now < next_start:
                    days_until = (next_start - now).days
                    return (
                        True,
                        f"Early access window (your period starts in {days_until} days)",
                    )
                elif next_start <= now <= next_end:
                    return True, "You are the current picker"

            # Not their turn
            if user.id == current_user.id:
                return False, "Your picking period hasn't started yet"
            elif user.id == next_user.id:
                early_access_start = next_start - timedelta(days=7)
                days_until_access = (early_access_start - now).days
                return False, f"Your early access starts in {days_until_access} days"
            else:
                return False, "It's not your turn in the rotation"

        finally:
            session.close()

    async def add_movie_pick(
        self,
        username: str,
        movie_title: str,
        movie_year: int = None,
        imdb_id: str = None,
        movie_details: dict = None,
    ) -> MoviePick:
        """
        DEPRECATED: Use add_or_update_movie_pick instead
        This method is kept for backward compatibility
        """
        logger.warning("add_movie_pick is deprecated, use add_or_update_movie_pick")
        return await self.add_or_update_movie_pick(
            username=username,
            movie_title=movie_title,
            movie_year=movie_year,
            imdb_id=imdb_id,
            movie_details=movie_details,
            is_early_access=False,
        )

    async def add_historical_pick(
        self,
        username: str,
        movie_title: str,
        movie_year: int = None,
        pick_date: datetime = None,
    ) -> MoviePick:
        """Add a historical movie pick with custom date"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                raise ValueError(f"User {username} not found")

            # Calculate period dates based on user's position and rotation start
            rotation_state = session.query(RotationState).first()
            if not rotation_state:
                raise ValueError("No rotation start date set")

            start_date = rotation_state.rotation_start_date
            user_position = user.rotation_position

            period_start = start_date + timedelta(days=14 * user_position)
            period_end = period_start + timedelta(days=14)

            movie_pick = MoviePick(
                picker_user_id=user.id,
                movie_title=movie_title,
                movie_year=movie_year,
                pick_date=pick_date or datetime.now(),
                period_start_date=period_start.date(),
                period_end_date=period_end.date(),
                movie_details={},
            )

            session.add(movie_pick)
            session.commit()
            session.refresh(movie_pick)

            logger.info(f"Added historical pick: {movie_title} by {username}")
            return movie_pick

        except Exception as e:
            session.rollback()
            logger.error(f"Error adding historical pick: {e}")
            raise
        finally:
            session.close()

    async def get_recent_picks(self, limit: int = 10) -> List[MoviePick]:
        """Get recent movie picks"""
        session = self.db.get_session()
        try:
            from sqlalchemy.orm import joinedload

            # Eagerly load relationships to avoid lazy loading issues
            picks = (
                session.query(MoviePick)
                .options(
                    joinedload(MoviePick.picker),  # Eagerly load picker relationship
                    joinedload(MoviePick.ratings).joinedload(
                        MovieRating.rater
                    ),  # Eagerly load ratings and raters
                )
                .order_by(MoviePick.pick_date.desc())
                .limit(limit)
                .all()
            )

            return picks
        finally:
            session.close()

    async def get_user_pick_history(self, username: str) -> List[MoviePick]:
        """Get pick history for a specific user"""
        session = self.db.get_session()
        try:
            from sqlalchemy.orm import joinedload

            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return []

            picks = (
                session.query(MoviePick)
                .options(
                    joinedload(MoviePick.picker),  # Eagerly load picker relationship
                    joinedload(MoviePick.ratings).joinedload(
                        MovieRating.rater
                    ),  # Eagerly load ratings and raters
                )
                .filter(MoviePick.picker_user_id == user.id)
                .order_by(MoviePick.pick_date.desc())
                .all()
            )

            return picks
        finally:
            session.close()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by Discord username"""
        session = self.db.get_session()
        try:
            return session.query(User).filter(User.discord_username == username).first()
        finally:
            session.close()

    async def get_schedule(
        self, periods: int = 5
    ) -> List[Tuple[User, datetime, datetime, bool, bool]]:
        """
        Get upcoming schedule with skip information
        Returns: List of (user, start, end, is_current, is_skipped)
        """
        session = self.db.get_session()
        try:
            from models.database import RotationSkip

            users = session.query(User).order_by(User.rotation_position).all()
            if not users:
                return []

            current_user, current_start, current_end = await self.get_current_picker()
            schedule = []

            # Add current period (never skipped by definition)
            schedule.append((current_user, current_start, current_end, True, False))

            # Calculate future periods
            check_position = (current_user.rotation_position + 1) % len(users)
            check_start = current_end
            periods_added = 1

            while periods_added < periods:
                check_end = check_start + timedelta(days=14)
                check_user = users[check_position % len(users)]

                # Check if this period is skipped
                skip_exists = (
                    session.query(RotationSkip)
                    .filter(
                        RotationSkip.skipped_user_id == check_user.id,
                        RotationSkip.original_start_date == check_start.date(),
                        RotationSkip.original_end_date == check_end.date(),
                    )
                    .first()
                )

                is_skipped = skip_exists is not None

                schedule.append((check_user, check_start, check_end, False, is_skipped))

                check_position = (check_position + 1) % len(users)
                periods_added += 1

                # Don't advance the date if this period was skipped
                # (the next person takes this slot)
                if not is_skipped:
                    check_start = check_end

            return schedule

        finally:
            session.close()

    async def create_schedule_embed(self, periods: int = 5) -> discord.Embed:
        """Create Discord embed showing rotation schedule with pick status and skips"""
        schedule = await self.get_schedule(periods)

        embed = discord.Embed(
            title="🎬 Movie Club Rotation Schedule",
            description="Upcoming movie picker schedule",
            color=0x00FF00,
        )

        display_position = 0
        for i, (user, start, end, is_current, is_skipped) in enumerate(schedule):
            if is_skipped:
                # Show skipped periods differently
                status = "⏭️ **SKIPPED**"
                period_str = (
                    f"~~{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}~~"
                )

                embed.add_field(
                    name=f"{status} {user.real_name}",
                    value=f"📅 {period_str}\n*Period skipped*",
                    inline=False,
                )
            else:
                status = "🎯 **CURRENT**" if is_current else f"#{display_position + 1}"

                # Check if user has picked for their period
                picks = await self.get_picks_for_period(start, end)
                user_pick = next(
                    (p for p in picks if p.picker_user_id == user.id), None
                )

                if user_pick:
                    status += " ✅"

                # Check if next person is in early access
                if display_position == 1:  # Next non-skipped picker
                    can_pick, reason = await self.can_user_pick(user.discord_username)
                    if "Early access" in reason:
                        if user_pick:
                            status += " 🚪✅ *Early Access - Already Picked*"
                        else:
                            status += " 🚪 *Early Access Open*"

                period_str = f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

                # Build the value string
                value_str = f"📅 {period_str}"
                if user_pick:
                    movie_title = user_pick.movie_title
                    if user_pick.movie_year:
                        movie_title += f" ({user_pick.movie_year})"
                    value_str += f"\n🎬 {movie_title}"

                embed.add_field(
                    name=f"{status} {user.real_name}", value=value_str, inline=False
                )

                display_position += 1

        return embed

    async def create_history_embed(self, limit: int = 10) -> discord.Embed:
        """Create Discord embed showing recent pick history"""
        picks = await self.get_recent_picks(limit)

        embed = discord.Embed(
            title="🎬 Recent Movie Picks",
            description=f"Last {min(len(picks), limit)} movie selections",
            color=0x0099FF,
        )

        if not picks:
            embed.add_field(
                name="No History", value="No movies have been picked yet!", inline=False
            )
            return embed

        for pick in picks:
            movie_title = pick.movie_title
            if pick.movie_year:
                movie_title += f" ({pick.movie_year})"

            # Calculate average rating (ratings were loaded in get_recent_picks)
            rating_info = ""
            if pick.ratings:
                avg_rating = sum(r.rating for r in pick.ratings) / len(pick.ratings)
                rating_info = f" ⭐ {avg_rating:.1f}/10 ({len(pick.ratings)} ratings)"

            embed.add_field(
                name=f"🎬 {movie_title}{rating_info}",
                value=f"Picked by {pick.picker.real_name}\n📅 {pick.pick_date.strftime('%b %d, %Y')}",
                inline=True,
            )

        return embed

    async def delete_movie_pick(self, movie_id: int) -> bool:
        """Delete a movie pick by ID"""
        session = self.db.get_session()
        try:
            movie_pick = (
                session.query(MoviePick).filter(MoviePick.id == movie_id).first()
            )

            if movie_pick:
                session.delete(movie_pick)
                session.commit()
                logger.info(f"Deleted movie pick ID {movie_id}")
                return True

            return False

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting movie pick: {e}")
            return False
        finally:
            session.close()

    async def reset_all_data(self):
        """Reset all rotation data - USE WITH CAUTION"""
        session = self.db.get_session()
        try:
            # Delete all data in order to respect foreign keys
            session.query(MovieRating).delete()
            session.query(MoviePick).delete()
            session.query(RotationState).delete()
            session.query(User).delete()

            session.commit()

            # Re-initialize rotation state
            self.db.init_rotation_state()

            logger.warning("All rotation data has been reset!")

        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting rotation data: {e}")
            raise
        finally:
            session.close()

    async def get_admin_stats(self) -> dict:
        """Get admin statistics"""
        session = self.db.get_session()
        try:
            from sqlalchemy import func

            # User stats
            total_users = session.query(User).count()
            active_users = (
                session.query(User).filter(User.rotation_position.isnot(None)).count()
            )

            # Movie stats
            total_picks = session.query(MoviePick).count()
            rated_movies = session.query(MoviePick).join(MovieRating).distinct().count()

            # Rating stats
            total_ratings = session.query(MovieRating).count()
            avg_rating_result = session.query(func.avg(MovieRating.rating)).scalar()
            average_rating = float(avg_rating_result) if avg_rating_result else 0.0

            # Current rotation info
            try:
                current_user, current_start, current_end = (
                    await self.get_current_picker()
                )
                current_period = f"{current_user.real_name} ({current_start.strftime('%b %d')} - {current_end.strftime('%b %d')})"
                days_remaining = (current_end - datetime.now()).days
            except:
                current_period = "Not set up"
                days_remaining = 0

            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_picks": total_picks,
                "rated_movies": rated_movies,
                "total_ratings": total_ratings,
                "average_rating": average_rating,
                "current_period": current_period,
                "days_remaining": days_remaining,
            }

        finally:
            session.close()

    async def add_or_update_movie_pick(
        self,
        username: str,
        movie_title: str,
        movie_year: int = None,
        imdb_id: str = None,
        movie_details: dict = None,
        is_early_access: bool = False,
    ) -> MoviePick:
        """Add or update a movie pick for the user's current/upcoming period"""
        session = self.db.get_session()
        try:
            from sqlalchemy.orm import joinedload

            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                raise ValueError(f"User {username} not found")

            # Determine which period this pick is for
            current_user, current_start, current_end = await self.get_current_picker()

            if is_early_access:
                # This is a future pick - get the next period for this user
                next_user, next_start, next_end = await self.get_next_picker()
                if user.id != next_user.id:
                    raise ValueError("User is not eligible for early access")
                period_start = next_start.date()
                period_end = next_end.date()
            else:
                # This is a current pick
                if user.id != current_user.id:
                    raise ValueError("User is not the current picker")
                period_start = current_start.date()
                period_end = current_end.date()

            # Check if user already has a pick for this period
            existing_pick = (
                session.query(MoviePick)
                .filter(
                    MoviePick.picker_user_id == user.id,
                    MoviePick.period_start_date == period_start,
                    MoviePick.period_end_date == period_end,
                )
                .first()
            )

            if existing_pick:
                # Update existing pick
                existing_pick.movie_title = movie_title
                existing_pick.movie_year = movie_year
                existing_pick.imdb_id = imdb_id
                existing_pick.movie_details = movie_details or {}
                existing_pick.pick_date = datetime.now()

                session.commit()
                session.refresh(existing_pick)

                logger.info(f"Updated movie pick: {movie_title} by {username}")
                return existing_pick
            else:
                # Create new pick
                movie_pick = MoviePick(
                    picker_user_id=user.id,
                    movie_title=movie_title,
                    movie_year=movie_year,
                    imdb_id=imdb_id,
                    movie_details=movie_details or {},
                    pick_date=datetime.now(),
                    period_start_date=period_start,
                    period_end_date=period_end,
                )

                session.add(movie_pick)
                session.commit()
                session.refresh(movie_pick)

                logger.info(f"Added movie pick: {movie_title} by {username}")
                return movie_pick

        except Exception as e:
            session.rollback()
            logger.error(f"Error adding/updating movie pick: {e}")
            raise
        finally:
            session.close()

    async def get_current_movie_pick(self) -> Optional[MoviePick]:
        """Get the movie pick for the current period"""
        session = self.db.get_session()
        try:
            from sqlalchemy.orm import joinedload

            # Get current period dates
            current_user, current_start, current_end = await self.get_current_picker()

            # Find pick for current period
            current_pick = (
                session.query(MoviePick)
                .options(
                    joinedload(MoviePick.picker),
                    joinedload(MoviePick.ratings).joinedload(MovieRating.rater),
                )
                .filter(
                    MoviePick.picker_user_id == current_user.id,
                    MoviePick.period_start_date == current_start.date(),
                    MoviePick.period_end_date == current_end.date(),
                )
                .first()
            )

            return current_pick

        finally:
            session.close()

    async def get_user_active_pick(self, username: str) -> Optional[MoviePick]:
        """Get user's active pick (current period or upcoming period if in early access)"""
        session = self.db.get_session()
        try:
            from sqlalchemy.orm import joinedload

            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return None

            # Check if user is current picker
            current_user, current_start, current_end = await self.get_current_picker()

            if user.id == current_user.id:
                # Look for current period pick
                return (
                    session.query(MoviePick)
                    .options(
                        joinedload(MoviePick.picker),
                        joinedload(MoviePick.ratings).joinedload(MovieRating.rater),
                    )
                    .filter(
                        MoviePick.picker_user_id == user.id,
                        MoviePick.period_start_date == current_start.date(),
                        MoviePick.period_end_date == current_end.date(),
                    )
                    .first()
                )
            else:
                # Check if user is next picker
                next_user, next_start, next_end = await self.get_next_picker()

                if user.id == next_user.id:
                    # Look for next period pick (early access)
                    return (
                        session.query(MoviePick)
                        .options(
                            joinedload(MoviePick.picker),
                            joinedload(MoviePick.ratings).joinedload(MovieRating.rater),
                        )
                        .filter(
                            MoviePick.picker_user_id == user.id,
                            MoviePick.period_start_date == next_start.date(),
                            MoviePick.period_end_date == next_end.date(),
                        )
                        .first()
                    )

            return None

        finally:
            session.close()

    async def get_picks_for_period(
        self, period_start: datetime, period_end: datetime
    ) -> List[MoviePick]:
        """Get all picks for a specific period"""
        session = self.db.get_session()
        try:
            from sqlalchemy.orm import joinedload

            picks = (
                session.query(MoviePick)
                .options(
                    joinedload(MoviePick.picker),
                    joinedload(MoviePick.ratings).joinedload(MovieRating.rater),
                )
                .filter(
                    MoviePick.period_start_date == period_start.date(),
                    MoviePick.period_end_date == period_end.date(),
                )
                .all()
            )

            return picks

        finally:
            session.close()

    async def add_user_to_rotation(
        self, discord_username: str, real_name: str
    ) -> tuple[bool, str, dict]:
        """
        Add a new user to the end of the rotation

        Args:
            discord_username: Discord username (without @)
            real_name: Real name of the person

        Returns:
            Tuple of (success, message, details)
        """
        session = self.db.get_session()
        try:
            from sqlalchemy import func

            # Check if user already exists
            existing_user = (
                session.query(User)
                .filter(User.discord_username == discord_username)
                .first()
            )

            if existing_user:
                return False, f"User @{discord_username} already exists in rotation", {}

            # Check if real name already exists (to prevent duplicates)
            existing_name = (
                session.query(User).filter(User.real_name == real_name).first()
            )

            if existing_name:
                return (
                    False,
                    f"A user with the name '{real_name}' already exists (@{existing_name.discord_username})",
                    {},
                )

            # Get the highest rotation position
            max_position_result = session.query(
                func.max(User.rotation_position)
            ).scalar()

            if max_position_result is None:
                # No users exist yet
                new_position = 0
            else:
                # Add to the end
                new_position = max_position_result + 1

            # Create the new user
            new_user = User(
                discord_username=discord_username,
                real_name=real_name,
                rotation_position=new_position,
            )

            session.add(new_user)
            session.commit()

            # Get total users for context
            total_users = session.query(User).count()

            # Calculate when their first turn would be
            rotation_state = session.query(RotationState).first()
            if rotation_state and rotation_state.rotation_start_date:
                # Calculate their first period
                # They're at the end of the rotation, so their first turn is after everyone else
                periods_until_turn = new_position
                first_turn_start = rotation_state.rotation_start_date + timedelta(
                    days=14 * periods_until_turn
                )
                first_turn_end = first_turn_start + timedelta(days=14)
                first_turn_str = f"{first_turn_start.strftime('%b %d')} - {first_turn_end.strftime('%b %d, %Y')}"
            else:
                first_turn_str = "Rotation not started"

            details = {
                "username": discord_username,
                "real_name": real_name,
                "position": new_position + 1,  # Convert to 1-based for display
                "total_users": total_users,
                "first_turn": first_turn_str,
            }

            message = (
                f"✅ Added {real_name} (@{discord_username}) to rotation\n"
                f"Position: #{new_position + 1} of {total_users}"
            )

            logger.info(
                f"Added user {real_name} (@{discord_username}) to rotation at position {new_position}"
            )

            return True, message, details

        except Exception as e:
            session.rollback()
            logger.error(f"Error adding user to rotation: {e}")
            return False, f"Error adding user: {str(e)}", {}
        finally:
            session.close()

    async def remove_user_from_rotation(
        self, discord_username: str
    ) -> tuple[bool, str, dict]:
        """
        Remove a user from active rotation while preserving their historical data

        Args:
            discord_username: Discord username to remove from active rotation

        Returns:
            Tuple of (success, message, details)
        """
        session = self.db.get_session()
        try:
            # Find the user
            user_to_remove = (
                session.query(User)
                .filter(User.discord_username == discord_username)
                .first()
            )

            if not user_to_remove:
                return False, f"User @{discord_username} not found in rotation", {}

            removed_position = user_to_remove.rotation_position
            removed_name = user_to_remove.real_name
            removed_id = user_to_remove.id

            # Count their historical data (for info only, not deleting)
            pick_count = (
                session.query(MoviePick)
                .filter(MoviePick.picker_user_id == removed_id)
                .count()
            )

            rating_count = (
                session.query(MovieRating)
                .filter(MovieRating.rater_user_id == removed_id)
                .count()
            )

            # Check if they're currently scheduled or have future picks
            from models.database import RotationSkip

            # Get current and next picker to check if they're active
            try:
                current_user, current_start, current_end = (
                    await self.get_current_picker()
                )
                is_current = current_user.id == removed_id if current_user else False

                next_user, next_start, next_end = await self.get_next_picker()
                is_next = next_user.id == removed_id if next_user else False
            except:
                is_current = False
                is_next = False

            # Delete any future skips for this user (they won't need them anymore)
            now = datetime.now()
            future_skips = (
                session.query(RotationSkip)
                .filter(
                    RotationSkip.skipped_user_id == removed_id,
                    RotationSkip.original_start_date >= now.date(),
                )
                .delete()
            )

            # Set rotation_position to NULL to mark them as inactive
            # This preserves the user record for historical relationships
            user_to_remove.rotation_position = None

            # Reorganize positions for active users after the removed one
            users_to_shift = (
                session.query(User)
                .filter(
                    User.rotation_position > removed_position,
                    User.rotation_position.isnot(None),  # Only active users
                )
                .all()
            )

            for user in users_to_shift:
                user.rotation_position -= 1

            session.commit()

            # Get new total of active users
            active_users = (
                session.query(User).filter(User.rotation_position.isnot(None)).count()
            )

            details = {
                "removed_user": removed_name,
                "removed_position": removed_position + 1,
                "picks_preserved": pick_count,
                "ratings_preserved": rating_count,
                "future_skips_removed": future_skips,
                "remaining_active_users": active_users,
                "was_current": is_current,
                "was_next": is_next,
            }

            status_notes = []
            if is_current:
                status_notes.append("Was current picker")
            if is_next:
                status_notes.append("Was next picker")
            if future_skips > 0:
                status_notes.append(f"Removed {future_skips} future skip(s)")

            message = (
                f"✅ Removed {removed_name} (@{discord_username}) from active rotation\n"
                f"Preserved {pick_count} picks and {rating_count} ratings for history\n"
                f"Active members remaining: {active_users}"
            )

            if status_notes:
                message += f"\nNotes: {', '.join(status_notes)}"

            logger.info(
                f"Removed user {removed_name} (@{discord_username}) from active rotation, preserved historical data"
            )

            return True, message, details

        except Exception as e:
            session.rollback()
            logger.error(f"Error removing user from rotation: {e}")
            return False, f"Error removing user: {str(e)}", {}
        finally:
            session.close()

    async def reactivate_user(
        self, discord_username: str, position: int = None
    ) -> tuple[bool, str, dict]:
        """
        Reactivate a previously removed user back into the rotation

        Args:
            discord_username: Discord username to reactivate
            position: Optional specific position (0-based), defaults to end

        Returns:
            Tuple of (success, message, details)
        """
        session = self.db.get_session()
        try:
            # Find the inactive user
            user_to_reactivate = (
                session.query(User)
                .filter(
                    User.discord_username == discord_username,
                    User.rotation_position.is_(None),  # Only inactive users
                )
                .first()
            )

            if not user_to_reactivate:
                # Check if they're already active
                active_user = (
                    session.query(User)
                    .filter(
                        User.discord_username == discord_username,
                        User.rotation_position.isnot(None),
                    )
                    .first()
                )

                if active_user:
                    return (
                        False,
                        f"User @{discord_username} is already active in rotation",
                        {},
                    )
                else:
                    return False, f"User @{discord_username} not found in system", {}

            # Get current max position
            max_position = session.query(func.max(User.rotation_position)).scalar()

            if max_position is None:
                new_position = 0
            elif position is not None and 0 <= position <= max_position + 1:
                # Insert at specific position
                # Shift users at or after this position
                users_to_shift = (
                    session.query(User)
                    .filter(
                        User.rotation_position >= position,
                        User.rotation_position.isnot(None),
                    )
                    .all()
                )

                for user in users_to_shift:
                    user.rotation_position += 1

                new_position = position
            else:
                # Add to end
                new_position = max_position + 1

            # Reactivate the user
            user_to_reactivate.rotation_position = new_position
            session.commit()

            # Get stats
            pick_count = (
                session.query(MoviePick)
                .filter(MoviePick.picker_user_id == user_to_reactivate.id)
                .count()
            )

            active_users = (
                session.query(User).filter(User.rotation_position.isnot(None)).count()
            )

            details = {
                "username": discord_username,
                "real_name": user_to_reactivate.real_name,
                "position": new_position + 1,
                "total_active": active_users,
                "historical_picks": pick_count,
            }

            message = (
                f"✅ Reactivated {user_to_reactivate.real_name} (@{discord_username})\n"
                f"Position: #{new_position + 1} of {active_users} active members\n"
                f"Historical picks retained: {pick_count}"
            )

            logger.info(
                f"Reactivated user {user_to_reactivate.real_name} at position {new_position}"
            )

            return True, message, details

        except Exception as e:
            session.rollback()
            logger.error(f"Error reactivating user: {e}")
            return False, f"Error reactivating user: {str(e)}", {}
        finally:
            session.close()

    async def list_inactive_users(self) -> list[dict]:
        """
        Get list of all inactive users (removed but with preserved history)

        Returns:
            List of inactive user dictionaries
        """
        session = self.db.get_session()
        try:
            inactive_users = (
                session.query(User).filter(User.rotation_position.is_(None)).all()
            )

            result = []
            for user in inactive_users:
                pick_count = (
                    session.query(MoviePick)
                    .filter(MoviePick.picker_user_id == user.id)
                    .count()
                )

                rating_count = (
                    session.query(MovieRating)
                    .filter(MovieRating.rater_user_id == user.id)
                    .count()
                )

                result.append(
                    {
                        "username": user.discord_username,
                        "real_name": user.real_name,
                        "picks": pick_count,
                        "ratings": rating_count,
                    }
                )

            return result

        finally:
            session.close()
