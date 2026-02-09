# ToyDB Test Suite

Comprehensive test suite for the ToyDB relational database implementation.

## Structure

```
tests/
├── unit/               # Unit tests for individual components
│   ├── test_basic.py          # Basic functionality tests
│   ├── test_phase2.py         # B-Tree index tests
│   ├── test_phase3.py         # WAL and transaction tests
│   ├── test_phase4.py         # SQL parser tests
│   ├── test_phase5.py         # Schema catalog tests
│   ├── test_phase6.py         # Query optimizer tests
│   └── test_phase7.py         # Advanced SQL features tests
├── integration/        # Integration tests between components
│   ├── test_debug.py          # Debugging utilities
│   ├── test_manual_read.py    # Manual data reading tests
│   └── test_rawdata.py        # Raw data access tests
├── performance/        # Performance benchmarks
│   └── test_cache_vs_disk.py  # Cache vs disk performance
├── conftest.py         # Shared pytest fixtures
├── run_tests.py        # Test runner with reporting
└── README.md           # This file
```

## Running Tests

### Quick Start

Run all tests with reports:
```bash
cd toy-db
conda activate py312
python tests/run_tests.py
```

This generates:
- `test_results/test_report.json` - Machine-readable results
- `test_results/test_report.md` - Human-readable summary

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance tests only
pytest tests/performance/ -v

# Specific test file
pytest tests/unit/test_phase2.py -v

# Specific test function
pytest tests/unit/test_phase2.py::test_btree_insert -v
```

### Useful Pytest Options

```bash
# Show print statements
pytest -v -s

# Stop on first failure
pytest -x

# Run only failed tests from last run
pytest --lf

# Show full traceback
pytest --tb=long

# Measure test coverage
pytest --cov=toydb --cov-report=html
```

## Test Categories

### Unit Tests
Test individual components in isolation:
- **Phase 1**: Page management, buffer pool, LRU cache
- **Phase 2**: B-Tree indexing, node splitting, range queries
- **Phase 3**: Write-ahead logging, crash recovery, checkpoints
- **Phase 4**: SQL parsing (CREATE, INSERT, SELECT)
- **Phase 5**: Schema catalog, ALTER TABLE, indexes
- **Phase 6**: Query optimization, statistics, cost estimation
- **Phase 7**: JOINs, aggregations, UPDATE, DELETE

### Integration Tests
Test interactions between components:
- Data persistence across restarts
- Transaction recovery scenarios
- Query execution with multiple components

### Performance Tests
Benchmark critical operations:
- Cache hit rates vs disk I/O
- Large dataset queries
- Index vs full scan performance

## Writing Tests

### Example Test

```python
import pytest
from toydb import BTree, PageManager

def test_btree_basic(temp_db_path):
    """Test basic B-Tree operations"""
    pm = PageManager(temp_db_path)
    tree = BTree(pm)
    
    # Insert
    tree.insert("key1", "value1")
    
    # Lookup
    result = tree.search("key1")
    assert result == "value1"
    
    # Delete
    tree.delete("key1")
    result = tree.search("key1")
    assert result is None
```

### Using Fixtures

The `conftest.py` provides shared fixtures:
- `temp_db_path`: Temporary database path (auto-cleanup)
- `clean_test_files`: Cleanup test database files after test
- `project_root`: Path to project root directory

## Test Reports

### JSON Format
Machine-readable format with detailed results:
```json
{
  "timestamp": "2026-02-09T21:00:00",
  "summary": {
    "total_tests": 50,
    "total_passed": 48,
    "total_failed": 0,
    "total_skipped": 2,
    "success_rate": 100.0
  },
  "test_suites": [...]
}
```

### Markdown Format
Human-readable summary with:
- Overall statistics
- Per-suite breakdown
- Failed test details
- Environment information

## Continuous Integration

To integrate with CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    conda activate py312
    python tests/run_tests.py
    
- name: Upload reports
  uses: actions/upload-artifact@v2
  with:
    name: test-reports
    path: test_results/
```

## Troubleshooting

### Tests fail with import errors
Ensure the project is built:
```bash
conda activate py312
pip install -e .
```

### Database file locked
Clean up stale files:
```bash
rm -f test.db test.db.wal
```

### Pytest not found
Install test dependencies:
```bash
conda activate py312
pip install pytest pytest-json-report
```

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Place unit tests in `tests/unit/`
3. Add integration tests if components interact
4. Update this README if adding new test categories
5. Run full test suite before committing: `python tests/run_tests.py`

## Coverage Goals

- **Unit Tests**: >90% code coverage
- **Integration Tests**: Critical user workflows
- **Performance Tests**: Regression detection (<10% slowdown)
