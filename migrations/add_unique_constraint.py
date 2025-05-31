"""
Database migration to add unique constraint for movie picks per period
Run this script to update your existing database
"""

import asyncio
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def migrate_database():
    """Add unique constraint to movie_picks table"""

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
            # First, check if the constraint already exists
            check_constraint_sql = text(
                """
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'movie_picks' 
                AND constraint_type = 'UNIQUE' 
                AND constraint_name = 'unique_user_period_pick'
            """
            )

            result = conn.execute(check_constraint_sql)
            if result.fetchone():
                logger.info(
                    "Constraint 'unique_user_period_pick' already exists, skipping migration"
                )
                return

            # Check for duplicate picks that would violate the constraint
            check_duplicates_sql = text(
                """
                SELECT picker_user_id, period_start_date, period_end_date, COUNT(*) as count
                FROM movie_picks
                WHERE period_start_date IS NOT NULL AND period_end_date IS NOT NULL
                GROUP BY picker_user_id, period_start_date, period_end_date
                HAVING COUNT(*) > 1
            """
            )

            duplicates = conn.execute(check_duplicates_sql).fetchall()

            if duplicates:
                logger.warning("Found duplicate picks that need to be resolved:")
                for dup in duplicates:
                    logger.warning(
                        f"User ID {dup[0]} has {dup[3]} picks for period {dup[1]} - {dup[2]}"
                    )

                # Keep only the most recent pick for each duplicate
                cleanup_sql = text(
                    """
                    DELETE FROM movie_picks p1
                    WHERE EXISTS (
                        SELECT 1 FROM movie_picks p2
                        WHERE p1.picker_user_id = p2.picker_user_id
                        AND p1.period_start_date = p2.period_start_date
                        AND p1.period_end_date = p2.period_end_date
                        AND p1.pick_date < p2.pick_date
                        AND p1.id != p2.id
                    )
                """
                )

                result = conn.execute(cleanup_sql)
                conn.commit()
                logger.info(
                    f"Removed {result.rowcount} duplicate picks (kept most recent)"
                )

            # Add the unique constraint
            add_constraint_sql = text(
                """
                ALTER TABLE movie_picks
                ADD CONSTRAINT unique_user_period_pick 
                UNIQUE (picker_user_id, period_start_date, period_end_date)
            """
            )

            conn.execute(add_constraint_sql)
            conn.commit()

            logger.info(
                "Successfully added unique constraint 'unique_user_period_pick'"
            )

            # Also update the MoviePick model to include this constraint
            logger.info(
                "Don't forget to update models/database.py to include the constraint in the table definition!"
            )

    except ProgrammingError as e:
        if "already exists" in str(e):
            logger.info("Constraint already exists")
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
