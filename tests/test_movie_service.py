"""
Tests for movie service functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.movie_service import MovieService


class TestMovieService:
    """Test cases for MovieService"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing"""
        settings = Mock()
        settings.imdb_cache_timeout = 3600
        settings.max_search_results = 5
        return settings

    @pytest.fixture
    def movie_service(self, mock_settings):
        """Create MovieService instance for testing"""
        return MovieService(mock_settings)

    @pytest.fixture
    def mock_movie_result(self):
        """Mock IMDB movie result"""
        movie = Mock()
        movie.movieID = "0133093"
        movie.__getitem__ = lambda self, key: {
            "title": "The Matrix",
            "year": 1999,
            "rating": 8.7,
            "genres": ["Action", "Sci-Fi"],
            "runtimes": ["136"],
            "directors": [{"name": "Lana Wachowski"}, {"name": "Lilly Wachowski"}],
            "cast": [{"name": "Keanu Reeves"}, {"name": "Laurence Fishburne"}],
            "plot outline": "A computer hacker learns about the true nature of reality.",
            "full-size cover url": "https://example.com/poster.jpg",
        }.get(key)
        movie.get = lambda key, default=None: {
            "title": "The Matrix",
            "year": 1999,
            "rating": 8.7,
            "genres": ["Action", "Sci-Fi"],
            "runtimes": ["136"],
            "directors": [{"name": "Lana Wachowski"}, {"name": "Lilly Wachowski"}],
            "cast": [{"name": "Keanu Reeves"}, {"name": "Laurence Fishburne"}],
            "plot outline": "A computer hacker learns about the true nature of reality.",
            "full-size cover url": "https://example.com/poster.jpg",
        }.get(key, default)
        return movie

    @pytest.mark.asyncio
    async def test_search_movie_success(self, movie_service, mock_movie_result):
        """Test successful movie search"""
        with patch.object(
            movie_service.ia, "search_movie", return_value=[mock_movie_result]
        ):
            with patch.object(movie_service.ia, "update"):
                success, message, movie_details = await movie_service.search_movie(
                    "The Matrix"
                )

                assert success == True
                assert "The Matrix" in message
                assert movie_details is not None
                assert movie_service.get_current_movie() == "The Matrix"

    @pytest.mark.asyncio
    async def test_search_movie_no_results(self, movie_service):
        """Test movie search with no results"""
        with patch.object(movie_service.ia, "search_movie", return_value=[]):
            success, message, movie_details = await movie_service.search_movie(
                "NonexistentMovie"
            )

            assert success == False
            assert "No movies found" in message
            assert movie_details is None

    @pytest.mark.asyncio
    async def test_search_movie_with_year_exact_match(
        self, movie_service, mock_movie_result
    ):
        """Test movie search with exact year match"""
        with patch.object(
            movie_service.ia, "search_movie", return_value=[mock_movie_result]
        ):
            with patch.object(movie_service.ia, "update"):
                success, message, movie_details = await movie_service.search_movie(
                    "The Matrix", 1999
                )

                assert success == True
                assert "The Matrix" in message
                assert movie_details is not None

    @pytest.mark.asyncio
    async def test_search_movie_with_year_fuzzy_match(self, movie_service):
        """Test movie search with fuzzy year matching"""
        # Create mock movie with different year
        mock_movie = Mock()
        mock_movie.movieID = "0133093"
        mock_movie.get = lambda key, default=None: {
            "title": "The Matrix",
            "year": 1999,  # Actual year
            "rating": 8.7,
            "genres": ["Action", "Sci-Fi"],
        }.get(key, default)

        with patch.object(movie_service.ia, "search_movie", return_value=[mock_movie]):
            with patch.object(movie_service.ia, "update"):
                # Search for 1997, should find 1999 (within 3 years)
                success, message, movie_details = await movie_service.search_movie(
                    "The Matrix", 1997
                )

                assert success == True
                assert "Found 1999, searched for 1997" in message

    @pytest.mark.asyncio
    async def test_find_best_match_no_year(self, movie_service, mock_movie_result):
        """Test finding best match without year filter"""
        movies = [mock_movie_result]
        best_match = await movie_service._find_best_match(movies)

        assert best_match == mock_movie_result

    @pytest.mark.asyncio
    async def test_find_best_match_exact_year(self, movie_service):
        """Test finding best match with exact year"""
        movie1 = Mock()
        movie1.get = lambda key, default=None: {"year": 1998}.get(key, default)

        movie2 = Mock()
        movie2.get = lambda key, default=None: {"year": 1999}.get(key, default)

        movies = [movie1, movie2]
        best_match = await movie_service._find_best_match(movies, 1999)

        assert best_match == movie2

    @pytest.mark.asyncio
    async def test_find_best_match_fuzzy_year(self, movie_service):
        """Test finding best match with fuzzy year matching"""
        movie1 = Mock()
        movie1.get = lambda key, default=None: {"year": 1995}.get(
            key, default
        )  # Too far

        movie2 = Mock()
        movie2.get = lambda key, default=None: {"year": 2001}.get(
            key, default
        )  # Close enough

        movies = [movie1, movie2]
        best_match = await movie_service._find_best_match(movies, 1999)

        assert best_match == movie2

    @pytest.mark.asyncio
    async def test_get_movie_details_success(self, movie_service, mock_movie_result):
        """Test getting detailed movie information"""
        with patch.object(movie_service.ia, "update") as mock_update:
            result = await movie_service._get_movie_details(mock_movie_result)

            mock_update.assert_called_once_with(mock_movie_result)
            assert result == mock_movie_result

    @pytest.mark.asyncio
    async def test_get_movie_details_error(self, movie_service, mock_movie_result):
        """Test handling error when getting movie details"""
        with patch.object(
            movie_service.ia, "update", side_effect=Exception("IMDB Error")
        ):
            result = await movie_service._get_movie_details(mock_movie_result)

            # Should return original object even on error
            assert result == mock_movie_result

    def test_current_movie_management(self, movie_service):
        """Test current movie getter/setter/clear functionality"""
        # Initially no current movie
        assert movie_service.get_current_movie() is None
        assert movie_service.get_current_movie_details() is None

        # Set current movie
        movie_service.current_movie = "Test Movie"
        movie_service.current_movie_details = {"title": "Test Movie"}

        assert movie_service.get_current_movie() == "Test Movie"
        assert movie_service.get_current_movie_details() == {"title": "Test Movie"}

        # Clear current movie
        movie_service.clear_current_movie()

        assert movie_service.get_current_movie() is None
        assert movie_service.get_current_movie_details() is None

    def test_extract_movie_info(self, movie_service, mock_movie_result):
        """Test extracting movie information for database storage"""
        movie_info = movie_service.extract_movie_info(mock_movie_result)

        assert movie_info["title"] == "The Matrix"
        assert movie_info["year"] == 1999
        assert movie_info["imdb_id"] == "0133093"
        assert "Action" in movie_info["genres"]
        assert movie_info["rating"] == 8.7
        assert "Keanu Reeves" in movie_info["cast"]
        assert "Lana Wachowski" in movie_info["directors"]

    def test_extract_movie_info_empty(self, movie_service):
        """Test extracting movie info from empty/None input"""
        movie_info = movie_service.extract_movie_info(None)
        assert movie_info == {}

        movie_info = movie_service.extract_movie_info({})
        assert isinstance(movie_info, dict)

    @pytest.mark.asyncio
    async def test_search_movie_exception_handling(self, movie_service):
        """Test exception handling during movie search"""
        with patch.object(
            movie_service.ia, "search_movie", side_effect=Exception("Search Error")
        ):
            success, message, movie_details = await movie_service.search_movie(
                "Test Movie"
            )

            assert success == False
            assert "Error searching for movie" in message
            assert movie_details is None

    def test_extract_movie_info_missing_fields(self, movie_service):
        """Test extracting movie info with missing fields"""
        minimal_movie = Mock()
        minimal_movie.movieID = "123456"
        minimal_movie.get = lambda key, default=None: {"title": "Minimal Movie"}.get(
            key, default
        )

        movie_info = movie_service.extract_movie_info(minimal_movie)

        assert movie_info["title"] == "Minimal Movie"
        assert movie_info["imdb_id"] == "123456"
        assert movie_info["genres"] == []
        assert movie_info["directors"] == []
        assert movie_info["cast"] == []


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])
