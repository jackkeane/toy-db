#!/usr/bin/env python3
"""
Phase 4 Test - SQL Parser & Query Execution
Tests SQL parsing and query execution
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb import SQLDatabase, parse_sql
from toydb.ast_nodes import *


def test_parser():
    """Test SQL parser"""
    print("=== SQL Parser Test ===\n")
    
    # CREATE TABLE
    ast = parse_sql("CREATE TABLE users (id INT, name TEXT, age INT)")
    assert isinstance(ast, CreateTableStmt)
    assert ast.table_name == "users"
    assert len(ast.columns) == 3
    assert ast.columns[0].name == "id"
    assert ast.columns[0].type == "INT"
    print("✓ Parsed CREATE TABLE")
    
    # INSERT
    ast = parse_sql("INSERT INTO users VALUES (1, 'Alice', 30)")
    assert isinstance(ast, InsertStmt)
    assert ast.table_name == "users"
    assert ast.values == [1, 'Alice', 30]
    print("✓ Parsed INSERT")
    
    # SELECT *
    ast = parse_sql("SELECT * FROM users")
    assert isinstance(ast, SelectStmt)
    assert ast.columns == ["*"]
    assert ast.table_name == "users"
    print("✓ Parsed SELECT *")
    
    # SELECT with WHERE
    ast = parse_sql("SELECT name, age FROM users WHERE age > 25")
    assert isinstance(ast, SelectStmt)
    assert ast.columns == ["name", "age"]
    assert ast.where is not None
    assert isinstance(ast.where, BinaryOp)
    print("✓ Parsed SELECT with WHERE")
    
    # SELECT with ORDER BY and LIMIT
    ast = parse_sql("SELECT * FROM users ORDER BY age LIMIT 10")
    assert isinstance(ast, SelectStmt)
    assert ast.order_by == "age"
    assert ast.limit == 10
    print("✓ Parsed SELECT with ORDER BY and LIMIT")
    
    print("\n🎉 Parser Test: PASSED\n")


def test_sql_execution():
    """Test SQL query execution"""
    db_file = "test_sql.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== SQL Execution Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table
        db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
        print("✓ Created table 'users'")
        
        # Insert data
        db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
        db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
        db.execute("INSERT INTO users VALUES (3, 'Charlie', 35)")
        db.execute("INSERT INTO users VALUES (4, 'David', 28)")
        print("✓ Inserted 4 rows")
        
        # SELECT *
        results = db.execute("SELECT * FROM users")
        assert len(results) == 4
        print(f"✓ SELECT * returned {len(results)} rows")
        
        # SELECT specific columns
        results = db.execute("SELECT name, age FROM users")
        assert len(results) == 4
        assert len(results[0]) == 2
        print("✓ SELECT name, age successful")
        
        # WHERE clause
        results = db.execute("SELECT name FROM users WHERE age > 28")
        assert len(results) == 2  # Alice (30) and Charlie (35)
        print(f"✓ WHERE age > 28 returned {len(results)} rows")
        
        # ORDER BY
        results = db.execute("SELECT name, age FROM users ORDER BY age")
        ages = [row[1] for row in results]
        assert ages == sorted(ages), "Results should be sorted by age"
        print("✓ ORDER BY age successful")
        
        # LIMIT
        results = db.execute("SELECT * FROM users LIMIT 2")
        assert len(results) == 2
        print("✓ LIMIT 2 successful")
        
        # Combined: WHERE + ORDER BY + LIMIT
        results = db.execute(
            "SELECT name, age FROM users WHERE age >= 25 ORDER BY age LIMIT 3"
        )
        assert len(results) == 3
        print("✓ Combined WHERE + ORDER BY + LIMIT successful")
        
        stats = db.get_stats()
        print(f"✓ Cache hit rate: {stats['cache_hit_rate']:.2%}")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 SQL Execution Test: PASSED\n")


def test_persistence():
    """Test SQL data persistence"""
    db_file = "test_sql_persist.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== SQL Persistence Test ===\n")
    
    # Create and populate
    with SQLDatabase(db_file) as db:
        db.execute("CREATE TABLE products (id INT, name TEXT, price INT)")
        db.execute("INSERT INTO products VALUES (1, 'Laptop', 1000)")
        db.execute("INSERT INTO products VALUES (2, 'Mouse', 25)")
        db.execute("INSERT INTO products VALUES (3, 'Keyboard', 75)")
        print("✓ Created table and inserted data")
    
    # Reopen and query
    with SQLDatabase(db_file) as db:
        results = db.execute("SELECT * FROM products")
        assert len(results) == 3
        print("✓ Data persisted correctly")
        
        # Query with WHERE
        results = db.execute("SELECT name FROM products WHERE price < 100")
        assert len(results) == 2  # Mouse and Keyboard
        print("✓ Query after reload successful")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Persistence Test: PASSED\n")


def test_complex_queries():
    """Test more complex SQL queries"""
    db_file = "test_complex.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Complex Query Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table
        db.execute("CREATE TABLE employees (id INT, name TEXT, salary INT, dept TEXT)")
        
        # Insert test data
        employees = [
            (1, "Alice", 75000, "Engineering"),
            (2, "Bob", 60000, "Sales"),
            (3, "Charlie", 90000, "Engineering"),
            (4, "David", 55000, "Sales"),
            (5, "Eve", 80000, "Marketing"),
            (6, "Frank", 70000, "Engineering"),
        ]
        
        for emp in employees:
            db.execute(f"INSERT INTO employees VALUES {emp}")
        
        print(f"✓ Inserted {len(employees)} employees")
        
        # Query: High earners (> 70k)
        results = db.execute("SELECT name, salary FROM employees WHERE salary > 70000")
        assert len(results) == 3  # Alice (75k), Charlie (90k), Eve (80k)
        print(f"✓ Found {len(results)} employees earning > $70,000")
        
        # Query: Engineering department
        results = db.execute("SELECT name FROM employees WHERE dept = 'Engineering'")
        assert len(results) == 3  # Alice, Charlie, Frank
        print(f"✓ Found {len(results)} engineers")
        
        # Query: Top 3 salaries
        results = db.execute("SELECT name, salary FROM employees ORDER BY salary LIMIT 3")
        # Should be: David (55k), Bob (60k), Frank (70k)
        assert results[0][1] == 55000
        assert results[1][1] == 60000
        assert results[2][1] == 70000
        print("✓ Top 3 lowest salaries correct")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Complex Query Test: PASSED\n")


if __name__ == "__main__":
    try:
        test_parser()
        test_sql_execution()
        test_persistence()
        test_complex_queries()
        
        print("=" * 50)
        print("🎉 ALL PHASE 4 TESTS PASSED! 🎉")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
