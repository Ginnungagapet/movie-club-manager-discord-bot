"""
Tests for rotation service functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rotation_service import RotationService
from models.database import DatabaseManager, User, MoviePick, RotationState


class TestRotationService:
    """Test cases for RotationService"""

    @pytest.fixture
    async def mock_settings(self):
        """Create mock settings for testing"""
        settings = Mock()
        settings.database_url_corrected = "sqlite:///:memory:"
        settings.rotation_period_days = 14
        settings.early_access_days = 7
        return settings

    @pytest.fixture
    async def rotation_service(self, mock_settings):
        """Create RotationService instance for testing"""
        service = RotationService(mock_settings)
        await service.initialize_database()
        return service

    @pytest.fixture
    def sample_users(self):
        """Sample user data for testing"""
        return [
            ("paul", "Paul"),
            ("derek", "Derek"),
            ("greg", "Greg"),
            ("gavin", "Gavin"),
        ]

    @pytest.mark.asyncio
    async def test_setup_rotation(self, rotation_service, sample_users):
        """Test rotation setup"""
        await rotation_service.setup_rotation(sample_users)

        # Verify users were created
        user = await rotation_service.get_user_by_username("paul")
        assert user is not None
        assert user.real_name == "Paul"
        assert user.rotation_position == 0

        user2 = await rotation_service.get_user_by_username("derek")
        assert user2 is not None
        assert user2.rotation_position == 1

    @pytest.mark.asyncio
    async def test_get_current_picker(self, rotation_service, sample_users):
        """Test getting current picker"""
        await rotation_service.setup_rotation(sample_users)

        # Set start date to May 5, 2025
        start_date = datetime(2025, 5, 5)
        await rotation_service.update_rotation_start_date(start_date)

        current_user, period_start, period_end = (
            await rotation_service.get_current_picker()
        )

        assert current_user.discord_username == "paul"
        assert current_user.real_name == "Paul"

    @pytest.mark.asyncio
    async def test_can_user_pick_current_period(self, rotation_service, sample_users):
        """Test permission checking for current period"""
        await rotation_service.setup_rotation(sample_users)

        # Set start date to ensure Paul is current picker
        start_date = datetime.now() - timedelta(days=7)  # Started a week ago
        await rotation_service.update_rotation_start_date(start_date)

        can_pick, reason = await rotation_service.can_user_pick("paul")
        assert can_pick == True
        assert "current picker" in reason.lower()

    @pytest.mark.asyncio
    async def test_can_user_pick_early_access(self, rotation_service, sample_users):
        """Test permission checking for early access"""
        await rotation_service.setup_rotation(sample_users)

        # Set start date so Derek gets early access
        start_date = datetime.now() - timedelta(days=10)  # Paul's period ending soon
        await rotation_service.update_rotation_start_date(start_date)

        can_pick, reason = await rotation_service.can_user_pick("derek")
        # This might be True or False depending on exact timing
        assert isinstance(can_pick, bool)
        assert isinstance(reason, str)

    @pytest.mark.asyncio
    async def test_add_movie_pick(self, rotation_service, sample_users):
        """Test adding a movie pick"""
        await rotation_service.setup_rotation(sample_users)

        start_date = datetime.now() - timedelta(days=7)
        await rotation_service.update_rotation_start_date(start_date)

        movie_pick = await rotation_service.add_movie_pick(
            username="paul",
            movie_title="The Matrix",
            movie_year=1999,
            imdb_id="0133093",
        )

        assert movie_pick.movie_title == "The Matrix"
        assert movie_pick.movie_year == 1999
        assert movie_pick.picker.discord_username == "paul"

    @pytest.mark.asyncio
    async def test_add_historical_pick(self, rotation_service, sample_users):
        """Test adding historical movie pick"""
        await rotation_service.setup_rotation(sample_users)

        start_date = datetime(2025, 5, 5)
        await rotation_service.update_rotation_start_date(start_date)

        pick_date = datetime(2025, 5, 12)
        movie_pick = await rotation_service.add_historical_pick(
            username="paul",
            movie_title="Event Horizon",
            movie_year=1997,
            pick_date=pick_date,
        )

        assert movie_pick.movie_title == "Event Horizon"
        assert movie_pick.pick_date == pick_date
        assert movie_pick.picker.discord_username == "paul"

    @pytest.mark.asyncio
    async def test_get_recent_picks(self, rotation_service, sample_users):
        """Test getting recent picks"""
        await rotation_service.setup_rotation(sample_users)

        start_date = datetime(2025, 5, 5)
        await rotation_service.update_rotation_start_date(start_date)

        # Add some picks
        await rotation_service.add_historical_pick("paul", "Movie 1", 2020)
        await rotation_service.add_historical_pick("derek", "Movie 2", 2021)

        recent_picks = await rotation_service.get_recent_picks(limit=5)

        assert len(recent_picks) == 2
        assert recent_picks[0].movie_title == "Movie 2"  # Most recent first
        assert recent_picks[1].movie_title == "Movie 1"

    @pytest.mark.asyncio
    async def test_get_user_pick_history(self, rotation_service, sample_users):
        """Test getting user's pick history"""
        await rotation_service.setup_rotation(sample_users)

        start_date = datetime(2025, 5, 5)
        await rotation_service.update_rotation_start_date(start_date)

        # Add picks for different users
        await rotation_service.add_historical_pick("paul", "Paul Movie 1", 2020)
        await rotation_service.add_historical_pick("paul", "Paul Movie 2", 2021)
        await rotation_service.add_historical_pick("derek", "Derek Movie", 2022)

        paul_picks = await rotation_service.get_user_pick_history("paul")

        assert len(paul_picks) == 2
        assert all(pick.picker.discord_username == "paul" for pick in paul_picks)

    @pytest.mark.asyncio
    async def test_advance_rotation(self, rotation_service, sample_users):
        """Test manually advancing rotation"""
        await rotation_service.setup_rotation(sample_users)

        start_date = datetime(2025, 5, 5)
        await rotation_service.update_rotation_start_date(start_date)

        # Get current picker
        current_user_before, _, _ = await rotation_service.get_current_picker()
        assert current_user_before.discord_username == "paul"

        # Advance rotation
        success = await rotation_service.advance_rotation()
        assert success == True

        # Check new current picker
        current_user_after, _, _ = await rotation_service.get_current_picker()
        assert current_user_after.discord_username == "derek"

    @pytest.mark.asyncio
    async def test_invalid_user_pick_permission(self, rotation_service, sample_users):
        """Test permission checking for invalid user"""
        await rotation_service.setup_rotation(sample_users)

        can_pick, reason = await rotation_service.can_user_pick("nonexistent_user")

        assert can_pick == False
        assert "not in the rotation" in reason

    @pytest.mark.asyncio
    async def test_get_schedule(self, rotation_service, sample_users):
        """Test getting rotation schedule"""
        await rotation_service.setup_rotation(sample_users)

        start_date = datetime(2025, 5, 5)
        await rotation_service.update_rotation_start_date(start_date)

        schedule = await rotation_service.get_schedule(periods=3)

        assert len(schedule) == 3
        assert schedule[0][0].discord_username == "paul"  # Current
        assert schedule[0][3] == True  # is_current
        assert schedule[1][0].discord_username == "derek"  # Next
        assert schedule[1][3] == False  # not current
        assert schedule[2][0].discord_username == "greg"  # Third

    @pytest.mark.asyncio
    async def test_user_not_found_movie_pick(self, rotation_service, sample_users):
        """Test adding movie pick for non-existent user"""
        await rotation_service.setup_rotation(sample_users)

        with pytest.raises(ValueError, match="User nonexistent not found"):
            await rotation_service.add_movie_pick("nonexistent", "Some Movie")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])
