"""
Input parsing utilities for bot commands
"""

import re
from typing import Optional, Tuple, List, Dict, Any


def parse_movie_input(movie_input: str) -> Tuple[str, Optional[int]]:
    """
    Parse movie input to extract movie name and optional year

    Examples:
        "The Matrix" -> ("The Matrix", None)
        "The Matrix 1999" -> ("The Matrix", 1999)
        "The Batman 2022" -> ("The Batman", 2022)
        "2001 A Space Odyssey" -> ("2001 A Space Odyssey", None)

    Args:
        movie_input: Raw movie input string

    Returns:
        Tuple of (movie_name, year)
    """
    if not movie_input:
        return "", None

    movie_input = movie_input.strip()

    # Look for a 4-digit year at the end of the string
    # Must be between 1900-2030 to avoid parsing movie titles with numbers
    year_pattern = r"\s+(19\d{2}|20[0-2]\d|2030)$"
    match = re.search(year_pattern, movie_input)

    if match:
        year = int(match.group(1))
        movie_name = movie_input[: match.start()].strip()
        return movie_name, year
    else:
        return movie_input, None


def parse_user_list(user_list_str: str) -> List[Tuple[str, str]]:
    """
    Parse user list string into username:real_name pairs

    Examples:
        "user1:John,user2:Jane" -> [("user1", "John"), ("user2", "Jane")]
        "user1,user2:Jane" -> [("user1", "user1"), ("user2", "Jane")]

    Args:
        user_list_str: Comma-separated user list

    Returns:
        List of (username, real_name) tuples
    """
    if not user_list_str:
        return []

    user_data = []

    for pair in user_list_str.split(","):
        pair = pair.strip()
        if not pair:
            continue

        if ":" in pair:
            username, real_name = pair.split(":", 1)
            user_data.append((username.strip(), real_name.strip()))
        else:
            username = pair
            user_data.append((username.strip(), username.strip()))

    return user_data


def parse_rating_input(rating_str: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse rating input to extract rating and optional review

    Examples:
        "8" -> (8, None)
        "8 Great movie!" -> (8, "Great movie!")
        "10 Amazing cinematography and plot" -> (10, "Amazing cinematography and plot")

    Args:
        rating_str: Raw rating input string

    Returns:
        Tuple of (rating, review_text)
    """
    if not rating_str:
        return None, None

    rating_str = rating_str.strip()

    # Try to extract rating (first number) and review (rest)
    match = re.match(r"^(\d+)(?:\s+(.+))?$", rating_str)

    if match:
        try:
            rating = int(match.group(1))
            review = match.group(2).strip() if match.group(2) else None
            return rating, review
        except ValueError:
            return None, None

    return None, None


def validate_discord_username(username: str) -> bool:
    """
    Validate Discord username format

    Args:
        username: Discord username to validate

    Returns:
        True if valid username format
    """
    if not username or not isinstance(username, str):
        return False

    username = username.strip()

    # Discord username rules (simplified)
    # - 2-32 characters
    # - alphanumeric, dots, underscores, hyphens
    # - cannot start/end with dots
    # - cannot have consecutive dots

    if len(username) < 2 or len(username) > 32:
        return False

    if username.startswith(".") or username.endswith("."):
        return False

    if ".." in username:
        return False

    # Check allowed characters
    allowed_pattern = r"^[a-zA-Z0-9._-]+$"
    return bool(re.match(allowed_pattern, username))


def parse_movie_id_from_message(message: str) -> Optional[int]:
    """
    Extract movie ID from a message (useful for parsing bot responses)

    Args:
        message: Message text that might contain a movie ID

    Returns:
        Movie ID if found, None otherwise
    """
    if not message:
        return None

    # Look for patterns like "Movie ID: 123" or "ID: 123"
    patterns = [
        r"Movie ID:\s*(\d+)",
        r"ID:\s*(\d+)",
        r"#(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue

    return None


def clean_movie_title(title: str) -> str:
    """
    Clean movie title by removing extra whitespace and formatting

    Args:
        title: Raw movie title

    Returns:
        Cleaned movie title
    """
    if not title:
        return ""

    # Remove extra whitespace
    title = " ".join(title.split())

    return title.strip()


def extract_mentions_and_text(message_content: str) -> Tuple[List[str], str]:
    """
    Extract Discord mentions and remaining text from message

    Args:
        message_content: Raw message content

    Returns:
        Tuple of (mentioned_users, remaining_text)
    """
    if not message_content:
        return [], ""

    # Discord mention patterns
    mention_pattern = r"<@!?(\d+)>"
    mentions = re.findall(mention_pattern, message_content)

    # Remove mentions from text
    remaining_text = re.sub(mention_pattern, "", message_content).strip()

    return mentions, remaining_text
