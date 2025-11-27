"""
Movie search and IMDB integration service
"""

import asyncio
from functools import partial
from typing import Optional, Tuple, Dict, Any
import logging

from imdb import IMDb

logger = logging.getLogger(__name__)


class MovieService:
    """Service for movie search and IMDB integration"""

    def __init__(self, settings):
        self.settings = settings
        self.ia = IMDb()

    async def search_movie(
        self, query: str, year: Optional[int] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Search for a movie and return the best match

        Args:
            query: Movie title to search for
            year: Optional year to filter results

        Returns:
            Tuple of (success, message, movie_details)
        """
        try:
            # Search IMDB for movies
            loop = asyncio.get_event_loop()
            search_func = partial(self.ia.search_movie, query)
            movies = await loop.run_in_executor(None, search_func)

            logger.info(
                f"Search returned {len(movies) if movies else 0} results")

            if movies:
                for i, movie in enumerate(movies[:5]):
                    logger.info(
                        f"  Result {i}: {movie.get('title')} ({movie.get('year')})")

            if not movies:
                return (
                    False,
                    f"❌ No movies found for **{query}**{f' ({year})' if year else ''}",
                    None,
                )

            # Filter by year if specified
            best_match = await self._find_best_match(movies, year)

            if not best_match:
                return (
                    False,
                    f"❌ No suitable matches found for **{query}**{f' ({year})' if year else ''}",
                    None,
                )

            # Get detailed movie information
            detailed_movie = await self._get_movie_details(best_match)

            # Create response message
            actual_year = detailed_movie.get("year")
            if year and actual_year and actual_year != year:
                message = f"🎬 **{detailed_movie['title']}** found! (Found {actual_year}, searched for {year})"
            else:
                message = f"🎬 **{detailed_movie['title']}** found!"

            return True, message, detailed_movie

        except Exception as e:
            logger.error(f"Error searching for movie '{query}': {e}")
            return False, f"❌ Error searching for movie: {str(e)}", None

    async def _find_best_match(
        self, movies: list, target_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching movie from search results"""
        if not target_year:
            return movies[0]  # Return first result if no year specified

        # Try exact year match first
        exact_matches = [
            movie for movie in movies if movie.get("year") == target_year]
        if exact_matches:
            return exact_matches[0]

        # Try fuzzy year matching (within 3 years)
        fuzzy_matches = [
            movie
            for movie in movies
            if movie.get("year") and abs(movie.get("year") - target_year) <= 3
        ]

        if fuzzy_matches:
            # Sort by how close the year is to target
            fuzzy_matches.sort(key=lambda m: abs(
                m.get("year", 9999) - target_year))
            return fuzzy_matches[0]

        # Return best overall match if no year matches
        return movies[0]

    async def _get_movie_details(self, movie_obj) -> Dict[str, Any]:
        """Get detailed information for a movie object"""
        try:
            loop = asyncio.get_event_loop()
            detail_func = partial(self.ia.update, movie_obj)
            await loop.run_in_executor(None, detail_func)
            return movie_obj
        except Exception as e:
            logger.warning(f"Error getting movie details: {e}")
            return movie_obj

    def get_current_movie(self) -> Optional[str]:
        """Get the currently selected movie title"""
        return self.current_movie

    def get_current_movie_details(self) -> Optional[Dict[str, Any]]:
        """Get detailed information about the current movie"""
        return self.current_movie_details

    def clear_current_movie(self):
        """Clear the current movie selection"""
        self.current_movie = None
        self.current_movie_details = None

    def extract_movie_info(self, movie_details: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format movie information for database storage"""
        if not movie_details:
            return {}

        return {
            "title": movie_details.get("title"),
            "year": movie_details.get("year"),
            "imdb_id": (
                movie_details.movieID if hasattr(
                    movie_details, "movieID") else None
            ),
            "genres": movie_details.get("genres", []),
            "rating": movie_details.get("rating"),
            "runtime": (
                movie_details.get("runtimes", [None])[0]
                if movie_details.get("runtimes")
                else None
            ),
            "directors": [
                d.get("name", str(d)) for d in movie_details.get("directors", [])
            ],
            "cast": [c.get("name", str(c)) for c in movie_details.get("cast", [])[:5]],
            "plot": movie_details.get("plot outline")
            or (
                movie_details.get("plot", [""])[
                    0] if movie_details.get("plot") else ""
            ),
            "poster_url": movie_details.get("full-size cover url"),
        }
