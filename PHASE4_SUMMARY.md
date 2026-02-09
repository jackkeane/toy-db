# Phase 4 Summary - SQL Parser & Query Execution

## What We Built

A **SQL parser and query executor** that brings SQL to ToyDB!

### Key Features

1. **SQL Parser**
   - Tokenizer with regex-based lexing
   - Recursive descent parser
   - AST (Abstract Syntax Tree) generation
   - Support for CREATE TABLE, INSERT, SELECT

2. **Supported SQL**
   ```sql
   CREATE TABLE table_name (col1 TYPE, col2 TYPE, ...)
   INSERT INTO table_name VALUES (val1, val2, ...)
   SELECT columns FROM table_name
   SELECT columns FROM table_name WHERE condition
   SELECT columns FROM table_name ORDER BY col
   SELECT columns FROM table_name LIMIT n
   ```

3. **Query Executor**
   - Schema management (in-memory catalog)
   - Table scans with B-Tree range queries
   - WHERE clause evaluation
   - ORDER BY sorting
   - LIMIT pagination
   - Type casting (INT, TEXT, FLOAT)

4. **Expression System**
   - Binary operators: =, >, <, >=, <=, !=
   - Logical operators: AND, OR
   - Column references
   - Literal values

## Test Results

### Parser Tests
```
✓ Parsed CREATE TABLE
✓ Parsed INSERT
✓ Parsed SELECT *
✓ Parsed SELECT with WHERE
✓ Parsed SELECT with ORDER BY and LIMIT
```

### SQL Execution
```
✓ Created table 'users'
✓ Inserted 4 rows
✓ SELECT * returned 4 rows
✓ SELECT name, age successful
✓ WHERE age > 28 returned 2 rows
✓ ORDER BY age successful
✓ LIMIT 2 successful
✓ Combined WHERE + ORDER BY + LIMIT successful
✓ Cache hit rate: 96.43%
```

### Persistence
```
✓ Created table and inserted data
✓ Data persisted correctly
✓ Query after reload successful
```

### Complex Queries
```
✓ Inserted 6 employees
✓ Found 3 employees earning > $70,000
✓ Found 3 engineers
✓ Top 3 lowest salaries correct
```

## Code Structure

```
python/toydb/
├── ast_nodes.py          # AST node definitions (190 lines)
├── parser.py             # SQL parser (370 lines)
├── executor.py           # Query executor (330 lines)
└── __init__.py           # SQLDatabase wrapper
```

## Technical Highlights

### Parser Architecture
```
SQL String → Tokenizer → Tokens → Parser → AST → Executor → Results
```

### Storage Format

**Schema metadata:**
```
Key:   __schema__table_name
Value: col1:TYPE;col2:TYPE;col3:TYPE
```

**Row data:**
```
Key:   table_name:000000001234567890
Value: val1|val2|val3
```

### Query Execution Flow
1. Parse SQL → AST
2. Load schema from catalog
3. Range scan table rows (B-Tree)
4. Parse row data
5. Apply WHERE filter
6. Apply ORDER BY
7. Apply LIMIT
8. Project columns

## Performance

| Operation | Performance |
|-----------|-------------|
| Parse SQL | < 1ms |
| Table scan | O(n) rows |
| WHERE filter | O(n) |
| ORDER BY | O(n log n) |
| Cache hit rate | 96.43% |

## Example Usage

```python
from toydb import SQLDatabase

with SQLDatabase("mydb.dat") as db:
    # Create table
    db.execute("CREATE TABLE employees (id INT, name TEXT, salary INT)")
    
    # Insert data
    db.execute("INSERT INTO employees VALUES (1, 'Alice', 75000)")
    db.execute("INSERT INTO employees VALUES (2, 'Bob', 60000)")
    db.execute("INSERT INTO employees VALUES (3, 'Charlie', 90000)")
    
    # Simple query
    results = db.execute("SELECT * FROM employees")
    # [(1, 'Alice', 75000), (2, 'Bob', 60000), (3, 'Charlie', 90000)]
    
    # Filtered query
    results = db.execute("SELECT name, salary FROM employees WHERE salary > 70000")
    # [('Alice', 75000), ('Charlie', 90000)]
    
    # Sorted with limit
    results = db.execute("SELECT name FROM employees ORDER BY salary LIMIT 2")
    # [('Bob',), ('Alice',)]
```

## Supported SQL Grammar

```
CREATE TABLE:
    CREATE TABLE table_name (
        col1 TYPE,
        col2 TYPE,
        ...
    )

INSERT:
    INSERT INTO table_name VALUES (val1, val2, ...)

SELECT:
    SELECT column1, column2, ... | *
    FROM table_name
    [WHERE condition]
    [ORDER BY column]
    [LIMIT n]

WHERE condition:
    column operator value
    condition AND condition
    condition OR condition
    
Operators:
    =, >, <, >=, <=, !=

Types:
    INT, TEXT, FLOAT
```

## Known Limitations

1. **No JOINs** - Only single table queries
2. **No aggregations** - No SUM, COUNT, AVG, GROUP BY
3. **No subqueries** - Can't nest SELECT statements
4. **Simple type system** - Only INT, TEXT, FLOAT
5. **No indexes on columns** - Table scans only (B-Tree on row keys)
6. **No DELETE/UPDATE** - Only CREATE and INSERT

These are planned for future phases.

## What's Next (Phase 5+)

**Phase 5: Schema & Catalog**
- Persistent catalog (not just in-memory)
- ALTER TABLE support
- Index creation (CREATE INDEX)
- Foreign keys

**Phase 6: Query Optimization**
- Cost-based query planning
- Index selection
- Statistics collection

**Phase 7: Advanced SQL**
- JOINs (nested loop, hash join)
- Aggregations (GROUP BY, HAVING)
- Subqueries
- DELETE & UPDATE

## Lessons Learned

1. **Parsing is fun** - Recursive descent is elegant and easy to understand
2. **AST is powerful** - Clean separation between parsing and execution
3. **Type casting matters** - String vs int comparison is tricky
4. **Range scans rock** - B-Tree makes table scans fast
5. **Testing SQL is easy** - Declarative queries are self-documenting

## Architecture Evolution

```
Phase 1: Page Storage
    ↓
Phase 2: B-Tree Index
    ↓
Phase 3: WAL + Transactions
    ↓
Phase 4: SQL Parser ← YOU ARE HERE
    ↓
Phase 5: Schema & Catalog
    ↓
Phase 6: Query Optimization
```

---

**Status:** ✅ Phase 4 Complete  
**Next:** Phase 5 - Persistent Schema & Catalog

**Achievement Unlocked:** You can now run SQL queries on your hand-built database! 🎉
