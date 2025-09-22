"""
Movie rating system commands - Updated for float ratings and movie titles
"""

import discord
from discord.ext import commands
import logging
from utils.parsers import (
    parse_movie_title_and_review,
    validate_rating,
    fuzzy_match_movie_title,
)

logger = logging.getLogger(__name__)


class RatingCommands(commands.Cog):
    """Commands for movie rating system"""

    def __init__(self, bot):
        self.bot = bot
        self.rating_service = bot.services["rating"]
        self.rotation_service = bot.services["rotation"]

    async def _get_available_movie_titles(self) -> list[str]:
        """Get list of all available movie titles for fuzzy matching"""
        try:
            recent_picks = await self.rotation_service.get_recent_picks(
                limit=100
            )  # Get many movies
            return [pick.movie_title for pick in recent_picks]
        except:
            return []

    async def _find_movie_by_title(self, search_title: str) -> tuple[str, str]:
        """
        Find movie by title with fuzzy matching
        Returns: (actual_title, display_title_with_year)
        """
        session = self.rating_service.db.get_session()
        try:
            from models.database import MoviePick

            # Try exact match first (case insensitive)
            movie_pick = (
                session.query(MoviePick)
                .filter(MoviePick.movie_title.ilike(f"%{search_title}%"))
                .order_by(MoviePick.pick_date.desc())
                .first()
            )

            if movie_pick:
                display_title = movie_pick.movie_title
                if movie_pick.movie_year:
                    display_title += f" ({movie_pick.movie_year})"
                return movie_pick.movie_title, display_title

            # Try fuzzy matching
            available_titles = await self._get_available_movie_titles()
            best_match = fuzzy_match_movie_title(search_title, available_titles)

            if best_match:
                movie_pick = (
                    session.query(MoviePick)
                    .filter(MoviePick.movie_title == best_match)
                    .order_by(MoviePick.pick_date.desc())
                    .first()
                )

                if movie_pick:
                    display_title = movie_pick.movie_title
                    if movie_pick.movie_year:
                        display_title += f" ({movie_pick.movie_year})"
                    return movie_pick.movie_title, display_title

            # Not found
            raise ValueError(f"Movie '{search_title}' not found")

        finally:
            session.close()

    @commands.command(name="rate")
    async def rate_movie(self, ctx, rating: float, *, movie_and_review: str):
        """
        Rate a movie by title (accepts float ratings 1.0-10.0)
        Usage: !rate 8.5 The Matrix
               !rate 9.2 The Matrix Amazing movie with great effects!
               !rate 7.0 Blade Runner 2049 Visually stunning but slow paced
        """
        username = ctx.author.name

        # Validate rating
        if not validate_rating(rating):
            await ctx.send(f"❌ Rating must be between 1.0 and 10.0!")
            return

        if not movie_and_review:
            await ctx.send(
                "❌ Please provide a movie title! Usage: `!rate 8.5 The Matrix`"
            )
            return

        try:
            # Get available movie titles for better parsing
            available_titles = await self._get_available_movie_titles()

            # Parse movie title and review
            movie_title, review_text = parse_movie_title_and_review(
                movie_and_review, available_titles
            )

            # Find the actual movie
            actual_title, display_title = await self._find_movie_by_title(movie_title)

            # Add the rating
            movie_rating = await self.rating_service.add_movie_rating(
                username, actual_title, rating, review_text
            )

            embed = discord.Embed(
                title="⭐ Rating Added!",
                description=f"You rated **{display_title}** {rating}/10",
                color=0x00FF00,
            )

            if review_text:
                embed.add_field(
                    name="Your Review", value=f'*"{review_text}"*', inline=False
                )

            embed.add_field(
                name="View All Ratings",
                value=f"Use `!movie_ratings {actual_title}` to see all ratings",
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error adding rating: {e}")
            await ctx.send(f"❌ Error adding rating: {str(e)}")

    @commands.command(name="movie_ratings")
    async def show_movie_ratings(self, ctx, *, movie_title: str):
        """Show all ratings for a specific movie by title"""
        try:
            # Find the movie
            actual_title, display_title = await self._find_movie_by_title(movie_title)

            embed = await self.rating_service.create_ratings_embed(actual_title)
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing ratings for movie {movie_title}: {e}")
            await ctx.send(f"❌ Error showing ratings: {str(e)}")

    @commands.command(name="my_ratings")
    async def show_my_ratings(self, ctx):
        """Show your rating history"""
        username = ctx.author.name

        try:
            ratings = await self.rating_service.get_user_ratings(username)

            if not ratings:
                await ctx.send("You haven't rated any movies yet!")
                return

            # Get user info
            user = await self.rotation_service.get_user_by_username(username)
            user_name = user.real_name if user else username

            embed = discord.Embed(
                title=f"🎬 {user_name}'s Recent Ratings", color=0x0099FF
            )

            for rating in ratings[:10]:  # Show last 10 ratings
                movie_title = rating.movie_pick.movie_title
                if rating.movie_pick.movie_year:
                    movie_title += f" ({rating.movie_pick.movie_year})"

                rating_text = f"⭐ {rating.rating:.1f}/10"
                if rating.review_text:
                    rating_text += f"\n*\"{rating.review_text[:50]}{'...' if len(rating.review_text) > 50 else ''}\"*"

                embed.add_field(name=movie_title, value=rating_text, inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing ratings for {username}: {e}")
            await ctx.send(f"❌ Error showing your ratings: {str(e)}")

    @commands.command(name="top_rated")
    async def show_top_rated(self, ctx, limit: int = 10):
        """Show top rated movies"""
        try:
            top_movies = await self.rating_service.get_top_rated_movies(limit)

            if not top_movies:
                await ctx.send("No rated movies yet!")
                return

            embed = discord.Embed(
                title="🏆 Top Rated Movies",
                description=f"Top {min(len(top_movies), limit)} movies by average rating",
                color=0xFFD700,
            )

            for i, movie in enumerate(top_movies, 1):
                movie_title = movie.movie_title
                if movie.movie_year:
                    movie_title += f" ({movie.movie_year})"

                avg_rating = movie.average_rating
                rating_count = movie.rating_count

                embed.add_field(
                    name=f"#{i} {movie_title}",
                    value=f"⭐ {avg_rating:.1f}/10 ({rating_count} rating{'s' if rating_count != 1 else ''})\nPicked by {movie.picker.real_name}",
                    inline=False,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing top rated movies: {e}")
            await ctx.send(f"❌ Error showing top rated movies: {str(e)}")

    @commands.command(name="recent_ratings")
    async def show_recent_ratings(self, ctx, limit: int = 10):
        """Show most recent ratings from all users"""
        try:
            recent_ratings = await self.rating_service.get_recent_ratings(limit)

            if not recent_ratings:
                await ctx.send("No ratings yet!")
                return

            embed = discord.Embed(
                title="🎬 Recent Ratings",
                description=f"Last {min(len(recent_ratings), limit)} ratings",
                color=0x0099FF,
            )

            for rating in recent_ratings:
                movie_title = rating.movie_pick.movie_title
                if rating.movie_pick.movie_year:
                    movie_title += f" ({rating.movie_pick.movie_year})"

                rating_text = f"⭐ {rating.rating:.1f}/10 by {rating.rater.real_name}"
                if rating.review_text:
                    rating_text += f"\n*\"{rating.review_text[:100]}{'...' if len(rating.review_text) > 100 else ''}\"*"

                embed.add_field(name=movie_title, value=rating_text, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing recent ratings: {e}")
            await ctx.send(f"❌ Error showing recent ratings: {str(e)}")

    @commands.command(name="update_rating")
    async def update_rating(self, ctx, new_rating: float, *, movie_and_review: str):
        """
        Update your existing rating for a movie
        Usage: !update_rating 9.5 The Matrix Even better on second viewing!
               !update_rating 8.0 Blade Runner 2049
        """
        username = ctx.author.name

        if not validate_rating(new_rating):
            await ctx.send(f"❌ Rating must be between 1.0 and 10.0!")
            return

        try:
            # Get available movie titles for better parsing
            available_titles = await self._get_available_movie_titles()

            # Parse movie title and review
            movie_title, new_review = parse_movie_title_and_review(
                movie_and_review, available_titles
            )

            # Find the actual movie
            actual_title, display_title = await self._find_movie_by_title(movie_title)

            # Update the rating (this will update if exists, create if doesn't)
            movie_rating = await self.rating_service.add_movie_rating(
                username, actual_title, new_rating, new_review
            )

            embed = discord.Embed(
                title="⭐ Rating Updated!",
                description=f"Updated rating for **{display_title}** to {new_rating:.1f}/10",
                color=0x00FF00,
            )

            if new_review:
                embed.add_field(
                    name="Updated Review", value=f'*"{new_review}"*', inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error updating rating: {e}")
            await ctx.send(f"❌ Error updating rating: {str(e)}")

    @commands.command(name="rating_stats")
    async def show_rating_stats(self, ctx, *, username: str = None):
        """
        Show rating statistics for yourself or another user
        Usage: !rating_stats
               !rating_stats @someone
        """
        if username:
            # Remove @ if present
            username = username.lstrip("@")
        else:
            username = ctx.author.name

        try:
            stats = await self.rating_service.get_user_rating_stats(username)

            if stats["total_ratings"] == 0:
                user_display = (
                    username if username == ctx.author.name else f"@{username}"
                )
                await ctx.send(f"{user_display} hasn't rated any movies yet!")
                return

            # Get user info
            user = await self.rotation_service.get_user_by_username(username)
            user_name = user.real_name if user else username

            embed = discord.Embed(
                title=f"📊 {user_name}'s Rating Statistics", color=0x0099FF
            )

            embed.add_field(
                name="Total Ratings", value=str(stats["total_ratings"]), inline=True
            )

            embed.add_field(
                name="Average Rating",
                value=f"{stats['average_rating']:.1f}/10",
                inline=True,
            )

            embed.add_field(
                name="Rating Range",
                value=f"{stats['min_rating']:.1f} - {stats['max_rating']:.1f}",
                inline=True,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing rating stats: {e}")
            await ctx.send(f"❌ Error showing rating statistics: {str(e)}")

    @commands.command(name="delete_rating")
    async def delete_rating(self, ctx, *, movie_title: str):
        """
        Delete your rating for a movie
        Usage: !delete_rating The Matrix
        """
        username = ctx.author.name

        try:
            # Find the movie
            actual_title, display_title = await self._find_movie_by_title(movie_title)

            # Delete the rating
            success = await self.rating_service.delete_rating(username, actual_title)

            if success:
                embed = discord.Embed(
                    title="🗑️ Rating Deleted",
                    description=f"Deleted your rating for **{display_title}**",
                    color=0x00FF00,
                )
            else:
                embed = discord.Embed(
                    title="❌ Rating Not Found",
                    description=f"You haven't rated **{display_title}** yet",
                    color=0xFF0000,
                )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error deleting rating: {e}")
            await ctx.send(f"❌ Error deleting rating: {str(e)}")

    @commands.command(name="rate_help")
    async def rating_help(self, ctx):
        """Show help for rating commands with examples"""
        embed = discord.Embed(
            title="⭐ Rating System Help",
            description="How to use the movie rating system",
            color=0x0099FF,
        )

        embed.add_field(
            name="Rate a Movie",
            value="`!rate 8.5 The Matrix`\n`!rate 9.2 Blade Runner 2049 Amazing visuals!`",
            inline=False,
        )

        embed.add_field(
            name="View Ratings",
            value="`!movie_ratings The Matrix`\n`!my_ratings`\n`!top_rated`",
            inline=False,
        )

        embed.add_field(
            name="Update/Delete",
            value="`!update_rating 9.0 The Matrix`\n`!delete_rating The Matrix`",
            inline=False,
        )

        embed.add_field(
            name="Statistics",
            value="`!rating_stats` - Your stats\n`!recent_ratings` - Latest ratings",
            inline=False,
        )

        embed.add_field(
            name="Rating Scale",
            value="1.0 - 10.0 (decimals allowed)\n1.0 = Terrible, 5.0 = Average, 10.0 = Perfect",
            inline=False,
        )

        embed.add_field(
            name="Tips",
            value="• Movie titles are fuzzy matched - close spellings work\n• Reviews are optional but encouraged\n• You can update ratings anytime",
            inline=False,
        )

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(RatingCommands(bot))
