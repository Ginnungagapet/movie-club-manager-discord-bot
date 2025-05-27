"""
Tests for Discord bot commands
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import discord
from discord.ext import commands
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBotCommands:
    """Test cases for Discord bot commands"""

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot instance"""
        bot = Mock()
        bot.services = {"movie": Mock(), "rotation": Mock(), "rating": Mock()}
        bot.settings = Mock()
        bot.settings.min_rating = 1
        bot.settings.max_rating = 10
        return bot

    @pytest.fixture
    def mock_ctx(self):
        """Create mock Discord context"""
        ctx = Mock()
        ctx.author = Mock()
        ctx.author.name = "test_user"
        ctx.send = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.discord_username = "test_user"
        user.real_name = "Test User"
        user.rotation_position = 0
        return user

    @pytest.fixture
    def mock_movie_pick(self):
        """Create mock movie pick object"""
        pick = Mock()
        pick.id = 1
        pick.movie_title = "The Matrix"
        pick.movie_year = 1999
        pick.picker = Mock()
        pick.picker.real_name = "Test User"
        pick.picker.discord_username = "test_user"
        return pick


class TestRotationCommands(TestBotCommands):
    """Test rotation-related commands"""

    @pytest.mark.asyncio
    async def test_show_schedule_success(self, mock_bot, mock_ctx):
        """Test successful schedule display"""
        # Import here to avoid import issues
        try:
            from bot.commands.rotation import RotationCommands
        except ImportError:
            pytest.skip("RotationCommands not available")

        # Mock embed creation
        mock_embed = Mock()
        mock_bot.services["rotation"].create_schedule_embed = AsyncMock(
            return_value=mock_embed
        )

        # Create command instance and test
        rotation_commands = RotationCommands(mock_bot)
        await rotation_commands.show_schedule(mock_ctx, 5)

        # Verify calls
        mock_bot.services["rotation"].create_schedule_embed.assert_called_once_with(5)
        mock_ctx.send.assert_called_once_with(embed=mock_embed)

    @pytest.mark.asyncio
    async def test_check_my_turn_can_pick(self, mock_bot, mock_ctx):
        """Test checking turn when user can pick"""
        try:
            from bot.commands.rotation import RotationCommands
        except ImportError:
            pytest.skip("RotationCommands not available")

        # Mock permission check
        mock_bot.services["rotation"].can_user_pick = AsyncMock(
            return_value=(True, "You are the current picker")
        )

        # Create command instance and test
        rotation_commands = RotationCommands(mock_bot)
        await rotation_commands.check_my_turn(mock_ctx)

        # Verify permission check called
        mock_bot.services["rotation"].can_user_pick.assert_called_once_with("test_user")

        # Verify response sent
        mock_ctx.send.assert_called_once()


class TestMovieCommands(TestBotCommands):
    """Test movie-related commands"""

    @pytest.mark.asyncio
    async def test_pick_movie_no_permission(self, mock_bot, mock_ctx):
        """Test movie picking without permission"""
        try:
            from bot.commands.movies import MovieCommands
        except ImportError:
            pytest.skip("MovieCommands not available")

        # Mock permission denial
        mock_bot.services["rotation"].can_user_pick = AsyncMock(
            return_value=(False, "Not your turn")
        )

        # Create command instance and test
        movie_commands = MovieCommands(mock_bot)
        await movie_commands.pick_movie(mock_ctx, movie_input="The Matrix")

        # Verify permission check
        mock_bot.services["rotation"].can_user_pick.assert_called_once_with("test_user")

        # Verify error message sent
        mock_ctx.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_movie_command(self, mock_bot, mock_ctx):
        """Test movie search command (without picking)"""
        try:
            from bot.commands.movies import MovieCommands
        except ImportError:
            pytest.skip("MovieCommands not available")

        # Mock successful search
        mock_bot.services["movie"].search_movie = AsyncMock(
            return_value=(True, "Found", {"title": "The Matrix"})
        )

        # Mock message
        mock_search_msg = Mock()
        mock_search_msg.edit = AsyncMock()
        mock_ctx.send = AsyncMock(return_value=mock_search_msg)

        # Create command instance and test
        movie_commands = MovieCommands(mock_bot)
        await movie_commands.search_movie(mock_ctx, movie_input="The Matrix")

        # Verify search called
        mock_bot.services["movie"].search_movie.assert_called_once_with(
            "The Matrix", None
        )


class TestRatingCommands(TestBotCommands):
    """Test rating-related commands"""

    @pytest.mark.asyncio
    async def test_rate_movie_invalid_rating(self, mock_bot, mock_ctx):
        """Test movie rating with invalid rating value"""
        try:
            from bot.commands.ratings import RatingCommands
        except ImportError:
            pytest.skip("RatingCommands not available")

        # Create command instance and test
        rating_commands = RatingCommands(mock_bot)
        await rating_commands.rate_movie(
            mock_ctx, movie_id=1, rating=15
        )  # Invalid rating

        # Verify error message sent
        mock_ctx.send.assert_called_once()
        args = mock_ctx.send.call_args[0]
        assert "Rating must be between" in args[0]

    @pytest.mark.asyncio
    async def test_show_my_ratings_no_ratings(self, mock_bot, mock_ctx):
        """Test showing user's ratings when they have no ratings"""
        try:
            from bot.commands.ratings import RatingCommands
        except ImportError:
            pytest.skip("RatingCommands not available")

        # Mock empty ratings
        mock_bot.services["rating"].get_user_ratings = AsyncMock(return_value=[])

        # Create command instance and test
        rating_commands = RatingCommands(mock_bot)
        await rating_commands.show_my_ratings(mock_ctx)

        # Verify response
        mock_ctx.send.assert_called_once()
        args = mock_ctx.send.call_args[0]
        assert "haven't rated any movies" in args[0]


class TestParsers:
    """Test parsing utility functions"""

    def test_parse_movie_input_no_year(self):
        """Test parsing movie input without year"""
        from utils.parsers import parse_movie_input

        title, year = parse_movie_input("The Matrix")
        assert title == "The Matrix"
        assert year is None

    def test_parse_movie_input_with_year(self):
        """Test parsing movie input with year"""
        from utils.parsers import parse_movie_input

        title, year = parse_movie_input("The Matrix 1999")
        assert title == "The Matrix"
        assert year == 1999

    def test_parse_movie_input_edge_cases(self):
        """Test parsing movie input edge cases"""
        from utils.parsers import parse_movie_input

        # Movie title with numbers that shouldn't be parsed as year
        title, year = parse_movie_input("2001 A Space Odyssey")
        assert title == "2001 A Space Odyssey"
        assert year is None

        # Empty input
        title, year = parse_movie_input("")
        assert title == ""
        assert year is None

        # Only whitespace
        title, year = parse_movie_input("   ")
        assert title == ""
        assert year is None

    def test_parse_user_list(self):
        """Test parsing user list"""
        from utils.parsers import parse_user_list

        # With real names
        users = parse_user_list("user1:John,user2:Jane")
        assert users == [("user1", "John"), ("user2", "Jane")]

        # Mixed format
        users = parse_user_list("user1,user2:Jane")
        assert users == [("user1", "user1"), ("user2", "Jane")]

        # Empty input
        users = parse_user_list("")
        assert users == []

    def test_parse_rating_input(self):
        """Test parsing rating input"""
        from utils.parsers import parse_rating_input

        # Rating only
        rating, review = parse_rating_input("8")
        assert rating == 8
        assert review is None

        # Rating with review
        rating, review = parse_rating_input("8 Great movie!")
        assert rating == 8
        assert review == "Great movie!"

        # Invalid input
        rating, review = parse_rating_input("not a number")
        assert rating is None
        assert review is None

    def test_validate_discord_username(self):
        """Test Discord username validation"""
        from utils.parsers import validate_discord_username

        # Valid usernames
        assert validate_discord_username("user123") == True
        assert validate_discord_username("user_name") == True
        assert validate_discord_username("user.name") == True
        assert validate_discord_username("user-name") == True

        # Invalid usernames
        assert validate_discord_username("") == False
        assert validate_discord_username("a") == False  # Too short
        assert validate_discord_username("a" * 33) == False  # Too long
        assert validate_discord_username(".username") == False  # Starts with dot
        assert validate_discord_username("username.") == False  # Ends with dot
        assert validate_discord_username("user..name") == False  # Consecutive dots
        assert validate_discord_username("user@name") == False  # Invalid character

    def test_parse_movie_id_from_message(self):
        """Test extracting movie ID from message"""
        from utils.parsers import parse_movie_id_from_message

        # Standard format
        movie_id = parse_movie_id_from_message("Movie ID: 123")
        assert movie_id == 123

        # Alternative format
        movie_id = parse_movie_id_from_message("ID: 456")
        assert movie_id == 456

        # Hash format
        movie_id = parse_movie_id_from_message("Check movie #789")
        assert movie_id == 789

        # No ID found
        movie_id = parse_movie_id_from_message("No ID here")
        assert movie_id is None

    def test_clean_movie_title(self):
        """Test cleaning movie titles"""
        from utils.parsers import clean_movie_title

        # Extra whitespace
        title = clean_movie_title("  The   Matrix  ")
        assert title == "The Matrix"

        # Empty input
        title = clean_movie_title("")
        assert title == ""

        # Normal title
        title = clean_movie_title("The Matrix")
        assert title == "The Matrix"

    def test_extract_mentions_and_text(self):
        """Test extracting Discord mentions"""
        from utils.parsers import extract_mentions_and_text

        # With mentions
        mentions, text = extract_mentions_and_text(
            "Hello <@123456789> and <@!987654321> how are you?"
        )
        assert mentions == ["123456789", "987654321"]
        assert text == "Hello  and  how are you?"

        # No mentions
        mentions, text = extract_mentions_and_text("Hello everyone!")
        assert mentions == []
        assert text == "Hello everyone!"

        # Empty input
        mentions, text = extract_mentions_and_text("")
        assert mentions == []
        assert text == ""


class TestCommandParsing:
    """Test command parsing functions used by commands"""

    def test_movie_input_parsing_integration(self):
        """Test movie input parsing as used in commands"""
        from utils.parsers import parse_movie_input

        # Test various real-world inputs
        test_cases = [
            ("The Matrix", ("The Matrix", None)),
            ("The Matrix 1999", ("The Matrix", 1999)),
            ("Blade Runner 2049", ("Blade Runner", 2049)),
            ("2001: A Space Odyssey", ("2001: A Space Odyssey", None)),
            ("Star Wars Episode IV 1977", ("Star Wars Episode IV", 1977)),
        ]

        for input_str, expected in test_cases:
            result = parse_movie_input(input_str)
            assert result == expected, f"Failed for input: {input_str}"


# Mock command classes for testing if imports fail
class MockRotationCommands:
    def __init__(self, bot):
        self.bot = bot
        self.rotation_service = bot.services["rotation"]

    async def show_schedule(self, ctx, periods=5):
        embed = await self.rotation_service.create_schedule_embed(periods)
        await ctx.send(embed=embed)

    async def check_my_turn(self, ctx):
        username = ctx.author.name
        can_pick, reason = await self.rotation_service.can_user_pick(username)

        if can_pick:
            embed = Mock()
            embed.title = "🎯 Your Turn!"
        else:
            embed = Mock()
            embed.title = "⏰ Not Your Turn"

        await ctx.send(embed=embed)


class MockMovieCommands:
    def __init__(self, bot):
        self.bot = bot
        self.movie_service = bot.services["movie"]
        self.rotation_service = bot.services["rotation"]

    async def pick_movie(self, ctx, *, movie_input):
        username = ctx.author.name
        can_pick, reason = await self.rotation_service.can_user_pick(username)

        if not can_pick:
            embed = Mock()
            embed.title = "❌ Cannot Pick Movie"
            await ctx.send(embed=embed)
            return

        # Continue with movie picking logic...
        await ctx.send("Movie picked!")

    async def search_movie(self, ctx, *, movie_input):
        from utils.parsers import parse_movie_input

        movie_name, year = parse_movie_input(movie_input)

        success, message, movie_details = await self.movie_service.search_movie(
            movie_name, year
        )

        if success:
            await ctx.send("Movie found!")
        else:
            await ctx.send(message)


class MockRatingCommands:
    def __init__(self, bot):
        self.bot = bot
        self.rating_service = bot.services["rating"]

    async def rate_movie(self, ctx, movie_id: int, rating: int, *, review: str = None):
        if (
            rating < self.bot.settings.min_rating
            or rating > self.bot.settings.max_rating
        ):
            await ctx.send(
                f"❌ Rating must be between {self.bot.settings.min_rating} and {self.bot.settings.max_rating}!"
            )
            return

        await ctx.send("Rating added!")

    async def show_my_ratings(self, ctx):
        username = ctx.author.name
        ratings = await self.rating_service.get_user_ratings(username)

        if not ratings:
            await ctx.send("You haven't rated any movies yet!")
        else:
            await ctx.send("Your ratings displayed!")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])
