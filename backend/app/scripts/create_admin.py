"""Create admin user script."""

from __future__ import annotations

import asyncio
import os
import sys
from getpass import getpass

from sqlalchemy import select

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.security import get_password_hash
from app.db.models.user import User
from app.db.session import SessionLocal


async def create_admin() -> None:
    """Create admin user interactively."""
    print("🔐 Legalia Admin User Creation")
    print("=" * 50)

    # Get user input
    email = input("Admin email: ").strip()
    if not email:
        print("❌ Email is required")
        return

    full_name = input("Full name: ").strip()
    if not full_name:
        print("❌ Full name is required")
        return

    password = getpass("Password: ")
    if not password or len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return

    password_confirm = getpass("Confirm password: ")
    if password != password_confirm:
        print("❌ Passwords don't match")
        return

    # Create admin user
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            print(f"❌ User with email {email} already exists")
            return

        # Create user
        admin = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("")
        print("✅ Admin user created successfully!")
        print(f"   Email: {admin.email}")
        print(f"   Name: {admin.full_name}")
        print(f"   ID: {admin.id}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_admin())
