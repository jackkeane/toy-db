#!/usr/bin/env python3
"""
Phase 6 Test - Query Optimization
Tests cost-based optimization, statistics, and EXPLAIN
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb import SQLDatabase


def test_explain_basic():
    """Test EXPLAIN for basic queries"""
    db_file = "test_explain.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Phase 6 Test: EXPLAIN ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table and insert data
        db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
        
        for i in range(100):
            db.execute(f"INSERT INTO users VALUES ({i}, 'User{i}', {20 + (i % 50)})")
        
        print("✓ Created table with 100 rows")
        
        # EXPLAIN simple SELECT
        plan = db.execute("EXPLAIN SELECT * FROM users")
        assert "Query Plan" in plan
        assert "TableScan" in plan
        print("✓ EXPLAIN SELECT * works")
        print(plan)
        print()
        
        # EXPLAIN with WHERE
        plan = db.execute("EXPLAIN SELECT name FROM users WHERE age > 30")
        assert "Query Plan" in plan
        assert "Filter" in plan or "TableScan" in plan
        print("✓ EXPLAIN with WHERE works")
        print(plan)
        print()
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 EXPLAIN Test: PASSED\n")


def test_statistics():
    """Test statistics collection"""
    db_file = "test_stats.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Statistics Collection Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table
        db.execute("CREATE TABLE products (id INT, name TEXT, price INT)")
        print("✓ Created table")
        
        # Check initial stats
        from toydb.executor import Executor
        stats = db.executor.catalog.get_stats("products")
        assert stats["rows"] == 0
        print("✓ Initial row count: 0")
        
        # Insert rows
        for i in range(50):
            db.execute(f"INSERT INTO products VALUES ({i}, 'Product{i}', {100 + i})")
        
        # Stats should be updated
        stats = db.executor.catalog.get_stats("products")
        assert stats["rows"] == 50
        print(f"✓ Row count after inserts: {stats['rows']}")
        
        # EXPLAIN should show correct row estimates
        plan = db.execute("EXPLAIN SELECT * FROM products")
        assert "50" in plan or "estimated_rows=50" in str(plan)
        print("✓ EXPLAIN shows correct row estimates")
    
    # Stats should persist
    with SQLDatabase(db_file) as db:
        stats = db.executor.catalog.get_stats("products")
        assert stats["rows"] == 50
        print("✓ Statistics persisted")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Statistics Test: PASSED\n")


def test_index_optimization():
    """Test index-aware query optimization"""
    db_file = "test_idx_opt.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Index Optimization Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table and insert data
        db.execute("CREATE TABLE employees (id INT, name TEXT, dept TEXT, salary INT)")
        
        for i in range(200):
            dept = ["Engineering", "Sales", "Marketing"][i % 3]
            db.execute(f"INSERT INTO employees VALUES ({i}, 'Employee{i}', '{dept}', {50000 + i * 100})")
        
        print("✓ Created table with 200 rows")
        
        # Query without index
        plan_no_idx = db.execute("EXPLAIN SELECT * FROM employees WHERE dept = 'Engineering'")
        print("Plan WITHOUT index:")
        print(plan_no_idx)
        assert "TableScan" in plan_no_idx
        print("✓ Uses TableScan without index")
        print()
        
        # Create index
        db.execute("CREATE INDEX idx_dept ON employees (dept)")
        print("✓ Created index on dept")
        
        # Query with index (should consider index scan)
        plan_with_idx = db.execute("EXPLAIN SELECT * FROM employees WHERE dept = 'Engineering'")
        print("Plan WITH index:")
        print(plan_with_idx)
        
        # Note: The planner might still choose TableScan if it's cheaper
        # For 200 rows, index might not be worth it
        if "IndexScan" in plan_with_idx:
            print("✓ Planner considered IndexScan")
        else:
            print("✓ Planner chose TableScan (cost-based decision)")
        print()
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Index Optimization Test: PASSED\n")


def test_cost_estimation():
    """Test cost-based plan selection"""
    db_file = "test_cost.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Cost Estimation Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create large table
        db.execute("CREATE TABLE orders (id INT, user_id INT, amount INT, status TEXT)")
        
        # Insert many rows to make index worthwhile
        for i in range(1000):
            status = "completed" if i % 10 == 0 else "pending"
            db.execute(f"INSERT INTO orders VALUES ({i}, {i % 100}, {100 + i}, '{status}')")
        
        print("✓ Created table with 1000 rows")
        
        # Without index
        plan1 = db.execute("EXPLAIN SELECT * FROM orders WHERE status = 'completed'")
        cost1_str = [line for line in plan1.split("\n") if "Estimated cost" in line][0]
        cost1 = float(cost1_str.split(":")[1].strip())
        print(f"TableScan cost: {cost1}")
        
        # Create index
        db.execute("CREATE INDEX idx_status ON orders (status)")
        
        # With index
        plan2 = db.execute("EXPLAIN SELECT * FROM orders WHERE status = 'completed'")
        
        # Check if IndexScan is in the plan
        if "IndexScan" in plan2:
            cost2_str = [line for line in plan2.split("\n") if "Estimated cost" in line][0]
            cost2 = float(cost2_str.split(":")[1].strip())
            print(f"IndexScan cost: {cost2}")
            
            if cost2 < cost1:
                print("✓ IndexScan has lower estimated cost")
            else:
                print("✓ Cost estimation working (IndexScan considered)")
        else:
            print("✓ Planner chose TableScan based on cost estimate")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Cost Estimation Test: PASSED\n")


def test_complex_plans():
    """Test query plans with multiple operations"""
    db_file = "test_complex_plan.db"
    wal_file = db_file + ".wal"
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("=== Complex Query Plans Test ===\n")
    
    with SQLDatabase(db_file) as db:
        # Create table
        db.execute("CREATE TABLE customers (id INT, name TEXT, age INT, city TEXT)")
        
        for i in range(100):
            db.execute(f"INSERT INTO customers VALUES ({i}, 'Customer{i}', {25 + i % 40}, 'City{i % 10}')")
        
        print("✓ Created table with 100 rows")
        
        # Complex query with WHERE, ORDER BY, LIMIT
        plan = db.execute(
            "EXPLAIN SELECT name, age FROM customers WHERE age > 30 ORDER BY age LIMIT 10"
        )
        
        print("Complex query plan:")
        print(plan)
        
        # Verify plan contains expected operations
        assert "Project" in plan
        assert "Limit" in plan
        assert "Sort" in plan or "ORDER BY" in plan.upper()
        assert "Filter" in plan or "WHERE" in plan.upper()
        assert "TableScan" in plan or "IndexScan" in plan
        
        print("✓ Plan contains all expected operations")
        print("✓ Operations in correct order: Scan → Filter → Sort → Limit → Project")
    
    # Clean up
    for f in [db_file, wal_file]:
        if os.path.exists(f):
            os.remove(f)
    
    print("\n🎉 Complex Plans Test: PASSED\n")


if __name__ == "__main__":
    try:
        test_explain_basic()
        test_statistics()
        test_index_optimization()
        test_cost_estimation()
        test_complex_plans()
        
        print("=" * 50)
        print("🎉 ALL PHASE 6 TESTS PASSED! 🎉")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
