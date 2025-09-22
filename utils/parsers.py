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


def parse_rating_input(rating_str: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse rating input to extract rating and optional review

    Examples:
        "8.5" -> (8.5, None)
        "8.5 Great movie!" -> (8.5, "Great movie!")
        "10.0 Amazing cinematography and plot" -> (10.0, "Amazing cinematography and plot")
        "7" -> (7.0, None)

    Args:
        rating_str: Raw rating input string

    Returns:
        Tuple of (rating, review_text)
    """
    if not rating_str:
        return None, None

    rating_str = rating_str.strip()

    # Try to extract rating (first number, can be int or float) and review (rest)
    match = re.match(r"^(\d+\.?\d*)(?:\s+(.+))?$", rating_str)

    if match:
        try:
            rating = float(match.group(1))
            review = match.group(2).strip() if match.group(2) else None
            return rating, review
        except ValueError:
            return None, None

    return None, None


def parse_movie_title_and_review(
    input_str: str, known_movies: List[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Parse input to separate movie title from review text
    Uses known movie titles to make better guesses

    Examples:
        "The Matrix Amazing effects" -> ("The Matrix", "Amazing effects")
        "Blade Runner 2049 Visually stunning" -> ("Blade Runner 2049", "Visually stunning")
    """
    if not input_str:
        return "", None

    input_str = input_str.strip()

    # If we have known movies, try to match against them
    if known_movies:
        # Sort by length (longest first) to match longer titles first
        sorted_movies = sorted(known_movies, key=len, reverse=True)

        for movie in sorted_movies:
            # Case-insensitive matching
            if input_str.lower().startswith(movie.lower()):
                remaining = input_str[len(movie) :].strip()
                return movie, remaining if remaining else None

            # Also try fuzzy matching for the whole input
            # This helps when user types most of the title
            if len(input_str.split()) <= 5:  # Reasonable movie title length
                match = fuzzy_match_movie_title(input_str, [movie])
                if match:
                    return match, None

    # Improved fallback: Try to identify where the review might start
    # Look for common review starter words
    review_starters = [
        "amazing",
        "great",
        "good",
        "bad",
        "terrible",
        "awesome",
        "excellent",
        "horrible",
        "boring",
        "fantastic",
        "brilliant",
        "awful",
        "perfect",
        "loved",
        "hated",
        "enjoyed",
        "disliked",
        "best",
        "worst",
        "beautiful",
        "stunning",
        "disappointing",
        "incredible",
        "outstanding",
        "mediocre",
    ]

    words = input_str.split()

    # Look for review starter words
    for i, word in enumerate(words):
        if word.lower() in review_starters and i > 0:
            # Found a likely review start
            title = " ".join(words[:i])
            review = " ".join(words[i:])
            return title, review

    # If no review starters found, assume the whole thing is the title
    # (user can always use !update_rating to add a review later)
    return input_str, None


def parse_command_args(args_str: str, expected_args: List[str]) -> Dict[str, Any]:
    """
    Parse command arguments based on expected argument names

    Args:
        args_str: Raw argument string
        expected_args: List of expected argument names

    Returns:
        Dictionary of parsed arguments
    """
    if not args_str or not expected_args:
        return {}

    # Simple space-based parsing for now
    # Could be enhanced for more complex parsing
    parts = args_str.split()
    result = {}

    for i, arg_name in enumerate(expected_args):
        if i < len(parts):
            result[arg_name] = parts[i]
        else:
            result[arg_name] = None

    # Join remaining parts as the last argument if it exists
    if len(parts) > len(expected_args) and expected_args:
        last_arg = expected_args[-1]
        remaining_parts = parts[len(expected_args) - 1 :]
        result[last_arg] = " ".join(remaining_parts)

    return result


def parse_time_range(time_str: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse time range input for commands

    Examples:
        "5" -> (5, "count")
        "5 days" -> (5, "days")
        "last 10" -> (10, "count")

    Args:
        time_str: Time range string

    Returns:
        Tuple of (number, unit)
    """
    if not time_str:
        return None, None

    time_str = time_str.strip().lower()

    # Pattern for "number unit" or just "number"
    patterns = [
        r"^(\d+)\s+(days?|weeks?|months?|years?)$",
        r"^(?:last\s+)?(\d+)$",
        r"^(\d+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, time_str)
        if match:
            try:
                number = int(match.group(1))
                unit = match.group(2) if len(match.groups()) > 1 else "count"
                return number, unit
            except (ValueError, IndexError):
                continue

    return None, None


def parse_quoted_strings(input_str: str) -> List[str]:
    """
    Parse input string and extract quoted strings while preserving spaces

    Examples:
        'word "quoted string" another' -> ['word', 'quoted string', 'another']
        '"first quote" "second quote"' -> ['first quote', 'second quote']

    Args:
        input_str: Input string with potential quotes

    Returns:
        List of parsed strings
    """
    if not input_str:
        return []

    # Regular expression to match quoted strings or individual words
    pattern = r'"([^"]*)"|(\S+)'
    matches = re.findall(pattern, input_str)

    # Extract non-empty groups from matches
    result = []
    for quoted, unquoted in matches:
        if quoted:
            result.append(quoted)
        elif unquoted:
            result.append(unquoted)

    return result


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


def validate_rating(rating: float) -> bool:
    """
    Validate rating value

    Args:
        rating: Rating value to validate

    Returns:
        True if valid rating (1.0 - 10.0)
    """
    return isinstance(rating, (int, float)) and 1.0 <= rating <= 10.0


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

    # Remove common prefixes/suffixes that might interfere
    prefixes_to_remove = ["the ", "a ", "an "]

    title_lower = title.lower()
    for prefix in prefixes_to_remove:
        if title_lower.startswith(prefix):
            # Only remove if it's not the entire title
            if len(title) > len(prefix):
                remaining = title[len(prefix) :]
                # Capitalize first letter of remaining title
                title = remaining[0].upper() + remaining[1:] if remaining else title
                break

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


def normalize_movie_title(title: str) -> str:
    """
    Normalize movie title for better matching

    Args:
        title: Movie title to normalize

    Returns:
        Normalized title
    """
    if not title:
        return ""

    # Convert to lowercase and remove extra spaces
    normalized = " ".join(title.lower().split())

    # Remove common punctuation that might interfere with matching
    normalized = re.sub(r"[^\w\s]", "", normalized)

    return normalized


def fuzzy_match_movie_title(
    search_title: str, movie_titles: List[str], threshold: float = 0.6
) -> Optional[str]:
    """
    Find the best matching movie title using fuzzy matching

    Args:
        search_title: Title to search for
        movie_titles: List of available movie titles
        threshold: Minimum similarity threshold (0.0 - 1.0)

    Returns:
        Best matching title or None if no good match found
    """
    if not search_title or not movie_titles:
        return None

    search_normalized = normalize_movie_title(search_title)
    best_match = None
    best_score = 0.0

    for title in movie_titles:
        title_normalized = normalize_movie_title(title)

        # Simple word-based matching
        search_words = set(search_normalized.split())
        title_words = set(title_normalized.split())

        if not search_words or not title_words:
            continue

        # Calculate Jaccard similarity
        intersection = len(search_words.intersection(title_words))
        union = len(search_words.union(title_words))

        if union > 0:
            score = intersection / union

            # Bonus for exact substring matches
            if (
                search_normalized in title_normalized
                or title_normalized in search_normalized
            ):
                score += 0.2

            if score > best_score and score >= threshold:
                best_score = score
                best_match = title

    return best_match
