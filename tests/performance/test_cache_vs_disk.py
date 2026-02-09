#!/usr/bin/env python3
"""Test cache vs disk reads"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb import Database

db_file = "test_cache.db"
if os.path.exists(db_file):
    os.remove(db_file)

print("=== Test 1: Same session (cache) ===")
with Database(db_file) as db:
    db.insert("key1", "val1")
    try:
        result = db.get("key1")
        print(f"✓ Got key1 from cache: {result}")
    except Exception as e:
        print(f"✗ Failed to get key1: {e}")

print("\n=== Test 2: New session (disk) ===")
with Database(db_file) as db:
    try:
        result = db.get("key1")
        print(f"✓ Got key1 from disk: {result}")
    except Exception as e:
        print(f"✗ Failed to get key1: {e}")

os.remove(db_file)
