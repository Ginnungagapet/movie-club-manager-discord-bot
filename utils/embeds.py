"""
Discord embed creation utilities
"""

import discord
from typing import Dict, Any, Optional, List
from datetime import datetime


def create_movie_embed(
    movie_details: Dict[str, Any], title: str = "🎬 Movie", is_current: bool = False
) -> discord.Embed:
    """
    Create a standardized movie embed with IMDB information

    Args:
        movie_details: Movie information dictionary
        title: Embed title
        is_current: Whether this is the current movie selection

    Returns:
        Discord embed object
    """
    movie_title = movie_details.get("title", "Unknown")
    year = movie_details.get("year", "Unknown")
    movie_id = getattr(movie_details, "movieID", None)

    # Create embed
    embed = discord.Embed(
        title=title,
        description=f"**{movie_title}** ({year})",
        color=0x0099FF if is_current else 0x00FF00,
    )

    # Add IMDB link if available
    if movie_id:
        embed.url = f"https://www.imdb.com/title/tt{movie_id}/"

    # Add IMDB rating
    rating = movie_details.get("rating")
    if rating:
        embed.add_field(name="⭐ IMDB Rating", value=f"{rating}/10", inline=True)

    # Add genres (limit to 3)
    genres = movie_details.get("genres", [])
    if genres:
        embed.add_field(name="🎭 Genres", value=", ".join(genres[:3]), inline=True)

    # Add runtime
    runtime = movie_details.get("runtimes") or movie_details.get("runtime")
    if runtime:
        if isinstance(runtime, list) and runtime:
            runtime_str = f"{runtime[0]} min"
        elif isinstance(runtime, (int, str)):
            runtime_str = f"{runtime} min"
        else:
            runtime_str = None

        if runtime_str:
            embed.add_field(name="⏱️ Runtime", value=runtime_str, inline=True)

    # Add director(s)
    directors = movie_details.get("directors", [])
    if directors:
        if isinstance(directors[0], dict):
            director_names = [
                director.get("name", str(director)) for director in directors[:2]
            ]
        else:
            director_names = [str(director) for director in directors[:2]]
        embed.add_field(
            name="🎬 Director", value=", ".join(director_names), inline=True
        )

    # Add cast (top 3)
    cast = movie_details.get("cast", [])
    if cast:
        if isinstance(cast[0], dict):
            cast_names = [actor.get("name", str(actor)) for actor in cast[:3]]
        else:
            cast_names = [str(actor) for actor in cast[:3]]
        embed.add_field(name="🎭 Cast", value=", ".join(cast_names), inline=True)

    # Add plot
    plot = movie_details.get("plot outline") or movie_details.get("plot")
    if plot:
        if isinstance(plot, list):
            plot = plot[0] if plot else ""

        # Clean up plot text and truncate
        clean_plot = str(plot).replace("::Anonymous", "").replace("::IMDb", "").strip()
        truncated_plot = (
            clean_plot[:300] + "..." if len(clean_plot) > 300 else clean_plot
        )
        if truncated_plot:
            embed.add_field(name="📖 Plot", value=truncated_plot, inline=False)

    # Add poster if available
    poster_url = movie_details.get("full-size cover url") or movie_details.get(
        "poster_url"
    )
    if poster_url:
        embed.set_thumbnail(url=poster_url)

    # Add footer with IMDB link
    if movie_id:
        embed.set_footer(
            text="Click the title to view on IMDB",
            icon_url="https://m.media-amazon.com/images/G/01/imdb/images/social/imdb_logo.png",
        )

    return embed


def create_error_embed(message: str, title: str = "❌ Error") -> discord.Embed:
    """Create a standardized error embed"""
    return discord.Embed(title=title, description=message, color=0xFF0000)


def create_success_embed(message: str, title: str = "✅ Success") -> discord.Embed:
    """Create a standardized success embed"""
    return discord.Embed(title=title, description=message, color=0x00FF00)


def create_info_embed(message: str, title: str = "ℹ️ Information") -> discord.Embed:
    """Create a standardized info embed"""
    return discord.Embed(title=title, description=message, color=0x0099FF)


def create_warning_embed(message: str, title: str = "⚠️ Warning") -> discord.Embed:
    """Create a standardized warning embed"""
    return discord.Embed(title=title, description=message, color=0xFF6600)


def create_user_embed(
    user_data: Dict[str, Any], title: str = "👤 User"
) -> discord.Embed:
    """Create a user information embed"""
    embed = discord.Embed(title=title, color=0x0099FF)

    if "real_name" in user_data:
        embed.add_field(name="Name", value=user_data["real_name"], inline=True)

    if "discord_username" in user_data:
        embed.add_field(
            name="Discord", value=f"@{user_data['discord_username']}", inline=True
        )

    if "rotation_position" in user_data:
        embed.add_field(
            name="Position", value=f"#{user_data['rotation_position'] + 1}", inline=True
        )

    return embed


def create_stats_embed(
    stats: Dict[str, Any], title: str = "📊 Statistics"
) -> discord.Embed:
    """Create a statistics embed"""
    embed = discord.Embed(title=title, color=0x0099FF)

    for key, value in stats.items():
        # Format key as title case
        field_name = key.replace("_", " ").title()

        # Format value appropriately
        if isinstance(value, float):
            field_value = f"{value:.1f}"
        else:
            field_value = str(value)

        embed.add_field(name=field_name, value=field_value, inline=True)

    return embed


def create_list_embed(
    items: List[Dict[str, Any]], title: str = "📋 List", item_formatter: callable = None
) -> discord.Embed:
    """
    Create an embed displaying a list of items

    Args:
        items: List of items to display
        title: Embed title
        item_formatter: Function to format each item (item) -> (name, value)
    """
    embed = discord.Embed(title=title, color=0x0099FF)

    if not items:
        embed.add_field(name="Empty", value="No items to display", inline=False)
        return embed

    for i, item in enumerate(items):
        if item_formatter:
            try:
                name, value = item_formatter(item)
            except (ValueError, TypeError):
                name = f"Item {i + 1}"
                value = str(item)
        else:
            name = f"Item {i + 1}"
            value = str(item)

        embed.add_field(name=name, value=value, inline=False)

    return embed


def create_help_embed(
    commands: Dict[str, str], title: str = "🆘 Help"
) -> discord.Embed:
    """Create a help embed with command descriptions"""
    embed = discord.Embed(
        title=title, description="Available commands:", color=0x0099FF
    )

    for command, description in commands.items():
        embed.add_field(name=f"!{command}", value=description, inline=False)

    return embed


def create_rotation_status_embed(
    current_picker: Dict[str, Any], next_picker: Dict[str, Any]
) -> discord.Embed:
    """Create an embed showing current rotation status"""
    embed = discord.Embed(title="🎯 Rotation Status", color=0x00FF00)

    # Current picker
    current_name = current_picker.get("real_name", "Unknown")
    current_username = current_picker.get("discord_username", "Unknown")
    current_period = current_picker.get("period", "Unknown")

    embed.add_field(
        name="Current Picker",
        value=f"**{current_name}** (@{current_username})\n📅 {current_period}",
        inline=False,
    )

    # Next picker
    next_name = next_picker.get("real_name", "Unknown")
    next_username = next_picker.get("discord_username", "Unknown")
    next_period = next_picker.get("period", "Unknown")
    next_status = next_picker.get("status", "")

    embed.add_field(
        name="Next Up",
        value=f"**{next_name}** (@{next_username}){next_status}\n📅 {next_period}",
        inline=False,
    )

    return embed


def create_movie_rating_embed(
    movie_title: str, ratings: List[Dict[str, Any]], average_rating: float = None
) -> discord.Embed:
    """Create an embed showing movie ratings"""
    embed = discord.Embed(title=f"🎬 {movie_title}", color=0x00FF00)

    if average_rating:
        embed.add_field(
            name="⭐ Average Rating",
            value=f"{average_rating:.1f}/10 ({len(ratings)} rating{'s' if len(ratings) != 1 else ''})",
            inline=False,
        )

    if not ratings:
        embed.add_field(
            name="No Ratings Yet",
            value="Be the first to rate this movie!",
            inline=False,
        )
        return embed

    for rating in ratings:
        rater_name = rating.get("rater_name", "Unknown")
        rating_value = rating.get("rating", 0)
        review = rating.get("review", "")

        rating_text = f"⭐ {rating_value}/10"
        if review:
            rating_text += f"\n*\"{review[:100]}{'...' if len(review) > 100 else ''}\"*"

        embed.add_field(name=rater_name, value=rating_text, inline=True)

    return embed


def add_timestamp_footer(
    embed: discord.Embed, timestamp: datetime = None
) -> discord.Embed:
    """Add a timestamp footer to an embed"""
    if timestamp is None:
        timestamp = datetime.now()

    embed.timestamp = timestamp
    return embed


def truncate_field_value(value: str, max_length: int = 1024) -> str:
    """Truncate field value to Discord's limit"""
    if len(value) <= max_length:
        return value

    return value[: max_length - 3] + "..."


def create_paginated_embed_fields(
    items: List[Any],
    items_per_page: int = 10,
    page: int = 1,
    formatter: callable = None,
) -> List[Dict[str, str]]:
    """
    Create fields for paginated embeds

    Args:
        items: List of items to paginate
        items_per_page: Number of items per page
        page: Current page (1-based)
        formatter: Function to format each item

    Returns:
        List of field dictionaries
    """
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_items = items[start_idx:end_idx]

    fields = []

    for i, item in enumerate(page_items, start=start_idx + 1):
        if formatter:
            try:
                name, value = formatter(item, i)
            except (ValueError, TypeError):
                name = f"Item {i}"
                value = str(item)
        else:
            name = f"Item {i}"
            value = str(item)

        fields.append(
            {"name": name, "value": truncate_field_value(value), "inline": False}
        )

    return fields
