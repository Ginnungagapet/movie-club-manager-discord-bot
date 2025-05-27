"""
Rotation service for managing movie club scheduling
"""

import discord
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging

from models.database import DatabaseManager, User, MoviePick, RotationState
from models.schemas import validate_rotation_setup, validate_movie_pick

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
        # Validate input data
        schema = validate_rotation_setup(user_data)

        session = self.db.get_session()
        try:
            # Clear existing users
            session.query(User).delete()

            # Add new users with rotation positions
            for position, (username, real_name) in enumerate(schema.user_data):
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

    async def get_current_picker(self) -> Tuple[User, datetime, datetime]:
        """Get current picker information"""
        session = self.db.get_session()
        try:
            rotation_state = session.query(RotationState).first()
            if not rotation_state or not rotation_state.current_user:
                raise ValueError("No rotation state set up")

            period_start, period_end = await self._get_current_period_dates()
            return rotation_state.current_user, period_start, period_end

        finally:
            session.close()

    async def get_next_picker(self) -> Tuple[User, datetime, datetime]:
        """Get next picker information"""
        session = self.db.get_session()
        try:
            current_user, _, current_end = await self.get_current_picker()
            users = session.query(User).order_by(User.rotation_position).all()

            if not users:
                raise ValueError("No users in rotation")

            # Find next user
            current_position = current_user.rotation_position
            next_position = (current_position + 1) % len(users)
            next_user = next(
                user for user in users if user.rotation_position == next_position
            )

            period_start = current_end
            period_end = period_start + timedelta(
                days=self.settings.rotation_period_days
            )

            return next_user, period_start, period_end

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
                early_access_start = next_start - timedelta(
                    days=self.settings.early_access_days
                )
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
                early_access_start = next_start - timedelta(
                    days=self.settings.early_access_days
                )
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
        """Add a movie pick to the database"""
        # Validate input
        schema = validate_movie_pick(
            username, movie_title, movie_year, imdb_id, movie_details
        )

        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                raise ValueError(f"User {username} not found")

            current_user, period_start, period_end = await self.get_current_picker()

            movie_pick = MoviePick(
                picker_user_id=user.id,
                movie_title=schema.movie_title,
                movie_year=schema.movie_year,
                imdb_id=schema.imdb_id,
                movie_details=schema.movie_details,
                period_start_date=period_start.date(),
                period_end_date=period_end.date(),
            )

            session.add(movie_pick)
            session.commit()
            session.refresh(movie_pick)

            logger.info(f"Added movie pick: {movie_title} by {username}")
            return movie_pick

        except Exception as e:
            session.rollback()
            logger.error(f"Error adding movie pick: {e}")
            raise
        finally:
            session.close()

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

            period_start = start_date + timedelta(
                days=self.settings.rotation_period_days * user_position
            )
            period_end = period_start + timedelta(
                days=self.settings.rotation_period_days
            )

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
            return (
                session.query(MoviePick)
                .order_by(MoviePick.pick_date.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    async def get_user_pick_history(self, username: str) -> List[MoviePick]:
        """Get pick history for a specific user"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return []

            return (
                session.query(MoviePick)
                .filter(MoviePick.picker_user_id == user.id)
                .order_by(MoviePick.pick_date.desc())
                .all()
            )
        finally:
            session.close()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by Discord username"""
        session = self.db.get_session()
        try:
            return session.query(User).filter(User.discord_username == username).first()
        finally:
            session.close()

    async def advance_rotation(self) -> bool:
        """Manually advance rotation to next person"""
        session = self.db.get_session()
        try:
            next_user, _, _ = await self.get_next_picker()

            rotation_state = session.query(RotationState).first()
            if rotation_state:
                rotation_state.current_user_id = next_user.id
                session.commit()
                logger.info(f"Advanced rotation to {next_user.real_name}")
                return True

            return False

        except Exception as e:
            session.rollback()
            logger.error(f"Error advancing rotation: {e}")
            return False
        finally:
            session.close()

    async def _get_current_period_dates(self) -> Tuple[datetime, datetime]:
        """Calculate current period start and end dates"""
        session = self.db.get_session()
        try:
            rotation_state = session.query(RotationState).first()
            if not rotation_state or not rotation_state.rotation_start_date:
                raise ValueError("No rotation start date set")

            now = datetime.now()
            days_since_start = (now - rotation_state.rotation_start_date).days
            periods_passed = days_since_start // self.settings.rotation_period_days

            current_period_start = rotation_state.rotation_start_date + timedelta(
                days=periods_passed * self.settings.rotation_period_days
            )
            current_period_end = current_period_start + timedelta(
                days=self.settings.rotation_period_days
            )

            # Check if we need to update current user
            users = session.query(User).order_by(User.rotation_position).all()
            if users:
                expected_position = periods_passed % len(users)
                current_user = rotation_state.current_user

                if (
                    not current_user
                    or current_user.rotation_position != expected_position
                ):
                    new_current_user = next(
                        u for u in users if u.rotation_position == expected_position
                    )
                    rotation_state.current_user_id = new_current_user.id
                    session.commit()

            return current_period_start, current_period_end

        finally:
            session.close()

    async def create_schedule_embed(self, periods: int = 5) -> discord.Embed:
        """Create Discord embed showing rotation schedule"""
        schedule = await self.get_schedule(periods)

        embed = discord.Embed(
            title="🎬 Movie Club Rotation Schedule",
            description="Upcoming movie picker schedule",
            color=0x00FF00,
        )

        for i, (user, start, end, is_current) in enumerate(schedule):
            status = "🎯 **CURRENT**" if is_current else f"#{i + 1}"

            # Check if next person is in early access
            if i == 1:
                can_pick, reason = await self.can_user_pick(user.discord_username)
                if "Early access" in reason:
                    status += " 🚪 *Early Access Open*"

            period_str = f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

            embed.add_field(
                name=f"{status} {user.real_name}",
                value=f"@{user.discord_username}\n📅 {period_str}",
                inline=False,
            )

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

            rating_info = ""
            if pick.average_rating:
                rating_info = (
                    f" ⭐ {pick.average_rating:.1f}/10 ({pick.rating_count} ratings)"
                )

            embed.add_field(
                name=f"🎬 {movie_title}{rating_info}",
                value=f"Picked by {pick.picker.real_name} (@{pick.picker.discord_username})\n📅 {pick.pick_date.strftime('%b %d, %Y')}",
                inline=True,
            )

        return embed

    async def get_schedule(
        self, periods: int = 5
    ) -> List[Tuple[User, datetime, datetime, bool]]:
        """Get upcoming schedule"""
        session = self.db.get_session()
        try:
            users = session.query(User).order_by(User.rotation_position).all()
            if not users:
                return []

            current_user, current_start, current_end = await self.get_current_picker()
            schedule = []

            for i in range(periods):
                position = (current_user.rotation_position + i) % len(users)
                user = next(u for u in users if u.rotation_position == position)

                if i == 0:
                    period_start = current_start
                    period_end = current_end
                    is_current = True
                else:
                    period_start = current_end + timedelta(
                        days=self.settings.rotation_period_days * (i - 1)
                    )
                    period_end = period_start + timedelta(
                        days=self.settings.rotation_period_days
                    )
                    is_current = False

                schedule.append((user, period_start, period_end, is_current))

            return schedule

        finally:
            session.close()
