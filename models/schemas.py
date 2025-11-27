"""
Data validation schemas for the Movie Club Bot
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass


@dataclass
class UserSchema:
    """Schema for user data validation"""

    discord_username: str
    real_name: str
    rotation_position: Optional[int] = None

    def __post_init__(self):
        self.discord_username = self.discord_username.strip()
        self.real_name = self.real_name.strip()

        if not self.discord_username:
            raise ValueError("Discord username cannot be empty")
        if not self.real_name:
            raise ValueError("Real name cannot be empty")
        if len(self.discord_username) > 50:
            raise ValueError("Discord username too long (max 50 characters)")
        if len(self.real_name) > 100:
            raise ValueError("Real name too long (max 100 characters)")


@dataclass
class MoviePickSchema:
    """Schema for movie pick data validation"""

    picker_username: str
    movie_title: str
    movie_year: Optional[int] = None
    imdb_id: Optional[str] = None
    movie_details: Optional[Dict[str, Any]] = None
    pick_date: Optional[datetime] = None

    def __post_init__(self):
        self.picker_username = self.picker_username.strip()
        self.movie_title = self.movie_title.strip()

        if not self.picker_username:
            raise ValueError("Picker username cannot be empty")
        if not self.movie_title:
            raise ValueError("Movie title cannot be empty")
        if len(self.movie_title) > 200:
            raise ValueError("Movie title too long (max 200 characters)")

        if self.movie_year is not None:
            if not (1800 <= self.movie_year <= 2100):
                raise ValueError("Movie year must be between 1800 and 2100")

        if self.imdb_id is not None:
            self.imdb_id = self.imdb_id.strip()
            if len(self.imdb_id) > 20:
                raise ValueError("IMDB ID too long (max 20 characters)")

        if self.movie_details is None:
            self.movie_details = {}


@dataclass
class MovieRatingSchema:
    """Schema for movie rating data validation"""

    rater_username: str
    movie_pick_id: int
    rating: int
    review_text: Optional[str] = None

    def __post_init__(self):
        self.rater_username = self.rater_username.strip()

        if not self.rater_username:
            raise ValueError("Rater username cannot be empty")

        if not (1.0 <= self.rating <= 10.0):
            raise ValueError("Rating must be between 1 and 10")

        if self.movie_pick_id <= 0:
            raise ValueError("Movie pick ID must be positive")

        if self.review_text is not None:
            self.review_text = self.review_text.strip()
            if len(self.review_text) > 1000:
                raise ValueError("Review text too long (max 1000 characters)")
            if not self.review_text:
                self.review_text = None


@dataclass
class RotationSetupSchema:
    """Schema for rotation setup data validation"""

    user_data: List[tuple[str, str]]  # List of (username, real_name) tuples
    start_date: Optional[datetime] = None

    def __post_init__(self):
        if not self.user_data:
            raise ValueError("User data cannot be empty")

        if len(self.user_data) < 2:
            raise ValueError("Need at least 2 users for rotation")

        # Validate each user
        usernames = set()
        real_names = set()

        for username, real_name in self.user_data:
            user_schema = UserSchema(username, real_name)

            # Check for duplicates
            if user_schema.discord_username.lower() in usernames:
                raise ValueError(f"Duplicate username: {user_schema.discord_username}")
            if user_schema.real_name.lower() in real_names:
                raise ValueError(f"Duplicate real name: {user_schema.real_name}")

            usernames.add(user_schema.discord_username.lower())
            real_names.add(user_schema.real_name.lower())


@dataclass
class MovieSearchSchema:
    """Schema for movie search parameters"""

    query: str
    year: Optional[int] = None

    def __post_init__(self):
        self.query = self.query.strip()

        if not self.query:
            raise ValueError("Search query cannot be empty")
        if len(self.query) > 100:
            raise ValueError("Search query too long (max 100 characters)")

        if self.year is not None:
            if not (1800 <= self.year <= 2100):
                raise ValueError("Year must be between 1800 and 2100")


def validate_user_data(discord_username: str, real_name: str) -> UserSchema:
    """Validate and return user data schema"""
    return UserSchema(discord_username, real_name)


def validate_movie_pick(
    picker_username: str,
    movie_title: str,
    movie_year: int = None,
    imdb_id: str = None,
    movie_details: dict = None,
) -> MoviePickSchema:
    """Validate and return movie pick schema"""
    return MoviePickSchema(
        picker_username, movie_title, movie_year, imdb_id, movie_details
    )


def validate_movie_rating(
    rater_username: str, movie_pick_id: int, rating: int, review_text: str = None
) -> MovieRatingSchema:
    """Validate and return movie rating schema"""
    return MovieRatingSchema(rater_username, movie_pick_id, rating, review_text)


def validate_rotation_setup(
    user_data: List[tuple[str, str]], start_date: datetime = None
) -> RotationSetupSchema:
    """Validate and return rotation setup schema"""
    return RotationSetupSchema(user_data, start_date)


def validate_movie_search(query: str, year: int = None) -> MovieSearchSchema:
    """Validate and return movie search schema"""
    return MovieSearchSchema(query, year)
