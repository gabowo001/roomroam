#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test registration directly"""
import sys
sys.path.insert(0, '.')

from models import get_db_session, User

try:
    print("Creating database session...")
    session = get_db_session()
    print("[OK] Session created")

    print("\nChecking if user exists...")
    existing_user = session.query(User).filter_by(username='testuser2').first()
    if existing_user:
        print("[INFO] User already exists, deleting...")
        session.delete(existing_user)
        session.commit()

    print("\nCreating new user...")
    user = User(username='testuser2')
    print("[OK] User object created")

    print("\nSetting password...")
    user.set_password('password123')
    print("[OK] Password set")

    print("\nAdding to session...")
    session.add(user)
    print("[OK] Added to session")

    print("\nCommitting...")
    session.commit()
    print("[OK] Committed")

    print("\n[SUCCESS] User registered successfully!")
    print(f"User ID: {user.id}")
    print(f"Username: {user.username}")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
