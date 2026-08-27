#!/usr/bin/env python3
"""Create an admin user for Legalia.

Usage:
    python scripts/create_admin.py

Or inside Docker:
    docker compose exec legalia-api python scripts/create_admin.py
"""

import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.db.models.user import User
from app.services.auth_service import AuthService


def main():
    """Create admin user interactively."""
    print("=" * 60)
    print("Legalia - Create Admin User")
    print("=" * 60)
    print()

    # Get credentials
    email = input("Admin email: ").strip()
    if not email or "@" not in email:
        print("❌ Invalid email")
        sys.exit(1)

    password = getpass("Admin password (min 8 chars): ").strip()
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)

    password_confirm = getpass("Confirm password: ").strip()
    if password != password_confirm:
        print("❌ Passwords don't match")
        sys.exit(1)

    full_name = input("Full name (optional): ").strip() or None

    # Create user
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing_user:
            print(f"\n❌ User with email '{email}' already exists")
            sys.exit(1)

        # Create admin user
        auth_service = AuthService(db)
        user = auth_service.create_user(
            email=email,
            password=password,
            full_name=full_name,
            is_superuser=True,
        )

        print()
        print("✅ Admin user created successfully!")
        print()
        print(f"  Email:      {user.email}")
        print(f"  ID:         {user.id}")
        print(f"  Full name:  {user.full_name or '(none)'}")
        print(f"  Superuser:  {user.is_superuser}")
        print()
        print("You can now login at: /login")
        print()

    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
