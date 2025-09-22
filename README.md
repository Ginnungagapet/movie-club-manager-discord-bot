# Movie Club Manager Discord Bot

A comprehensive Discord bot for managing movie club activities with biweekly rotation, movie selection, and rating system. Features IMDB integration, PostgreSQL database, and a complete rotation management system.

## Features

### 🎯 Rotation Management
- **Biweekly rotation** system with automatic scheduling
- **Early access window** - next picker gets access 1 week before their period
- **Automatic advancement** based on time elapsed since start date
- **Historical tracking** of all movie picks with dates and periods

### 🎬 Movie Selection
- **IMDB integration** with fuzzy search and year matching
- **Rich movie information** - plot, cast, directors, ratings, posters
- **Permission-based picking** - only current/next picker can select movies
- **Clickable IMDB links** in all movie displays

### ⭐ Rating System
- **1-10 rating scale** with optional text reviews
- **Average ratings** calculated and displayed for all movies
- **Personal rating history** tracking for each user
- **Top-rated movies** leaderboard

### 📊 Database Backend
- **PostgreSQL** for persistent data storage
- **Automatic table creation** and database initialization
- **Survives deployments** - no data loss on Heroku restarts

## Commands

### Rotation Commands
- `!schedule [periods]` - Show upcoming rotation schedule (default: 5 periods)
- `!who_picks` - Show current and next picker with early access status
- `!my_turn` - Check if it's your turn to pick a movie
- `!history [limit]` - Show recent movie picks with ratings (default: 10)
- `!my_picks` - Show your personal movie pick history

### Movie Commands
- `!pick_movie <title> [year]` - Pick a movie (only during your turn)
  - Examples: `!pick_movie The Matrix`, `!pick_movie The Matrix 1999`
- `!search_movie <title> [year]` - Search for a movie without picking it
- `!current_movie` - Display currently selected movie with full details
- `!clear_movie` - Clear current movie selection
- `!movie_status` - Quick status of current movie

### Rating Commands
- `!rate <movie_id> <rating> [review]` - Rate a movie (1-10)
  - Examples: `!rate 5 8`, `!rate 5 9 Amazing cinematography!`
- `!movie_ratings <movie_id>` - Show all ratings for a specific movie
- `!my_ratings` - Show your rating history
- `!top_rated [limit]` - Show top-rated movies (default: 10)
- `!recent_ratings [limit]` - Show most recent ratings from all users
- `!update_rating <movie_id> <new_rating> [new_review]` - Update your existing rating

### Admin Commands (Requires Administrator Permission)
- `!setup_rotation <user_list>` - Set up the rotation order
  - Format: `user1:RealName1,user2:RealName2,user3:RealName3`
  - Example: `!setup_rotation paul:Paul,derek:Derek,greg:Greg`
- `!skip_pick` - Manually advance to next person in rotation
- `!add_historical_pick <username> "<title>" [year] ["date"]` - Add historical movie pick
- `!admin_stats` - Show administrative statistics

## Setup Instructions

### Prerequisites
- Python 3.8+
- Heroku account
- Discord application and bot token

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ginnungagapet/movie-club-manager-discord-bot.git
   cd movie-club-manager-discord-bot
   git checkout Add-DB-And-Reorg
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

5. **Set up local PostgreSQL**
   ```bash
   # Install PostgreSQL locally
   # Create database: createdb movieclub
   # Set DATABASE_URL in .env
   ```

6. **Initialize database**
   ```bash
   python migrations/initial_setup.py setup
   ```

7. **Run the bot**
   ```bash
   python main.py
   ```


## PostgreSQL Database Schema

### Tables Created Automatically:
- **users** - Discord usernames, real names, rotation positions
- **movie_picks** - Movie selections with IMDB data and period info
- **movie_ratings** - User ratings and reviews for movies
- **rotation_state** - Current rotation state and timing

### Key Features:
- **Automatic table creation** on first run
- **Foreign key relationships** between users, picks, and ratings
- **JSON storage** for flexible IMDB metadata
- **Unique constraints** to prevent duplicate ratings
- **Calculated properties** for average ratings

## Configuration

### Environment Variables (.env file):
```bash
# Required
DISCORD_TOKEN=your_discord_bot_token_here
DATABASE_URL=postgresql://username:password@localhost:5432/movieclub

# Optional
COMMAND_PREFIX=!
ROTATION_PERIOD_DAYS=14
EARLY_ACCESS_DAYS=7
MIN_RATING=1
MAX_RATING=10
LOG_LEVEL=INFO
DEBUG=False
```

## Movie Club Setup Example

1. **Set up rotation** (Admin only):
   ```
   !setup_rotation paul:Paul,derek:Derek,greg:Greg,gavin:Gavin,baldo:Baldo,j:J,kyle:Kyle,dennis:Dennis
   ```

2. **Add historical picks** (Admin only):
   ```
   !add_historical_pick paul "Event Horizon" 1997 "May 12, 2025"
   !add_historical_pick derek "Sunshine" 2007 "May 26, 2025"
   ```

3. **Users check their turn**:
   ```
   !my_turn
   !schedule
   ```

4. **Pick movies** (when it's your turn):
   ```
   !pick_movie Dune 2021
   ```

5. **Rate movies**:
   ```
   !rate 1 8 Incredible visuals and sound design!
   ```

## Dependencies

- **discord.py** - Discord API wrapper
- **SQLAlchemy** - Database ORM
- **psycopg2-binary** - PostgreSQL adapter
- **cinemagoer** - IMDB integration
- **python-dotenv** - Environment variable management
- **Pillow, imageio, numpy** - Image processing for wheel features

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Heroku logs for error details
3. Open an issue on GitHub with relevant log output

---