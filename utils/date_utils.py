"""
Date parsing and formatting utilities
"""

from datetime import datetime, date, timedelta
from typing import Optional, Union
import re


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string in various formats

    Args:
        date_str: Date string to parse

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    # Common date formats to try
    formats = [
        "%B %d, %Y",  # May 10, 2025
        "%b %d, %Y",  # May 10, 2025
        "%Y-%m-%d",  # 2025-05-10
        "%m/%d/%Y",  # 05/10/2025
        "%d/%m/%Y",  # 10/05/2025
        "%Y/%m/%d",  # 2025/05/10
        "%B %d %Y",  # May 10 2025
        "%b %d %Y",  # May 10 2025
        "%m-%d-%Y",  # 05-10-2025
        "%d-%m-%Y",  # 10-05-2025
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def format_date(dt: Union[datetime, date], format_type: str = "short") -> str:
    """
    Format datetime/date object for display

    Args:
        dt: datetime or date object
        format_type: 'short', 'long', 'discord', or custom format string

    Returns:
        Formatted date string
    """
    if not dt:
        return "Unknown"

    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())

    format_map = {
        "short": "%b %d",  # May 10
        "long": "%B %d, %Y",  # May 10, 2025
        "discord": "%b %d, %Y",  # May 10, 2025
        "iso": "%Y-%m-%d",  # 2025-05-10
        "full": "%A, %B %d, %Y",  # Monday, May 10, 2025
    }

    if format_type in format_map:
        return dt.strftime(format_map[format_type])
    else:
        # Assume it's a custom format string
        try:
            return dt.strftime(format_type)
        except ValueError:
            return dt.strftime("%b %d, %Y")  # Default fallback


def get_time_until(target_date: datetime) -> str:
    """
    Get human-readable time until target date

    Args:
        target_date: Target datetime

    Returns:
        Human-readable string like "3 days", "2 hours", etc.
    """
    if not target_date:
        return "Unknown"

    now = datetime.now()
    delta = target_date - now

    if delta.total_seconds() < 0:
        return "Past"

    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if days > 0:
        if days == 1:
            return "1 day"
        return f"{days} days"
    elif hours > 0:
        if hours == 1:
            return "1 hour"
        return f"{hours} hours"
    elif minutes > 0:
        if minutes == 1:
            return "1 minute"
        return f"{minutes} minutes"
    else:
        return "Less than a minute"


def get_time_since(past_date: datetime) -> str:
    """
    Get human-readable time since past date

    Args:
        past_date: Past datetime

    Returns:
        Human-readable string like "3 days ago", "2 hours ago", etc.
    """
    if not past_date:
        return "Unknown"

    now = datetime.now()
    delta = now - past_date

    if delta.total_seconds() < 0:
        return "Future"

    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60

    if days > 0:
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"
    elif hours > 0:
        if hours == 1:
            return "1 hour ago"
        return f"{hours} hours ago"
    elif minutes > 0:
        if minutes == 1:
            return "1 minute ago"
        return f"{minutes} minutes ago"
    else:
        return "Just now"


def is_within_period(
    check_date: datetime, start_date: datetime, end_date: datetime
) -> bool:
    """
    Check if a date falls within a period

    Args:
        check_date: Date to check
        start_date: Period start
        end_date: Period end

    Returns:
        True if date is within period
    """
    if not all([check_date, start_date, end_date]):
        return False

    return start_date <= check_date <= end_date


def get_next_occurrence(target_weekday: int, from_date: datetime = None) -> datetime:
    """
    Get next occurrence of a specific weekday

    Args:
        target_weekday: Target weekday (0=Monday, 6=Sunday)
        from_date: Starting date (default: now)

    Returns:
        Next occurrence of the weekday
    """
    if from_date is None:
        from_date = datetime.now()

    days_ahead = target_weekday - from_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7

    return from_date + timedelta(days=days_ahead)


def calculate_rotation_dates(
    start_date: datetime, position: int, period_days: int = 14
) -> tuple[datetime, datetime]:
    """
    Calculate rotation period dates for a given position

    Args:
        start_date: Rotation start date
        position: User's position in rotation (0-based)
        period_days: Length of each period in days

    Returns:
        Tuple of (period_start, period_end)
    """
    period_start = start_date + timedelta(days=period_days * position)
    period_end = period_start + timedelta(days=period_days)
    return period_start, period_end


def get_current_rotation_period(
    start_date: datetime, period_days: int = 14
) -> tuple[int, datetime, datetime]:
    """
    Get current rotation period information

    Args:
        start_date: Rotation start date
        period_days: Length of each period in days

    Returns:
        Tuple of (period_number, period_start, period_end)
    """
    now = datetime.now()
    days_since_start = (now - start_date).days
    period_number = days_since_start // period_days

    period_start = start_date + timedelta(days=period_number * period_days)
    period_end = period_start + timedelta(days=period_days)

    return period_number, period_start, period_end


def parse_relative_date(
    relative_str: str, from_date: datetime = None
) -> Optional[datetime]:
    """
    Parse relative date strings like "tomorrow", "next week", "in 3 days"

    Args:
        relative_str: Relative date string
        from_date: Base date (default: now)

    Returns:
        datetime object or None
    """
    if from_date is None:
        from_date = datetime.now()

    relative_str = relative_str.lower().strip()

    # Simple relative dates
    if relative_str in ["today", "now"]:
        return from_date
    elif relative_str == "tomorrow":
        return from_date + timedelta(days=1)
    elif relative_str == "yesterday":
        return from_date - timedelta(days=1)
    elif relative_str == "next week":
        return from_date + timedelta(weeks=1)
    elif relative_str == "last week":
        return from_date - timedelta(weeks=1)

    # Pattern matching for "in X days/weeks/months"
    patterns = [
        (r"in (\d+) days?", lambda x: from_date + timedelta(days=int(x))),
        (r"in (\d+) weeks?", lambda x: from_date + timedelta(weeks=int(x))),
        (r"in (\d+) months?", lambda x: from_date + timedelta(days=int(x) * 30)),
        (r"(\d+) days? ago", lambda x: from_date - timedelta(days=int(x))),
        (r"(\d+) weeks? ago", lambda x: from_date - timedelta(weeks=int(x))),
    ]

    for pattern, func in patterns:
        match = re.match(pattern, relative_str)
        if match:
            try:
                return func(match.group(1))
            except (ValueError, OverflowError):
                continue

    return None
