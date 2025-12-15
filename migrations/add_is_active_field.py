"""
Migration: Add is_active field to users table
Run this once to update existing database
"""

import os
from sqlalchemy import create_engine, text


def migrate():
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return

    # Handle Heroku postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_active'
        """))

        if result.fetchone():
            print("✓ is_active column already exists")
            return

        # Add the column with default value
        print("Adding is_active column to users table...")
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE
        """))
        conn.commit()

        print("✓ Successfully added is_active column")
        print("✓ All existing users set to active (is_active=true)")


if __name__ == "__main__":
    migrate()
