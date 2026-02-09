# Phase 2 Summary - B-Tree Index

## What We Built

A fully functional **B-Tree index** for fast, sorted key-value storage.

### Key Features

1. **B-Tree Structure**
   - Internal nodes for navigation
   - Leaf nodes for data storage
   - Linked leaves for efficient range scans
   - Order 16 (max 16 keys per node)

2. **Operations**
   - `Insert(key, value)` - O(log n) with automatic node splitting
   - `Search(key)` - O(log n) binary search in sorted tree
   - `RangeScan(start, end)` - Efficient sorted range retrieval
   - `Delete(key)` - *TODO: Phase 2.5* (requires node merging)

3. **Performance**
   - **97% cache hit rate** on 100-record dataset
   - Automatic tree balancing (node splits)
   - Efficient disk I/O with buffer pool

## Test Results

### Basic Operations Test
```
✓ Inserted 5 records (out of order)
✓ Search operations successful
✓ Range scan [user:002, user:004] returned 3 records
✓ Cache hit rate: 95.83%
✓ Data persisted correctly after reload
```

### Large Dataset Test (100 records)
```
✓ Inserted 100 records
✓ Random access works (O(log n))
✓ Range scan returned 10 records
✓ Cache hit rate: 97.67%
```

## Code Structure

```
cpp/
├── include/
│   └── btree.hpp           # B-Tree interface
└── src/
    └── btree.cpp           # B-Tree implementation (350+ lines)

python/toydb/
└── __init__.py             # IndexedDatabase wrapper

bindings/
└── python_bindings.cpp     # IndexedStorageEngine C++ ↔ Python
```

## Technical Highlights

### Node Splitting Algorithm
When a node reaches capacity (16 keys):
1. Create new sibling node
2. Move upper half of keys to sibling
3. Promote middle key to parent
4. Link siblings (for leaf nodes)
5. Recursively split parent if needed

### Range Scan Optimization
Uses linked leaf nodes:
1. Binary search to find start key
2. Sequential scan through linked leaves
3. Stop when end key exceeded

### Persistence
- All nodes stored in 4KB pages
- Header contains node type, key count, next pointer
- Keys and values serialized with length prefixes
- Child pointers stored for internal nodes

## Performance Characteristics

| Operation   | Time Complexity | Space Complexity |
|-------------|----------------|------------------|
| Insert      | O(log n)       | O(1) per node    |
| Search      | O(log n)       | O(1)             |
| Range Scan  | O(log n + k)   | O(k) where k = # results |
| Delete*     | O(log n)       | O(1)             |

*Delete not yet implemented (requires merging logic)

## What's Next (Phase 3)

**Write-Ahead Log (WAL)**
- Log all writes before applying
- Crash recovery mechanism
- Atomic transactions (ACID)

## Lessons Learned

1. **B-Trees are elegant** - Self-balancing with simple split logic
2. **Serialization matters** - Need careful byte packing for disk storage
3. **Cache is king** - 97% hit rate = minimal disk I/O
4. **Testing is crucial** - Caught several edge cases (header sync, key delimiter)

## Try It Yourself

```python
from toydb import IndexedDatabase

with IndexedDatabase("mydb.dat") as db:
    # Insert 100 users
    for i in range(100):
        db.insert(f"user:{i:04d}", f"User #{i}")
    
    # Fast lookup
    print(db.get("user:0042"))  # O(log 100) = ~7 comparisons
    
    # Range query
    results = db.range_scan("user:0020", "user:0029")
    print(len(results))  # 10 users
```

---

**Status:** ✅ Phase 2 Complete  
**Next:** Phase 3 - Write-Ahead Log
