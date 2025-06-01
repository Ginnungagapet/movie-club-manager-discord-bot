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

# Type aliases for better readability
Color = tuple[int, int, int]
Position = tuple[int, int]


class WheelService:
    """A movie genre wheel that creates spinning animations and manages genres."""

    # Class constants
    DEFAULT_GENRES: Final[list[str]] = [
        "Action",
        "Adventure",
        "Animation",
        "Biography",
        "Comedy",
        "Crime",
        "Documentary",
        "Drama",
        "Family",
        "Fantasy",
        "Film-Noir",
        "History",
        "Horror",
        "Music",
        "Musical",
        "Mystery",
        "Romance",
        "Sci-Fi",
        "Sport",
        "Thriller",
        "War",
        "Western",
    ]

    WHEEL_COLORS: Final[list[Color]] = [
        (255, 0, 0),
        (255, 127, 0),
        (255, 255, 0),
        (127, 255, 0),
        (0, 255, 0),
        (0, 255, 127),
        (0, 255, 255),
        (0, 127, 255),
        (0, 0, 255),
        (127, 0, 255),
        (255, 0, 255),
        (255, 0, 127),
        (192, 192, 192),
        (128, 128, 128),
        (128, 0, 0),
        (128, 128, 0),
        (0, 128, 0),
        (0, 128, 128),
        (0, 0, 128),
        (128, 0, 128),
        (170, 110, 40),
        (128, 128, 64),
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
        self, center: Position, radius: int, angle: float
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
        rotation_angle: float = 0,
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
                [
                    (center[0] - radius, center[1] - radius),
                    (center[0] + radius, center[1] + radius),
                ],
                start_angle,
                end_angle,
                fill=segment_color,
            )

            # Calculate text position
            text_angle = start_angle + angle_per_segment / 2
            text_pos = self._calculate_text_position(center, radius, text_angle)

            # Draw the genre name
            draw.text(text_pos, genre, fill=(0, 0, 0), font=font, anchor="mm")

    def _draw_wheel_decorations(
        self, draw: ImageDraw.ImageDraw, center: Position, radius: int
    ) -> None:
        """Draw the center circle, border, and pointer."""
        # Draw center circle
        draw.ellipse(
            [
                (
                    center[0] - self.CENTER_CIRCLE_RADIUS,
                    center[1] - self.CENTER_CIRCLE_RADIUS,
                ),
                (
                    center[0] + self.CENTER_CIRCLE_RADIUS,
                    center[1] + self.CENTER_CIRCLE_RADIUS,
                ),
            ],
            fill=(100, 100, 100),
        )

        # Draw outer border
        draw.ellipse(
            [
                (center[0] - radius, center[1] - radius),
                (center[0] + radius, center[1] + radius),
            ],
            outline=(0, 0, 0),
            width=2,
        )

        # Draw pointer at the top - flipped so the point touches the wheel
        pointer_tip = (center[0], center[1] - radius + 5)  # Point touches the wheel
        pointer_left = (
            center[0] - self.POINTER_WIDTH,
            center[1] - radius - self.POINTER_LENGTH,
        )
        pointer_right = (
            center[0] + self.POINTER_WIDTH,
            center[1] - radius - self.POINTER_LENGTH,
        )

        draw.polygon(
            [pointer_tip, pointer_left, pointer_right],
            fill=(255, 0, 0),
            outline=(0, 0, 0),
            width=2,
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
        image = Image.new("RGB", (self.IMAGE_SIZE, self.IMAGE_SIZE), (255, 255, 255))
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
        segment_center_angle = (
            selected_index * angle_per_segment + angle_per_segment / 2
        )
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
                self.FULL_ROTATIONS * 360 * eased_progress + final_angle * progress
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
        frames = [self.create_wheel_image(angle) for angle in rotation_angles]

        # Create GIF in memory
        gif_buffer = io.BytesIO()
        imageio.mimsave(
            gif_buffer, frames, format="GIF", duration=self.GIF_DURATION, loop=0
        )

        gif_buffer.seek(0)
        return gif_buffer
