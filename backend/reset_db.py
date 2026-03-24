#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reset database - drop all tables and recreate them"""
from models import Base, get_db_session
from sqlalchemy import create_engine
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')

print("Connecting to database...")
engine = create_engine(DATABASE_URL)

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("[OK] All tables dropped")

print("\nCreating all tables...")
Base.metadata.create_all(bind=engine)
print("[OK] All tables created")

print("\n[OK] Database reset complete!")
print("\nNew tables created:")
for table in Base.metadata.tables.keys():
    print(f"  - {table}")
