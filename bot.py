"""
Discord Movie Genre Wheel Bot

A Discord bot that spins a wheel to randomly select movie genres 
with animated GIF visualization using modern Python features.
"""

from __future__ import annotations

import asyncio
import io
import math
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Final, Optional

import discord
import imageio
import numpy as np
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

# Local
from movie_manager import MovieManager

# Type aliases for better readability
Color = tuple[int, int, int]
Position = tuple[int, int]


class MovieGenreWheel:
    """A movie genre wheel that creates spinning animations and manages genres."""
    
    # Class constants
    DEFAULT_GENRES: Final[list[str]] = [
        "Action", "Adventure", "Animation", "Biography", "Comedy",
        "Crime", "Documentary", "Drama", "Family", "Fantasy",
        "Film-Noir", "History", "Horror", "Music", "Musical",
        "Mystery", "Romance", "Sci-Fi", "Sport", "Thriller",
        "War", "Western"
    ]
    
    WHEEL_COLORS: Final[list[Color]] = [
        (255, 0, 0), (255, 127, 0), (255, 255, 0), (127, 255, 0),
        (0, 255, 0), (0, 255, 127), (0, 255, 255), (0, 127, 255),
        (0, 0, 255), (127, 0, 255), (255, 0, 255), (255, 0, 127),
        (192, 192, 192), (128, 128, 128), (128, 0, 0), (128, 128, 0),
        (0, 128, 0), (0, 128, 128), (0, 0, 128), (128, 0, 128),
        (170, 110, 40), (128, 128, 64)
    ]
    
    # Image settings
    IMAGE_SIZE: Final[int] = 500
    RADIUS_OFFSET: Final[int] = 20
    TEXT_RADIUS_RATIO: Final[float] = 0.7
    CENTER_CIRCLE_RADIUS: Final[int] = 20
    POINTER_LENGTH: Final[int] = 30
    POINTER_WIDTH: Final[int] = 15
    
    # Animation settings
    ANIMATION_FRAMES: Final[int] = 30
    FULL_ROTATIONS: Final[int] = 3
    GIF_DURATION: Final[float] = 0.07
    
    def __init__(self) -> None:
        """Initialize the wheel with default genres."""
        self.genres = self.DEFAULT_GENRES.copy()
    
    def spin_wheel(self) -> str:
        """
        Spin the wheel and return a randomly selected genre.
        
        Uses cryptographically secure randomness for true randomness.
        
        Returns:
            str: A randomly selected movie genre
            
        Raises:
            ValueError: If no genres are available
        """
        if not self.genres:
            raise ValueError("No genres available to spin")
        return secrets.choice(self.genres)
    
    def add_genre(self, genre: str) -> bool:
        """
        Add a new genre to the wheel.
        
        Args:
            genre: The genre name to add
            
        Returns:
            bool: True if genre was added, False if it already exists
        """
        genre = genre.strip()
        if not genre:
            return False
            
        if genre not in self.genres:
            self.genres.append(genre)
            return True
        return False
    
    def remove_genre(self, genre: str) -> bool:
        """
        Remove a genre from the wheel.
        
        Args:
            genre: The genre name to remove
            
        Returns:
            bool: True if genre was removed, False if it wasn't found
        """
        try:
            self.genres.remove(genre.strip())
            return True
        except ValueError:
            return False
    
    @property
    def genre_list(self) -> list[str]:
        """Get a copy of the current genres list."""
        return self.genres.copy()
    
    @property
    def genre_count(self) -> int:
        """Get the number of genres on the wheel."""
        return len(self.genres)
    
    def _get_center_and_radius(self) -> tuple[Position, int]:
        """Calculate the center position and radius of the wheel."""
        center = (self.IMAGE_SIZE // 2, self.IMAGE_SIZE // 2)
        radius = (self.IMAGE_SIZE // 2) - self.RADIUS_OFFSET
        return center, radius
    
    def _get_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load a font, falling back to default if Arial is not available."""
        try:
            return ImageFont.truetype("arial.ttf", 14)
        except (OSError, IOError):
            return ImageFont.load_default()
    
    def _calculate_text_position(
        self, 
        center: Position, 
        radius: int, 
        angle: float
    ) -> Position:
        """Calculate the position for text at a given angle."""
        text_radius = radius * self.TEXT_RADIUS_RATIO
        text_angle_rad = math.radians(angle)
        
        x = center[0] + int(text_radius * math.cos(text_angle_rad))
        y = center[1] + int(text_radius * math.sin(text_angle_rad))
        
        return (x, y)
    
    def _draw_wheel_segments(
        self, 
        draw: ImageDraw.ImageDraw, 
        center: Position, 
        radius: int, 
        rotation_angle: float = 0
    ) -> None:
        """Draw all segments of the wheel with genres and colors."""
        if not self.genres:
            return
            
        angle_per_segment = 360 / len(self.genres)
        font = self._get_font()
        
        for i, genre in enumerate(self.genres):
            # Calculate segment angles
            start_angle = rotation_angle + i * angle_per_segment
            end_angle = start_angle + angle_per_segment
            
            # Draw the segment
            segment_color = self.WHEEL_COLORS[i % len(self.WHEEL_COLORS)]
            draw.pieslice(
                [(center[0] - radius, center[1] - radius), 
                 (center[0] + radius, center[1] + radius)],
                start_angle, end_angle, 
                fill=segment_color
            )
            
            # Calculate text position
            text_angle = start_angle + angle_per_segment / 2
            text_pos = self._calculate_text_position(center, radius, text_angle)
            
            # Draw the genre name
            draw.text(text_pos, genre, fill=(0, 0, 0), font=font, anchor="mm")
    
    def _draw_wheel_decorations(
        self, 
        draw: ImageDraw.ImageDraw, 
        center: Position, 
        radius: int
    ) -> None:
        """Draw the center circle, border, and pointer."""
        # Draw center circle
        draw.ellipse(
            [(center[0] - self.CENTER_CIRCLE_RADIUS, center[1] - self.CENTER_CIRCLE_RADIUS),
             (center[0] + self.CENTER_CIRCLE_RADIUS, center[1] + self.CENTER_CIRCLE_RADIUS)],
            fill=(100, 100, 100)
        )
        
        # Draw outer border
        draw.ellipse(
            [(center[0] - radius, center[1] - radius), 
             (center[0] + radius, center[1] + radius)],
            outline=(0, 0, 0), width=2
        )
        
        # Draw pointer at the top - flipped so the point touches the wheel
        pointer_tip = (center[0], center[1] - radius + 5)  # Point touches the wheel
        pointer_left = (center[0] - self.POINTER_WIDTH, center[1] - radius - self.POINTER_LENGTH)
        pointer_right = (center[0] + self.POINTER_WIDTH, center[1] - radius - self.POINTER_LENGTH)
        
        draw.polygon(
            [pointer_tip, pointer_left, pointer_right],
            fill=(255, 0, 0), outline=(0, 0, 0), width=2
        )
    
    def create_wheel_image(self, rotation_angle: float = 0) -> Image.Image:
        """
        Create a wheel image at a specific rotation angle.
        
        Args:
            rotation_angle: The rotation angle in degrees
            
        Returns:
            PIL Image of the wheel
        """
        # Create image with white background
        image = Image.new('RGB', (self.IMAGE_SIZE, self.IMAGE_SIZE), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        center, radius = self._get_center_and_radius()
        
        # Draw wheel components
        self._draw_wheel_segments(draw, center, radius, rotation_angle)
        self._draw_wheel_decorations(draw, center, radius)
        
        return image
    
    def _calculate_final_angle(self, selected_genre: str) -> float:
        """Calculate the final angle for the wheel to land on the selected genre."""
        if selected_genre not in self.genres:
            raise ValueError(f"Genre '{selected_genre}' not found in wheel")
            
        selected_index = self.genres.index(selected_genre)
        angle_per_segment = 360 / len(self.genres)
        
        # Calculate where the selected segment should be positioned
        # (under the top pointer at 270 degrees)
        segment_center_angle = selected_index * angle_per_segment + angle_per_segment / 2
        return 270 - segment_center_angle
    
    def _generate_rotation_angles(self, final_angle: float) -> list[float]:
        """Generate a list of rotation angles for smooth animation."""
        angles = []
        
        for i in range(self.ANIMATION_FRAMES):
            # Quadratic ease-out for realistic deceleration
            progress = i / (self.ANIMATION_FRAMES - 1)
            eased_progress = 1 - (1 - progress) ** 2
            
            # Calculate current angle with multiple rotations
            current_angle = (
                self.FULL_ROTATIONS * 360 * eased_progress + 
                final_angle * progress
            )
            
            angles.append(current_angle % 360)
        
        return angles
    
    def create_wheel_gif(self, selected_genre: str) -> io.BytesIO:
        """
        Create a spinning wheel GIF that lands on the selected genre.
        
        Args:
            selected_genre: The genre the wheel should land on
            
        Returns:
            BytesIO object containing the GIF data
            
        Raises:
            ValueError: If the selected genre is not on the wheel
        """
        final_angle = self._calculate_final_angle(selected_genre)
        rotation_angles = self._generate_rotation_angles(final_angle)
        
        # Generate frames
        frames = [
            self.create_wheel_image(angle) 
            for angle in rotation_angles
        ]
        
        # Create GIF in memory
        gif_buffer = io.BytesIO()
        imageio.mimsave(
            gif_buffer, 
            frames, 
            format='GIF', 
            duration=self.GIF_DURATION, 
            loop=0
        )
        
        gif_buffer.seek(0)
        return gif_buffer


class MovieBot(commands.Bot):
    """Custom Discord bot for movie genre wheel functionality."""
    
    def __init__(self) -> None:
        """Initialize the bot with proper intents and settings."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description="A bot that spins a wheel to select random movie genres"
        )
        
        self.wheel = MovieGenreWheel()
        self.manager = MovieManager()
    
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')


# Initialize bot
bot = MovieBot()


@bot.command(name='spin')
async def spin_wheel(ctx: commands.Context) -> None:
    """Spin the wheel and select a random movie genre with GIF animation."""
    try:
        # Send initial message
        initial_msg = await ctx.send("🎡 Spinning the movie genre wheel...")
        
        # Select random genre and create animation
        selected_genre = bot.wheel.spin_wheel()
        gif_data = bot.wheel.create_wheel_gif(selected_genre)
        
        # Send the spinning GIF
        gif_file = discord.File(fp=gif_data, filename='wheel_spinning.gif')
        gif_msg = await ctx.send(file=gif_file)
        
        # Wait for the animation to finish (duration * frames + small buffer)
        animation_duration = bot.wheel.GIF_DURATION * bot.wheel.ANIMATION_FRAMES + 1.0
        await asyncio.sleep(animation_duration)
        
        # Create and send the final static wheel image
        final_angle = bot.wheel._calculate_final_angle(selected_genre)
        final_wheel_image = bot.wheel.create_wheel_image(final_angle)
        
        with io.BytesIO() as image_buffer:
            final_wheel_image.save(image_buffer, 'PNG')
            image_buffer.seek(0)
            
            final_image_file = discord.File(fp=image_buffer, filename='final_wheel.png')
            
            # Delete the GIF and replace with static image
            await gif_msg.delete()
            await ctx.send(file=final_image_file)
        
        # Send the result message
        await initial_msg.edit(
            content=f"🎡 The wheel has stopped! Tonight's movie genre is: **{selected_genre}**"
        )
        
    except ValueError as e:
        await ctx.send(f"❌ Error: {e}")
    except Exception as e:
        await ctx.send("❌ An unexpected error occurred while spinning the wheel.")
        print(f"Error in spin command: {e}")


@bot.command(name='add_genre')
async def add_genre(ctx: commands.Context, *, genre: str) -> None:
    """Add a new genre to the wheel."""
    if not genre.strip():
        await ctx.send("❌ Please provide a genre name.")
        return
    
    if bot.wheel.add_genre(genre):
        await ctx.send(f'✅ Added "{genre}" to the wheel!')
    else:
        await ctx.send(f'❌ "{genre}" is already on the wheel!')


@bot.command(name='remove_genre')
async def remove_genre(ctx: commands.Context, *, genre: str) -> None:
    """Remove a genre from the wheel."""
    if not genre.strip():
        await ctx.send("❌ Please provide a genre name.")
        return
    
    if bot.wheel.remove_genre(genre):
        await ctx.send(f'✅ Removed "{genre}" from the wheel!')
    else:
        await ctx.send(f'❌ "{genre}" was not found on the wheel!')


@bot.command(name='list_genres')
async def list_genres(ctx: commands.Context) -> None:
    """List all genres currently on the wheel with visual representation."""
    genres = bot.wheel.genre_list
    
    if not genres:
        await ctx.send("❌ No genres available on the wheel.")
        return
    
    genres_text = ", ".join(genres)
    
    # Create and send wheel image
    try:
        wheel_image = bot.wheel.create_wheel_image()
        
        with io.BytesIO() as image_buffer:
            wheel_image.save(image_buffer, 'PNG')
            image_buffer.seek(0)
            
            image_file = discord.File(fp=image_buffer, filename='wheel.png')
            await ctx.send(
                f'**Movie Genres on the Wheel ({len(genres)} total)**:\n{genres_text}', 
                file=image_file
            )
    except Exception as e:
        # Fallback to text-only if image generation fails
        await ctx.send(f'**Movie Genres on the Wheel ({len(genres)} total)**:\n{genres_text}')
        print(f"Error generating wheel image: {e}")


@bot.command(name='wheel_image')
async def show_wheel_image(ctx: commands.Context) -> None:
    """Show the current wheel as a static image."""
    try:
        wheel_image = bot.wheel.create_wheel_image()
        
        with io.BytesIO() as image_buffer:
            wheel_image.save(image_buffer, 'PNG')
            image_buffer.seek(0)
            
            image_file = discord.File(fp=image_buffer, filename='current_wheel.png')
            await ctx.send('🎡 Current Movie Genre Wheel:', file=image_file)
            
    except Exception as e:
        await ctx.send("❌ Failed to generate wheel image.")
        print(f"Error in wheel_image command: {e}")


@bot.command(name='wheel_stats')
async def wheel_stats(ctx: commands.Context) -> None:
    """Show statistics about the current wheel."""
    genre_count = bot.wheel.genre_count
    
    if genre_count == 0:
        await ctx.send("📊 The wheel is empty!")
        return
    
    embed = discord.Embed(
        title="🎡 Wheel Statistics",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(name="Total Genres", value=str(genre_count), inline=True)
    embed.add_field(
        name="Probability per Genre", 
        value=f"{100/genre_count:.2f}%", 
        inline=True
    )
    embed.add_field(name="Colors Used", value=str(min(genre_count, len(bot.wheel.WHEEL_COLORS))), inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name='help_wheel')
async def help_wheel(ctx: commands.Context) -> None:
    """Show help information for movie genre wheel commands."""
    embed = discord.Embed(
        title="🎡 Movie Genre Wheel Bot Commands",
        color=discord.Color.green(),
        description="Spin the wheel to discover your next movie genre!"
    )
    
    commands_info = [
        ("!spin", "Spin the wheel with animated GIF"),
        ("!add_genre [name]", "Add a new genre to the wheel"),
        ("!remove_genre [name]", "Remove a genre from the wheel"),
        ("!list_genres", "Show all genres with wheel image"),
        ("!wheel_image", "Display the current wheel"),
        ("!wheel_stats", "Show wheel statistics"),
        ("!help_wheel", "Show this help message")
    ]
    
    for cmd, description in commands_info:
        embed.add_field(name=cmd, value=description, inline=False)
    
    embed.set_footer(text="Made with ❤️ for movie lovers")
    await ctx.send(embed=embed)


@bot.command(name='pick_movie')
async def pick_movie(ctx, *, movie_name):
    """Pick a movie using fuzzy search from IMDB"""
    if not movie_name:
        await ctx.send("Please provide a movie name!")
        return
    
    # Show searching message
    search_msg = await ctx.send(f"🔍 Searching for **{movie_name}**...")
    
    # Search and select movie
    success, message, embed = await movie_manager.pick_movie(movie_name)
    
    if success and embed:
        await search_msg.edit(content=message, embed=embed)
    else:
        await search_msg.edit(content=message)

@bot.command(name='current_movie')
async def current_movie(ctx):
    """Display the currently selected movie with details"""
    current = movie_manager.get_current_movie()
    
    if not current:
        await ctx.send("No movie has been selected yet. Use `!pick_movie [name]` to pick one!")
        return
    
    embed = movie_manager.create_current_movie_embed()
    
    if embed:
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"🎬 Current movie: **{current}**")


def main() -> None:
    """Main function to run the bot."""
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        raise ValueError(
            "DISCORD_TOKEN environment variable is required. "
            "Please set it with your Discord bot token."
        )
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Failed to log in. Please check your DISCORD_TOKEN.")
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == '__main__':
    main()
