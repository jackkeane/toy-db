#!/usr/bin/env python3
"""
Phase 2 Test - B-Tree Index
Tests insert, search, and range scan operations
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from toydb import IndexedDatabase


def test_btree_operations():
    """Test B-Tree insert and search"""
    db_file = "test_phase2.db"
    
    if os.path.exists(db_file):
        os.remove(db_file)
    
    print("=== Phase 2 Test: B-Tree Index ===\n")
    
    with IndexedDatabase(db_file) as db:
        print("✓ B-Tree database created")
        
        # Insert data (out of order to test sorting)
        test_data = [
            ("user:003", "Charlie"),
            ("user:001", "Alice"),
            ("user:005", "Eve"),
            ("user:002", "Bob"),
            ("user:004", "David"),
        ]
        
        for key, value in test_data:
            db.insert(key, value)
        
        print(f"✓ Inserted {len(test_data)} records (out of order)")
        
        # Search for specific keys
        assert db.get("user:001") == "Alice"
        assert db.get("user:003") == "Charlie"
        assert db.get("user:005") == "Eve"
        print("✓ Search operations successful")
        
        # Test range scan
        results = db.range_scan("user:002", "user:004")
        expected = [
            ("user:002", "Bob"),
            ("user:003", "Charlie"),
            ("user:004", "David"),
        ]
        
        print(f"\n  Range scan [user:002, user:004]:")
        for key, value in results:
            print(f"    {key} = {value}")
        
        assert results == expected, f"Expected {expected}, got {results}"
        print("✓ Range scan successful")
        
        stats = db.get_stats()
        print(f"✓ Cache hit rate: {stats['cache_hit_rate']:.2%}")
    
    print("\n=== Test Persistence ===\n")
    
    # Reopen and verify
    with IndexedDatabase(db_file) as db:
        print("✓ Database reopened")
        
        assert db.get("user:001") == "Alice"
        assert db.get("user:005") == "Eve"
        print("✓ Data persisted correctly")
        
        # Range scan after reload
        results = db.range_scan("user:001", "user:005")
        assert len(results) == 5
        print(f"✓ Range scan works after reload ({len(results)} records)")
    
    os.remove(db_file)
    print("\n🎉 Phase 2 B-Tree Index: PASSED\n")


def test_large_dataset():
    """Test B-Tree with more data to trigger splits"""
    db_file = "test_btree_large.db"
    
    if os.path.exists(db_file):
        os.remove(db_file)
    
    print("=== Large Dataset Test (Node Splitting) ===\n")
    
    with IndexedDatabase(db_file) as db:
        # Insert enough data to trigger node splits
        n = 100
        for i in range(n):
            key = f"key:{i:04d}"
            value = f"value_{i}"
            db.insert(key, value)
        
        print(f"✓ Inserted {n} records")
        
        # Verify random access
        assert db.get("key:0042") == "value_42"
        assert db.get("key:0099") == "value_99"
        print("✓ Random access works")
        
        # Range scan
        results = db.range_scan("key:0010", "key:0019")
        assert len(results) == 10
        print(f"✓ Range scan returned {len(results)} records")
        
        stats = db.get_stats()
        print(f"✓ Cache hit rate: {stats['cache_hit_rate']:.2%}")
    
    os.remove(db_file)
    print("\n🎉 Large Dataset Test: PASSED\n")


def test_delete_keys():
    """Test deleting keys from B-Tree"""
    db_file = "test_btree_delete.db"

    if os.path.exists(db_file):
        os.remove(db_file)

    with IndexedDatabase(db_file) as db:
        db.insert("k1", "v1")
        db.insert("k2", "v2")
        db.insert("k3", "v3")

        db.delete("k2")

        with pytest.raises(Exception, match="Key not found"):
            db.get("k2")

        assert db.get("k1") == "v1"
        assert db.get("k3") == "v3"
        assert db.range_scan("k1", "k3") == [("k1", "v1"), ("k3", "v3")]

    # Verify persistence after reopen
    with IndexedDatabase(db_file) as db:
        with pytest.raises(Exception, match="Key not found"):
            db.get("k2")
        assert db.get("k1") == "v1"

    os.remove(db_file)


if __name__ == "__main__":
    try:
        test_btree_operations()
        test_large_dataset()
        test_delete_keys()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
