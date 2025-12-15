"""
One-time fix: Set is_active=False for users with rotation_position=NULL
This fixes users removed before the is_active field was added
"""

import os
from sqlalchemy import create_engine, text


def fix_inactive_users():
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Find users with NULL rotation_position but is_active=True
        result = conn.execute(text("""
            SELECT discord_username, real_name 
            FROM users 
            WHERE rotation_position IS NULL AND is_active = TRUE
        """))

        users_to_fix = result.fetchall()

        if not users_to_fix:
            print("✓ No users need fixing - all data is consistent")
            return

        print(f"Found {len(users_to_fix)} users to fix:")
        for username, real_name in users_to_fix:
            print(f"  - {real_name} (@{username})")

        # Fix them
        print("\nSetting is_active=FALSE for these users...")
        conn.execute(text("""
            UPDATE users 
            SET is_active = FALSE 
            WHERE rotation_position IS NULL AND is_active = TRUE
        """))
        conn.commit()

        print(f"✓ Fixed {len(users_to_fix)} users")
        print("✓ Removed users are now properly marked as inactive")


if __name__ == "__main__":
    fix_inactive_users()
