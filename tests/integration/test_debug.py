#!/usr/bin/env python3
"""Debug test"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb._storage_engine import StorageEngine

db_file = "test_debug.db"
if os.path.exists(db_file):
    os.remove(db_file)

engine = StorageEngine(db_file)

# Insert
print("Inserting...")
engine.insert("user:1", "Alice")
print("Inserted user:1=Alice")

# Flush
engine.flush()
print("Flushed to disk")

# Try to get
print("Getting user:1...")
try:
    result = engine.get("user:1")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")

os.remove(db_file)
