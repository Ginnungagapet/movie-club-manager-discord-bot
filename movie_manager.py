import discord
import asyncio
from functools import partial
from imdb import IMDb
from typing import Optional, Tuple, Dict, Any


class MovieManager:
    """
    Simple movie manager with fuzzy search and IMDB integration.
    Finds best match for movie queries and caches current selection.
    """

    def __init__(self):
        self.ia = IMDb()
        self.current_movie: Optional[str] = None
        self.current_movie_details: Optional[Dict[str, Any]] = None

    def get_current_movie(self) -> Optional[str]:
        """Returns the currently selected movie name"""
        return self.current_movie

    def get_current_movie_details(self) -> Optional[Dict[str, Any]]:
        """Returns detailed information about the current movie"""
        return self.current_movie_details

    def clear_current_movie(self) -> None:
        """Clears the current movie selection"""
        self.current_movie = None
        self.current_movie_details = None

    async def pick_movie(self, query: str) -> Tuple[bool, str, Optional[discord.Embed]]:
        """
        Search for a movie and select the best match
        Returns: (success: bool, message: str, embed: Optional[discord.Embed])
        """
        try:
            # Search IMDB for movies
            loop = asyncio.get_event_loop()
            search_func = partial(self.ia.search_movie, query)
            movies = await loop.run_in_executor(None, search_func)

            if not movies:
                return False, f"❌ No movies found for **{query}**", None

            # Get the best match (first result is usually most relevant)
            best_match = movies[0]

            # Get detailed movie information
            detail_func = partial(self.ia.update, best_match)
            await loop.run_in_executor(None, detail_func)

            # Cache the movie selection
            self.current_movie = best_match["title"]
            self.current_movie_details = best_match

            # Create embed with movie details
            embed = self._create_movie_embed(best_match)

            return True, f"🎬 **{self.current_movie}** has been selected!", embed

        except Exception as e:
            return False, f"❌ Error searching for movie: {str(e)}", None

    def create_current_movie_embed(self) -> Optional[discord.Embed]:
        """
        Create an embed for the currently selected movie
        Returns None if no movie is selected
        """
        if not self.current_movie or not self.current_movie_details:
            return None

        return self._create_movie_embed(self.current_movie_details, is_current=True)

    def _create_movie_embed(
        self, movie_details: Dict[str, Any], is_current: bool = False
    ) -> discord.Embed:
        """
        Create a standardized movie embed with IMDB information
        """
        title = movie_details.get("title", "Unknown")
        year = movie_details.get("year", "Unknown")
        movie_id = movie_details.movieID

        # Create embed
        embed_title = "🎬 Current Movie" if is_current else "🎬 Movie Selected!"
        embed = discord.Embed(
            title=embed_title,
            description=f"**{title}** ({year})",
            color=0x0099FF if is_current else 0x00FF00,
            url=f"https://www.imdb.com/title/tt{movie_id}/",
        )

        # Add IMDB rating
        rating = movie_details.get("rating")
        if rating:
            embed.add_field(name="⭐ IMDB Rating", value=f"{rating}/10", inline=True)

        # Add genres
        genres = movie_details.get("genres", [])
        if genres:
            embed.add_field(
                name="🎭 Genres", value=", ".join(genres[:3]), inline=True
            )  # Limit to 3 genres

        # Add runtime
        runtime = movie_details.get("runtimes")
        if runtime and len(runtime) > 0:
            embed.add_field(name="⏱️ Runtime", value=f"{runtime[0]} min", inline=True)

        # Add director(s)
        directors = movie_details.get("directors", [])
        if directors:
            director_names = [
                director.get("name", str(director)) for director in directors[:2]
            ]
            embed.add_field(
                name="🎬 Director", value=", ".join(director_names), inline=True
            )

        # Add cast (top 3)
        cast = movie_details.get("cast", [])
        if cast:
            cast_names = [actor.get("name", str(actor)) for actor in cast[:3]]
            embed.add_field(name="🎭 Cast", value=", ".join(cast_names), inline=True)

        # Add plot
        plot = movie_details.get("plot outline") or (
            movie_details.get("plot", [""])[0] if movie_details.get("plot") else ""
        )
        if plot:
            # Clean up plot text and truncate
            clean_plot = plot.replace("::Anonymous", "").replace("::IMDb", "").strip()
            truncated_plot = (
                clean_plot[:300] + "..." if len(clean_plot) > 300 else clean_plot
            )
            embed.add_field(name="📖 Plot", value=truncated_plot, inline=False)

        # Add footer with IMDB link
        embed.set_footer(
            text="Click the title to view on IMDB",
            icon_url="https://m.media-amazon.com/images/G/01/imdb/images/social/imdb_logo.png",
        )

        # Add poster if available
        poster_url = movie_details.get("full-size cover url")
        if poster_url:
            embed.set_thumbnail(url=poster_url)

        return embed
