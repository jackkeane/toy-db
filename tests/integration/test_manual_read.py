#!/usr/bin/env python3
"""Manual read test - bypass the get() method"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb._storage_engine import StorageEngine

db_file = "test_manual.db"
if os.path.exists(db_file):
    os.remove(db_file)

# Write data
engine = StorageEngine(db_file)
engine.insert("abc", "123")
engine.insert("def", "456")
engine.flush()

print("=== Written data ===")
with open(db_file, 'rb') as f:
    data = f.read()
    # Skip header (16 bytes) and read data section
    header_size = 16
    data_section = data[header_size:header_size+100]
    print(f"Data section: {data_section.decode('ascii', errors='ignore')}")
    print(f"Data section (hex): {data_section[:50].hex()}")

# Try to read back
print("\n=== Reading back ===")
try:
    result = engine.get("abc")
    print(f"Successfully got 'abc': {result}")
except Exception as e:
    print(f"Failed to get 'abc': {e}")

os.remove(db_file)
