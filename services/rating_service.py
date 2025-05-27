"""
Rating service for managing movie ratings and reviews
"""

import discord
from typing import List, Optional
import logging

from models.database import DatabaseManager, User, MoviePick, MovieRating

logger = logging.getLogger(__name__)


class RatingService:
    """Service for managing movie ratings and reviews"""

    def __init__(self, settings):
        self.settings = settings
        self.db = DatabaseManager(settings.database_url_corrected)

    async def add_movie_rating(
        self, username: str, movie_pick_id: int, rating: float, review_text: str = None
    ) -> MovieRating:
        """Add or update a movie rating"""
        if rating < 1.0 or rating > 10.0:
            raise ValueError("Rating must be between 1 and 10")

        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                raise ValueError(f"User {username} not found")

            movie_pick = (
                session.query(MoviePick).filter(MoviePick.id == movie_pick_id).first()
            )
            if not movie_pick:
                raise ValueError(f"Movie pick {movie_pick_id} not found")

            # Check if rating already exists
            existing_rating = (
                session.query(MovieRating)
                .filter(
                    MovieRating.movie_pick_id == movie_pick_id,
                    MovieRating.rater_user_id == user.id,
                )
                .first()
            )

            if existing_rating:
                # Update existing rating
                existing_rating.rating = rating
                existing_rating.review_text = review_text
                movie_rating = existing_rating
                logger.info(f"Updated rating for movie {movie_pick_id} by {username}")
            else:
                # Create new rating
                movie_rating = MovieRating(
                    movie_pick_id=movie_pick_id,
                    rater_user_id=user.id,
                    rating=rating,
                    review_text=review_text,
                )
                session.add(movie_rating)
                logger.info(f"Added new rating for movie {movie_pick_id} by {username}")

            session.commit()
            session.refresh(movie_rating)
            return movie_rating

        except Exception as e:
            session.rollback()
            logger.error(f"Error adding/updating rating: {e}")
            raise
        finally:
            session.close()

    async def get_movie_pick(self, movie_pick_id: int) -> Optional[MoviePick]:
        """Get movie pick by ID"""
        session = self.db.get_session()
        try:
            return (
                session.query(MoviePick).filter(MoviePick.id == movie_pick_id).first()
            )
        finally:
            session.close()

    async def get_movie_ratings(self, movie_pick_id: int) -> List[MovieRating]:
        """Get all ratings for a specific movie"""
        session = self.db.get_session()
        try:
            return (
                session.query(MovieRating)
                .filter(MovieRating.movie_pick_id == movie_pick_id)
                .order_by(MovieRating.rated_at.desc())
                .all()
            )
        finally:
            session.close()

    async def get_user_ratings(self, username: str) -> List[MovieRating]:
        """Get all ratings by a specific user"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return []

            return (
                session.query(MovieRating)
                .filter(MovieRating.rater_user_id == user.id)
                .order_by(MovieRating.rated_at.desc())
                .all()
            )
        finally:
            session.close()

    async def get_recent_ratings(self, limit: int = 10) -> List[MovieRating]:
        """Get most recent ratings from all users"""
        session = self.db.get_session()
        try:
            return (
                session.query(MovieRating)
                .order_by(MovieRating.rated_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    async def get_top_rated_movies(self, limit: int = 10) -> List[MoviePick]:
        """Get top rated movies by average rating"""
        session = self.db.get_session()
        try:
            from sqlalchemy import func

            # Query movies with their average ratings
            subquery = (
                session.query(
                    MovieRating.movie_pick_id,
                    func.avg(MovieRating.rating).label("avg_rating"),
                    func.count(MovieRating.id).label("rating_count"),
                )
                .group_by(MovieRating.movie_pick_id)
                .having(func.count(MovieRating.id) >= 1)  # At least 1 rating
                .subquery()
            )

            return (
                session.query(MoviePick)
                .join(subquery, MoviePick.id == subquery.c.movie_pick_id)
                .order_by(subquery.c.avg_rating.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    async def get_user_rating_stats(self, username: str) -> dict:
        """Get rating statistics for a user"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return {}

            from sqlalchemy import func

            stats = (
                session.query(
                    func.count(MovieRating.id).label("total_ratings"),
                    func.avg(MovieRating.rating).label("avg_rating"),
                    func.min(MovieRating.rating).label("min_rating"),
                    func.max(MovieRating.rating).label("max_rating"),
                )
                .filter(MovieRating.rater_user_id == user.id)
                .first()
            )

            return {
                "total_ratings": stats.total_ratings or 0,
                "average_rating": float(stats.avg_rating) if stats.avg_rating else 0,
                "min_rating": stats.min_rating or 0,
                "max_rating": stats.max_rating or 0,
            }
        finally:
            session.close()

    async def create_ratings_embed(self, movie_pick_id: int) -> discord.Embed:
        """Create Discord embed showing all ratings for a movie"""
        session = self.db.get_session()
        try:
            movie_pick = (
                session.query(MoviePick).filter(MoviePick.id == movie_pick_id).first()
            )
            if not movie_pick:
                raise ValueError("Movie pick not found")

            ratings = await self.get_movie_ratings(movie_pick_id)

            movie_title = movie_pick.movie_title
            if movie_pick.movie_year:
                movie_title += f" ({movie_pick.movie_year})"

            embed = discord.Embed(
                title=f"🎬 {movie_title}",
                description=f"Picked by {movie_pick.picker.real_name}",
                color=0x00FF00,
            )

            if movie_pick.average_rating:
                embed.add_field(
                    name="⭐ Average Rating",
                    value=f"{movie_pick.average_rating:.1f}/10 ({len(ratings)} rating{'s' if len(ratings) != 1 else ''})",
                    inline=False,
                )

            # Show individual ratings
            if ratings:
                for rating in ratings:
                    rating_text = f"⭐ {rating.rating}/10"
                    if rating.review_text:
                        rating_text += f"\n*\"{rating.review_text[:100]}{'...' if len(rating.review_text) > 100 else ''}\"*"

                    embed.add_field(
                        name=rating.rater.real_name, value=rating_text, inline=True
                    )
            else:
                embed.add_field(
                    name="No Ratings Yet",
                    value="Be the first to rate this movie!",
                    inline=False,
                )

            return embed

        finally:
            session.close()

    async def create_user_stats_embed(self, username: str) -> discord.Embed:
        """Create Discord embed showing user rating statistics"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                raise ValueError("User not found")

            stats = await self.get_user_rating_stats(username)

            embed = discord.Embed(
                title=f"📊 {user.real_name}'s Rating Stats", color=0x0099FF
            )

            embed.add_field(
                name="Total Ratings",
                value=str(stats.get("total_ratings", 0)),
                inline=True,
            )

            if stats.get("total_ratings", 0) > 0:
                embed.add_field(
                    name="Average Rating",
                    value=f"{stats.get('average_rating', 0):.1f}/10",
                    inline=True,
                )

                embed.add_field(
                    name="Rating Range",
                    value=f"{stats.get('min_rating', 0)} - {stats.get('max_rating', 0)}",
                    inline=True,
                )

            return embed

        finally:
            session.close()

    async def delete_rating(self, username: str, movie_pick_id: int) -> bool:
        """Delete a user's rating for a movie"""
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.discord_username == username).first()
            if not user:
                return False

            rating = (
                session.query(MovieRating)
                .filter(
                    MovieRating.movie_pick_id == movie_pick_id,
                    MovieRating.rater_user_id == user.id,
                )
                .first()
            )

            if rating:
                session.delete(rating)
                session.commit()
                logger.info(f"Deleted rating for movie {movie_pick_id} by {username}")
                return True

            return False

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting rating: {e}")
            return False
        finally:
            session.close()
