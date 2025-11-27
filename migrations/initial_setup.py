"""
Initial database setup and migration script
"""

import os
import sys
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager, Base


def run_initial_setup():
    """Run initial database setup"""
    print("Starting initial database setup...")

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False

    try:
        # Initialize database manager
        db_manager = DatabaseManager(database_url)

        # Create all tables
        print("Creating database tables...")
        db_manager.create_tables()

        # Initialize rotation state
        print("Initializing rotation state...")
        db_manager.init_rotation_state()

        print("✅ Initial database setup completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error during database setup: {e}")
        return False


def verify_setup():
    """Verify database setup is working correctly"""
    print("Verifying database setup...")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False

    try:
        db_manager = DatabaseManager(database_url)
        session = db_manager.get_session()

        # Test database connection
        from models.database import User, MoviePick, MovieRating, RotationState

        # Check if tables exist by querying them
        user_count = session.query(User).count()
        pick_count = session.query(MoviePick).count()
        rating_count = session.query(MovieRating).count()
        rotation_state = session.query(RotationState).first()

        print(f"✅ Database verification completed:")
        print(f"   - Users: {user_count}")
        print(f"   - Movie picks: {pick_count}")
        print(f"   - Ratings: {rating_count}")
        print(
            f"   - Rotation state: {'Initialized' if rotation_state else 'Not found'}"
        )

        session.close()
        return True

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False


def reset_database():
    """Reset database (DROP ALL TABLES - USE WITH CAUTION)"""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    confirm = input("Type 'CONFIRM RESET' to proceed: ")

    if confirm != "CONFIRM RESET":
        print("Reset cancelled.")
        return False

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False

    try:
        db_manager = DatabaseManager(database_url)

        print("Dropping all tables...")
        Base.metadata.drop_all(bind=db_manager.engine)

        print("Recreating tables...")
        Base.metadata.create_all(bind=db_manager.engine)

        print("Reinitializing rotation state...")
        db_manager.init_rotation_state()

        print("✅ Database reset completed!")
        return True

    except Exception as e:
        print(f"❌ Error during reset: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database setup and migration tools")
    parser.add_argument(
        "action", choices=["setup", "verify", "reset"], help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "setup":
        success = run_initial_setup()
    elif args.action == "verify":
        success = verify_setup()
    elif args.action == "reset":
        success = reset_database()

    sys.exit(0 if success else 1)
