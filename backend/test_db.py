#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test database connection"""
from models import get_db_session, init_db, User

try:
    print("Testing database connection...")
    session = get_db_session()
    print("[OK] Database session created")

    print("\nInitializing database tables...")
    init_db()
    print("[OK] Tables created/verified")

    print("\nQuerying users...")
    users = session.query(User).all()
    print(f"[OK] Found {len(users)} users")

    print("\nTrying to create a test user...")
    test_user = User(username="test123")
    test_user.set_password("password123")
    session.add(test_user)
    session.commit()
    print("[OK] Test user created successfully")

    print("\n[OK] All database tests passed!")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
