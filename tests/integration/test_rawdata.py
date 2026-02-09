#!/usr/bin/env python3
"""Raw data inspection"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb._storage_engine import StorageEngine

db_file = "test_raw.db"
if os.path.exists(db_file):
    os.remove(db_file)

engine = StorageEngine(db_file)
engine.insert("key1", "value1")
engine.flush()

# Read the raw file
with open(db_file, 'rb') as f:
    data = f.read()
    print(f"File size: {len(data)} bytes")
    print(f"First 200 bytes (hex): {data[:200].hex()}")
    print(f"First 200 bytes (ascii, ignoring errors): {data[:200].decode('ascii', errors='ignore')}")

os.remove(db_file)
