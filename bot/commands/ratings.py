"""
Movie rating system commands
"""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class RatingCommands(commands.Cog):
    """Commands for movie rating system"""

    def __init__(self, bot):
        self.bot = bot
        self.rating_service = bot.services["rating"]
        self.rotation_service = bot.services["rotation"]

    @commands.command(name="rate")
    async def rate_movie(self, ctx, movie_id: int, rating: int, *, review: str = None):
        """
        Rate a movie pick
        Usage: !rate 5 8 Great movie!
               !rate 5 7
        """
        username = ctx.author.name

        if (
            rating < self.bot.settings.min_rating
            or rating > self.bot.settings.max_rating
        ):
            await ctx.send(
                f"❌ Rating must be between {self.bot.settings.min_rating} and {self.bot.settings.max_rating}!"
            )
            return

        try:
            movie_rating = await self.rating_service.add_movie_rating(
                username, movie_id, rating, review
            )

            # Get the movie details
            movie_pick = await self.rating_service.get_movie_pick(movie_id)

            if movie_pick:
                movie_title = f"{movie_pick.movie_title}"
                if movie_pick.movie_year:
                    movie_title += f" ({movie_pick.movie_year})"
            else:
                movie_title = f"Movie ID {movie_id}"

            embed = discord.Embed(
                title="⭐ Rating Added!",
                description=f"You rated **{movie_title}** {rating}/10",
                color=0x00FF00,
            )

            if review:
                embed.add_field(name="Your Review", value=f'*"{review}"*', inline=False)

            embed.add_field(
                name="View All Ratings",
                value=f"Use `!movie_ratings {movie_id}` to see all ratings for this movie",
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error adding rating: {e}")
            await ctx.send(f"❌ Error adding rating: {str(e)}")

    @commands.command(name="movie_ratings")
    async def show_movie_ratings(self, ctx, movie_id: int):
        """Show all ratings for a specific movie"""
        try:
            embed = await self.rating_service.create_ratings_embed(movie_id)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error showing ratings for movie {movie_id}: {e}")
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

                rating_text = f"⭐ {rating.rating}/10"
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

                rating_text = f"⭐ {rating.rating}/10 by {rating.rater.real_name}"
                if rating.review_text:
                    rating_text += f"\n*\"{rating.review_text[:100]}{'...' if len(rating.review_text) > 100 else ''}\"*"

                embed.add_field(name=movie_title, value=rating_text, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error showing recent ratings: {e}")
            await ctx.send(f"❌ Error showing recent ratings: {str(e)}")

    @commands.command(name="update_rating")
    async def update_rating(
        self, ctx, movie_id: int, new_rating: int, *, new_review: str = None
    ):
        """
        Update your existing rating for a movie
        Usage: !update_rating 5 9 Even better on second viewing!
        """
        username = ctx.author.name

        if (
            new_rating < self.bot.settings.min_rating
            or new_rating > self.bot.settings.max_rating
        ):
            await ctx.send(
                f"❌ Rating must be between {self.bot.settings.min_rating} and {self.bot.settings.max_rating}!"
            )
            return

        try:
            # This will update if rating exists, or create new if it doesn't
            movie_rating = await self.rating_service.add_movie_rating(
                username, movie_id, new_rating, new_review
            )

            movie_pick = await self.rating_service.get_movie_pick(movie_id)
            movie_title = f"{movie_pick.movie_title}"
            if movie_pick.movie_year:
                movie_title += f" ({movie_pick.movie_year})"

            embed = discord.Embed(
                title="⭐ Rating Updated!",
                description=f"Updated rating for **{movie_title}** to {new_rating}/10",
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


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(RatingCommands(bot))
