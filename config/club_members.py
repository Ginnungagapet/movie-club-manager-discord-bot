"""
Movie Club Member Configuration

This file contains the Discord usernames and real names for your movie club.
Update the CLUB_MEMBERS list with the actual Discord usernames from your server.

To find Discord usernames:
1. In Discord, right-click on a user
2. Copy their username (the new format without #numbers)
3. Update the list below

Current rotation order based on your schedule:
Paul - May 5-18
Derek - May 19 - June 1
Greg - June 2-15
Gavin - June 16-29
Baldo - June 30 - July 13
J - July 14-27
Kyle - July 28 - Aug 10
Dennis - Aug 11-24
"""

# UPDATE THESE WITH ACTUAL DISCORD USERNAMES
CLUB_MEMBERS = [
    # Format: (discord_username, real_name)
    ("bzerkap", "Paul"),  # Replace with Paul's actual Discord username
    ("dham0577", "Derek"),  # Replace with Derek's actual Discord username
    ("thegredge", "Greg"),  # Replace with Greg's actual Discord username
    ("gavocado", "Gavin"),  # Replace with Gavin's actual Discord username
    ("bgarz13", "Baldo"),  # Replace with Baldo's actual Discord username
    ("jaustin429", "J"),  # Replace with J's actual Discord username
    ("kile", "Kyle"),  # Replace with Kyle's actual Discord username
    ("bodown3d", "Dennis"),  # Replace with Dennis's actual Discord username
]


def get_setup_command():
    """Generate the setup command string for easy copying"""
    user_pairs = [f"{username}:{real_name}" for username, real_name in CLUB_MEMBERS]
    return f"!setup_rotation {','.join(user_pairs)}"


def get_backfill_commands():
    """Generate historical backfill commands"""
    return [
        '!add_historical_pick bzerkap "Event Horizon" 1997 "May 12, 2025"',
        '!add_historical_pick dham0577 "Sunshine" 2007 "May 26, 2025"',
    ]


def validate_usernames():
    """Check if usernames have been updated from defaults"""
    default_patterns = ["_username_here", "username_here"]
    for username, real_name in CLUB_MEMBERS:
        for pattern in default_patterns:
            if pattern in username:
                return (
                    False,
                    f"Please update {real_name}'s Discord username (currently: {username})",
                )
    return True, "All usernames configured"


if __name__ == "__main__":
    print("Movie Club Setup Commands:")
    print("=" * 50)

    # Check if usernames are configured
    is_valid, message = validate_usernames()
    if not is_valid:
        print(f"⚠️  {message}")
        print(
            "\nPlease update the CLUB_MEMBERS list with actual Discord usernames first!"
        )
    else:
        print("✅ All usernames configured")

        print("\n1. Setup Rotation Command:")
        print(get_setup_command())

        print("\n2. Backfill Historical Picks:")
        for command in get_backfill_commands():
            print(command)

        print("\n3. Verify Setup:")
        print("!schedule")
        print("!history")
