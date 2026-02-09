#!/usr/bin/env python3
"""Debug JOIN test failure"""

import os
import sys

# Add project to path
sys.path.insert(0, "/home/zz79jk/clawd/toy-db")

from toydb import SQLDatabase

db_file = "debug_join.db"
wal_file = db_file + ".wal"

# Clean up
for f in [db_file, wal_file]:
    if os.path.exists(f):
        os.remove(f)

print("Creating database...")
db = SQLDatabase(db_file)
with db:
    print("\n1. Creating users table...")
    db.execute("CREATE TABLE users (id INT, name TEXT)")
    
    print("2. Listing tables after CREATE users:")
    tables = db.list_tables()
    print(f"   Tables: {tables}")
    
    print("\n3. Creating orders table...")
    db.execute("CREATE TABLE orders (id INT, user_id INT, product TEXT)")
    
    print("4. Listing tables after CREATE orders:")
    tables = db.list_tables()
    print(f"   Tables: {tables}")
    
    print("\n5. Checking if 'users' table exists...")
    exists = db.executor.catalog.table_exists("users")
    print(f"   users exists: {exists}")
    
    print("\n6. Trying to get 'users' columns...")
    try:
        cols = db.executor.catalog.get_columns("users")
        print(f"   users columns: {[f'{c.name}:{c.type}' for c in cols]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n7. Inserting data...")
    db.execute("INSERT INTO users VALUES (1, 'Alice')")
    db.execute("INSERT INTO users VALUES (2, 'Bob')")
    
    print("\n8. Trying simple SELECT on users...")
    try:
        result = db.execute("SELECT * FROM users")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n9. Trying SELECT with JOIN...")
    try:
        result = db.execute("""
            SELECT name, product 
            FROM users 
            INNER JOIN orders ON id = user_id
        """)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\nDone!")

# Cleanup
for f in [db_file, wal_file]:
    if os.path.exists(f):
        os.remove(f)
