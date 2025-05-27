"""
Database models and manager for the Movie Club Bot
"""

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
    Float,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class User(Base):
    """Represents a movie club member"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    discord_username = Column(String(50), unique=True, nullable=False)
    real_name = Column(String(100), nullable=False)
    rotation_position = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    movie_picks = relationship("MoviePick", back_populates="picker")
    ratings_given = relationship("MovieRating", back_populates="rater")

    def __repr__(self):
        return (
            f"<User(username='{self.discord_username}', real_name='{self.real_name}')>"
        )


class MoviePick(Base):
    """Represents a movie selection by a user during their rotation period"""

    __tablename__ = "movie_picks"

    id = Column(Integer, primary_key=True)
    picker_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_title = Column(String(200), nullable=False)
    movie_year = Column(Integer)
    imdb_id = Column(String(20))
    pick_date = Column(DateTime, default=func.now())
    period_start_date = Column(Date)
    period_end_date = Column(Date)
    movie_details = Column(JSON)

    # Relationships
    picker = relationship("User", back_populates="movie_picks")
    ratings = relationship(
        "MovieRating", back_populates="movie_pick", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MoviePick(title='{self.movie_title}', year={self.movie_year}, picker='{self.picker.real_name if self.picker else 'Unknown'}')>"

    @property
    def average_rating(self):
        """Calculate average rating for this movie"""
        if not self.ratings:
            return None
        return sum(rating.rating for rating in self.ratings) / len(self.ratings)

    @property
    def rating_count(self):
        """Get number of ratings for this movie"""
        return len(self.ratings)


class MovieRating(Base):
    """Represents a user's rating of a picked movie"""

    __tablename__ = "movie_ratings"

    id = Column(Integer, primary_key=True)
    movie_pick_id = Column(Integer, ForeignKey("movie_picks.id"), nullable=False)
    rater_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Float, nullable=False)
    review_text = Column(Text)
    rated_at = Column(DateTime, default=func.now())

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "movie_pick_id", "rater_user_id", name="unique_user_movie_rating"
        ),
        CheckConstraint("rating >= 1.0 AND rating <= 10.0", name="rating_range_check"),
    )

    # Relationships
    movie_pick = relationship("MoviePick", back_populates="ratings")
    rater = relationship("User", back_populates="ratings_given")

    def __repr__(self):
        return f"<MovieRating(movie='{self.movie_pick.movie_title if self.movie_pick else 'Unknown'}', rating={self.rating}, rater='{self.rater.real_name if self.rater else 'Unknown'}')>"


class RotationState(Base):
    """Stores the current state of the movie club rotation"""

    __tablename__ = "rotation_state"

    id = Column(Integer, primary_key=True, default=1)
    current_user_id = Column(Integer, ForeignKey("users.id"))
    rotation_start_date = Column(DateTime)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship
    current_user = relationship("User")

    # Constraint to ensure only one row
    __table_args__ = (CheckConstraint("id = 1", name="singleton_rotation_state"),)

    def __repr__(self):
        return f"<RotationState(current_user='{self.current_user.real_name if self.current_user else 'None'}', start_date='{self.rotation_start_date}')>"


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, database_url: str):
        """Initialize database connection"""
        # Handle Heroku postgres:// URLs
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        logger.info("Database connection initialized")

    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created/verified")

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    def init_rotation_state(self):
        """Initialize rotation state if it doesn't exist"""
        session = self.get_session()
        try:
            rotation_state = session.query(RotationState).first()
            if rotation_state is None:
                rotation_state = RotationState(id=1, rotation_start_date=datetime.now())
                session.add(rotation_state)
                session.commit()
                logger.info("Initialized rotation state")
        except Exception as e:
            session.rollback()
            logger.error(f"Error initializing rotation state: {e}")
            raise
        finally:
            session.close()
