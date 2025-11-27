"""
Movie search and IMDB integration service
"""

import asyncio
from functools import partial
from typing import Optional, Tuple, Dict, Any
import logging
import aiohttp
import os

logger = logging.getLogger(__name__)


class MovieService:
    """Service for movie search and IMDB integration"""

    def __init__(self, settings):
        self.settings = settings
        self.omdb_api_key = os.environ.get('OMDB_API_KEY')

    async def search_movie(
        self, query: str, year: Optional[int] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Search for a movie using OMDb API"""

        clean_query = query.replace('\\', '')

        try:
            params = {
                't': clean_query,
                'apikey': self.omdb_api_key,
                'type': 'movie'
            }
            if year:
                params['y'] = str(year)

            async with aiohttp.ClientSession() as session:
                async with session.get('http://www.omdbapi.com/', params=params) as response:
                    data = await response.json()

                    logger.info(
                        f"OMDb response for '{clean_query}': {data.get('Response')}")

                    if data.get('Response') == 'False':
                        return (
                            False,
                            f"❌ No movies found for **{query}**{f' ({year})' if year else ''}",
                            None
                        )

                    movie_details = {
                        'title': data.get('Title'),
                        'year': int(data.get('Year', '0').split('–')[0]) if data.get('Year') else None,
                        'rating': float(data.get('imdbRating', 0)) if data.get('imdbRating') != 'N/A' else None,
                        'plot': data.get('Plot'),
                        'genres': data.get('Genre', '').split(', ') if data.get('Genre') else [],
                        'directors': data.get('Director', '').split(', ') if data.get('Director') else [],
                        'cast': data.get('Actors', '').split(', ') if data.get('Actors') else [],
                        'cover_url': data.get('Poster') if data.get('Poster') != 'N/A' else None,
                        'imdb_id': data.get('imdbID'),
                        'imdb_url': f"https://www.imdb.com/title/{data.get('imdbID')}/"
                    }

                    return (True, "Success", movie_details)

        except Exception as e:
            logger.error(f"Error searching movie: {e}", exc_info=True)
            return (False, f"❌ Error: {str(e)}", None)

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
