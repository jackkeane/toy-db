#!/usr/bin/env python3
"""
Phase 5 Test - Persistent Schema Catalog
Tests catalog operations, ALTER TABLE, and CREATE INDEX
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb import SQLDatabase


def test_catalog_operations():
    """Test catalog list operations"""
    db_file = "test_catalog.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Phase 5 Test: Catalog Operations ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create multiple tables
        db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
        db.execute("CREATE TABLE products (id INT, name TEXT, price INT)")
        db.execute("CREATE TABLE orders (id INT, user_id INT, product_id INT)")
        
        print("✓ Created 3 tables")
        
        # List tables
        tables = db.list_tables()
        assert len(tables) == 3
        assert "users" in tables
        assert "products" in tables
        assert "orders" in tables
        print(f"✓ Listed {len(tables)} tables: {tables}")
        
        # Describe table
        columns = db.describe_table("users")
        assert len(columns) == 3
        assert columns[0].name == "id"
        assert columns[0].type == "INT"
        assert columns[1].name == "name"
        assert columns[1].type == "TEXT"
        print(f"✓ Described 'users' table: {len(columns)} columns")
    
    # Test persistence
    with SQLDatabase(db_file) as db:
        tables = db.list_tables()
        assert len(tables) == 3
        print("✓ Catalog persisted correctly")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Catalog Operations Test: PASSED\n")


def test_alter_table():
    """Test ALTER TABLE ADD COLUMN"""
    db_file = "test_alter.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== ALTER TABLE Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table
        db.execute("CREATE TABLE employees (id INT, name TEXT)")
        print("✓ Created table with 2 columns")
        
        # Insert data
        db.execute("INSERT INTO employees VALUES (1, 'Alice')")
        print("✓ Inserted row")
        
        # Add column
        db.execute("ALTER TABLE employees ADD COLUMN salary INT")
        print("✓ Added 'salary' column")
        
        # Verify schema
        columns = db.describe_table("employees")
        assert len(columns) == 3
        assert columns[2].name == "salary"
        assert columns[2].type == "INT"
        print("✓ Schema updated correctly")
        
        # Insert new row with all columns
        db.execute("INSERT INTO employees VALUES (2, 'Bob', 75000)")
        print("✓ Inserted row with new column")
        
        # Query
        results = db.execute("SELECT * FROM employees")
        assert len(results) == 2
        print(f"✓ Query returned {len(results)} rows")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 ALTER TABLE Test: PASSED\n")


def test_create_index():
    """Test CREATE INDEX and DROP INDEX"""
    db_file = "test_index.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== CREATE INDEX Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table
        db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
        print("✓ Created table")
        
        # Create indexes
        db.execute("CREATE INDEX idx_age ON users (age)")
        db.execute("CREATE INDEX idx_name ON users (name)")
        print("✓ Created 2 indexes")
        
        # List indexes
        indexes = db.list_indexes()
        assert len(indexes) == 2
        print(f"✓ Listed {len(indexes)} indexes")
        
        # List indexes for specific table
        user_indexes = db.list_indexes("users")
        assert len(user_indexes) == 2
        assert any(idx["name"] == "idx_age" for idx in user_indexes)
        assert any(idx["name"] == "idx_name" for idx in user_indexes)
        print("✓ Indexes associated with table")
        
        # Drop index
        db.execute("DROP INDEX idx_name")
        print("✓ Dropped index")
        
        # Verify
        indexes = db.list_indexes()
        assert len(indexes) == 1
        assert indexes[0]["name"] == "idx_age"
        print("✓ Index removed from catalog")
    
    # Test persistence
    with SQLDatabase(db_file) as db:
        indexes = db.list_indexes()
        assert len(indexes) == 1
        print("✓ Index metadata persisted")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 CREATE INDEX Test: PASSED\n")


def test_drop_table():
    """Test DROP TABLE"""
    db_file = "test_drop.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== DROP TABLE Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create tables
        db.execute("CREATE TABLE users (id INT, name TEXT)")
        db.execute("CREATE TABLE products (id INT, name TEXT)")
        db.execute("CREATE TABLE orders (id INT, user_id INT)")
        
        tables = db.list_tables()
        assert len(tables) == 3
        print(f"✓ Created {len(tables)} tables")
        
        # Drop one table
        db.execute("DROP TABLE products")
        print("✓ Dropped 'products' table")
        
        # Verify
        tables = db.list_tables()
        assert len(tables) == 2
        assert "products" not in tables
        assert "users" in tables
        assert "orders" in tables
        print(f"✓ Table removed from catalog ({len(tables)} remaining)")
    
    # Test persistence
    with SQLDatabase(db_file) as db:
        tables = db.list_tables()
        assert len(tables) == 2
        assert "products" not in tables
        print("✓ DROP TABLE persisted")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 DROP TABLE Test: PASSED\n")


def test_full_workflow():
    """Test complete workflow with catalog operations"""
    db_file = "test_workflow.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Full Workflow Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # 1. Create table
        db.execute("CREATE TABLE employees (id INT, name TEXT, dept TEXT)")
        print("✓ Created employees table")
        
        # 2. Create index
        db.execute("CREATE INDEX idx_dept ON employees (dept)")
        print("✓ Created index on dept")
        
        # 3. Insert data
        db.execute("INSERT INTO employees VALUES (1, 'Alice', 'Engineering')")
        db.execute("INSERT INTO employees VALUES (2, 'Bob', 'Sales')")
        db.execute("INSERT INTO employees VALUES (3, 'Charlie', 'Engineering')")
        print("✓ Inserted 3 employees")
        
        # 4. Alter table
        db.execute("ALTER TABLE employees ADD COLUMN salary INT")
        print("✓ Added salary column")
        
        # 5. Insert with new schema
        db.execute("INSERT INTO employees VALUES (4, 'David', 'Sales', 60000)")
        print("✓ Inserted employee with salary")
        
        # 6. Query
        results = db.execute("SELECT name, dept FROM employees WHERE dept = 'Engineering'")
        assert len(results) == 2
        print(f"✓ Found {len(results)} engineers")
        
        # 7. Verify catalog
        tables = db.list_tables()
        indexes = db.list_indexes()
        columns = db.describe_table("employees")
        
        assert len(tables) == 1
        assert len(indexes) == 1
        assert len(columns) == 4
        
        print(f"✓ Catalog: {len(tables)} tables, {len(indexes)} indexes, {len(columns)} columns")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Full Workflow Test: PASSED\n")


if __name__ == "__main__":
    try:
        test_catalog_operations()
        test_alter_table()
        test_create_index()
        test_drop_table()
        test_full_workflow()
        
        print("=" * 50)
        print("🎉 ALL PHASE 5 TESTS PASSED! 🎉")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
