"""
Database migration to add skip functionality
Save this as: migrations/add_skip_functionality.py
"""

import asyncio
import logging
from sqlalchemy import (
    create_engine,
    text,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

Base = declarative_base()


class RotationSkip(Base):
    """Tracks skipped periods in the rotation"""

    __tablename__ = "rotation_skips"

    id = Column(Integer, primary_key=True)
    skipped_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_start_date = Column(Date, nullable=False)
    original_end_date = Column(Date, nullable=False)
    skip_reason = Column(String(200))
    skipped_at = Column(DateTime, default=func.now())
    skipped_by = Column(String(50))  # Discord username who initiated the skip


async def migrate_database():
    """Add rotation_skips table to the database"""

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Handle Heroku postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # First, check if the table already exists
            check_table_sql = text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'rotation_skips'
            """
            )

            result = conn.execute(check_table_sql)
            if result.fetchone():
                logger.info("Table 'rotation_skips' already exists, skipping migration")
                return

            # Create the rotation_skips table
            create_table_sql = text(
                """
                CREATE TABLE rotation_skips (
                    id SERIAL PRIMARY KEY,
                    skipped_user_id INTEGER NOT NULL REFERENCES users(id),
                    original_start_date DATE NOT NULL,
                    original_end_date DATE NOT NULL,
                    skip_reason VARCHAR(200),
                    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    skipped_by VARCHAR(50),
                    CONSTRAINT unique_user_period_skip
                        UNIQUE (skipped_user_id, original_start_date, original_end_date)
                )
            """
            )

            conn.execute(create_table_sql)
            conn.commit()

            logger.info("Successfully created 'rotation_skips' table")

            # Create index for better query performance
            create_index_sql = text(
                """
                CREATE INDEX idx_rotation_skips_dates
                ON rotation_skips(original_start_date, original_end_date)
            """
            )

            conn.execute(create_index_sql)
            conn.commit()

            logger.info("Created index on rotation_skips dates")

    except ProgrammingError as e:
        if "already exists" in str(e):
            logger.info("Table already exists")
        else:
            logger.error(f"Migration failed: {e}")
            raise
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        engine.dispose()


def main():
    """Run the migration"""
    asyncio.run(migrate_database())


if __name__ == "__main__":
    main()
