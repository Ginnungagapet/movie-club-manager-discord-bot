# Discord Movie Genre Wheel Bot

A Discord bot that spins a wheel to randomly select movie genres with animated GIF visualization.

## Features

- **Animated Wheel Spinning**: Creates a GIF showing the wheel spinning and landing on a genre
- **True Random Selection**: Uses cryptographically secure randomness
- **Customizable Genres**: Add or remove genres from the wheel
- **Visual Feedback**: Shows the wheel with colorful segments for each genre

## Commands

- `!spin` - Spin the wheel and get a random movie genre with animation
- `!add_genre [name]` - Add a new genre to the wheel
- `!remove_genre [name]` - Remove a genre from the wheel
- `!list_genres` - See all genres currently on the wheel
- `!wheel_image` - Show the current wheel as an image
- `!help_wheel` - Show available commands

## Setup

1. Create a Discord application and bot at the [Discord Developer Portal](https://discord.com/developers/applications)
2. Set the `DISCORD_TOKEN` environment variable to your bot's token
3. Invite the bot to your server with the necessary permissions
4. Deploy to your hosting platform

## Default Genres

The bot comes with 22 default movie genres:
Action, Adventure, Animation, Biography, Comedy, Crime, Documentary, Drama, Family, Fantasy, Film-Noir, History, Horror, Music, Musical, Mystery, Romance, Sci-Fi, Sport, Thriller, War, Western

## Requirements

- Python 3.8+
- discord.py
- Pillow (PIL)
- imageio
- numpy

## Hosting

This bot is designed to be deployed on platforms like Heroku, Railway, or similar cloud hosting services.
