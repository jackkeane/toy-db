#!/usr/bin/env python3
"""
Basic test for Phase 1 - Foundation
Tests that we can insert and retrieve data
"""

import os
import sys

# Add python package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb import Database


def test_basic_operations():
    """Test basic insert/get operations"""
    db_file = "test_phase1.db"
    
    # Clean up old test file
    if os.path.exists(db_file):
        os.remove(db_file)
    
    print("=== Phase 1 Test: Basic Key-Value Storage ===\n")
    
    # Create database
    with Database(db_file) as db:
        print("✓ Database created")
        
        # Insert data
        db.insert("user:1", "Alice")
        db.insert("user:2", "Bob")
        db.insert("user:3", "Charlie")
        print("✓ Inserted 3 records")
        
        # Retrieve data
        assert db.get("user:1") == "Alice"
        assert db.get("user:2") == "Bob"
        assert db.get("user:3") == "Charlie"
        print("✓ Retrieved all records correctly")
        
        # Check stats
        stats = db.get_stats()
        print(f"✓ Cache hit rate: {stats['cache_hit_rate']:.2%}")
    
    print("\n=== Test Persistence ===\n")
    
    # Re-open database and verify persistence
    with Database(db_file) as db:
        print("✓ Database reopened")
        
        assert db.get("user:1") == "Alice"
        assert db.get("user:2") == "Bob"
        assert db.get("user:3") == "Charlie"
        print("✓ Data persisted correctly")
    
    # Clean up
    os.remove(db_file)
    
    print("\n🎉 Phase 1 Foundation: PASSED\n")


if __name__ == "__main__":
    try:
        test_basic_operations()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
