"""
ToyDB - A minimal but functional database engine
"""

from ._storage_engine import StorageEngine, IndexedStorageEngine, TransactionalStorageEngine
from .parser import parse_sql
from .executor import Executor

__version__ = "0.4.0"
__all__ = [
    "StorageEngine", 
    "IndexedStorageEngine", 
    "TransactionalStorageEngine",
    "Database", 
    "IndexedDatabase",
    "TransactionalDatabase",
    "SQLDatabase",
    "parse_sql"
]


class Database:
    """
    High-level database interface
    
    Example:
        db = Database("mydb.dat")
        db.insert("user:1", "Alice")
        print(db.get("user:1"))  # "Alice"
        db.close()
    """
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.engine = StorageEngine(db_file)
    
    def insert(self, key: str, value: str):
        """Insert a key-value pair"""
        self.engine.insert(key, value)
    
    def get(self, key: str) -> str:
        """Get value by key"""
        return self.engine.get(key)
    
    def flush(self):
        """Flush all changes to disk"""
        self.engine.flush()
    
    def close(self):
        """Close database and flush changes"""
        self.flush()
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        return {
            "cache_hit_rate": self.engine.get_cache_hit_rate()
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class IndexedDatabase:
    """
    B-Tree indexed database (Phase 2)
    
    Features:
    - Sorted key storage with B-Tree index
    - Fast lookups (O(log n) vs O(n))
    - Range queries
    
    Example:
        db = IndexedDatabase("mydb.dat")
        db.insert("user:001", "Alice")
        db.insert("user:002", "Bob")
        db.insert("user:003", "Charlie")
        
        # Get single value
        print(db.get("user:002"))  # "Bob"
        
        # Range query
        results = db.range_scan("user:001", "user:002")
        # [("user:001", "Alice"), ("user:002", "Bob")]
        
        db.close()
    """
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.engine = IndexedStorageEngine(db_file)
    
    def insert(self, key: str, value: str):
        """Insert a key-value pair"""
        self.engine.insert(key, value)
    
    def get(self, key: str) -> str:
        """Get value by key"""
        return self.engine.get(key)
    
    def range_scan(self, start_key: str, end_key: str) -> list:
        """
        Get all key-value pairs in range [start_key, end_key]
        
        Returns:
            List of (key, value) tuples sorted by key
        """
        return self.engine.range_scan(start_key, end_key)
    
    def flush(self):
        """Flush all changes to disk"""
        self.engine.flush()
    
    def close(self):
        """Close database and flush changes"""
        self.flush()
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        return {
            "cache_hit_rate": self.engine.get_cache_hit_rate()
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class TransactionalDatabase:
    """
    Crash-safe transactional database with Write-Ahead Log (Phase 3)
    
    Features:
    - ACID transactions
    - Crash recovery via WAL
    - Automatic checkpoints
    - Durable writes
    
    Example:
        db = TransactionalDatabase("mydb.dat")
        
        # Auto-transaction (single operation)
        db.insert("key1", "value1")
        
        # Manual transaction (multiple operations)
        txn = db.begin_transaction()
        db.insert_txn(txn, "key2", "value2")
        db.insert_txn(txn, "key3", "value3")
        db.commit_transaction(txn)
        
        # Checkpoint (truncate WAL)
        db.checkpoint()
        
        db.close()
    """
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.engine = TransactionalStorageEngine(db_file)
    
    def begin_transaction(self) -> int:
        """Start a new transaction, returns transaction ID"""
        return self.engine.begin_transaction()
    
    def commit_transaction(self, txn_id: int):
        """Commit a transaction"""
        self.engine.commit_transaction(txn_id)
    
    def abort_transaction(self, txn_id: int):
        """Abort a transaction (rollback)"""
        self.engine.abort_transaction(txn_id)
    
    def insert(self, key: str, value: str):
        """Insert with auto-transaction"""
        self.engine.insert(key, value)
    
    def insert_txn(self, txn_id: int, key: str, value: str):
        """Insert within a transaction"""
        self.engine.insert_txn(txn_id, key, value)
    
    def get(self, key: str) -> str:
        """Get value by key"""
        return self.engine.get(key)
    
    def range_scan(self, start_key: str, end_key: str) -> list:
        """Get all key-value pairs in range [start_key, end_key]"""
        return self.engine.range_scan(start_key, end_key)
    
    def checkpoint(self):
        """Create checkpoint and truncate WAL"""
        self.engine.checkpoint()
    
    def flush(self):
        """Flush all changes to disk"""
        self.engine.flush()
    
    def close(self):
        """Close database and flush changes"""
        self.flush()
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        return {
            "cache_hit_rate": self.engine.get_cache_hit_rate(),
            "last_lsn": self.engine.get_last_lsn()
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SQLDatabase:
    """
    SQL-enabled database (Phase 4)
    
    Features:
    - SQL query support (SELECT, INSERT, CREATE TABLE)
    - Schema management
    - Query execution
    - Full ACID transactions
    
    Example:
        db = SQLDatabase("mydb.dat")
        
        # Create table
        db.execute("CREATE TABLE users (id INT, name TEXT, age INT)")
        
        # Insert data
        db.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
        db.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
        db.execute("INSERT INTO users VALUES (3, 'Charlie', 35)")
        
        # Query data
        results = db.execute("SELECT * FROM users WHERE age > 25")
        for row in results:
            print(row)
        
        # Order and limit
        results = db.execute("SELECT name FROM users ORDER BY age LIMIT 2")
        
        db.close()
    """
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.engine = TransactionalStorageEngine(db_file)
        self.executor = Executor(self.engine)
    
    def execute(self, sql: str):
        """
        Execute SQL statement
        
        Returns:
            - For SELECT: List of tuples (rows)
            - For INSERT/CREATE: None
        """
        return self.executor.execute(sql)
    
    def begin_transaction(self) -> int:
        """Start a new transaction"""
        return self.engine.begin_transaction()
    
    def commit_transaction(self, txn_id: int):
        """Commit a transaction"""
        self.engine.commit_transaction(txn_id)
    
    def abort_transaction(self, txn_id: int):
        """Abort a transaction"""
        self.engine.abort_transaction(txn_id)
    
    def checkpoint(self):
        """Create checkpoint"""
        self.engine.checkpoint()
    
    def flush(self):
        """Flush all changes to disk"""
        self.engine.flush()
    
    def close(self):
        """Close database"""
        self.flush()
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        return {
            "cache_hit_rate": self.engine.get_cache_hit_rate(),
            "last_lsn": self.engine.get_last_lsn()
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def list_tables(self) -> list:
        """Get list of all tables"""
        return self.executor.catalog.get_tables()
    
    def describe_table(self, table_name: str) -> list:
        """Get column definitions for a table"""
        return self.executor.catalog.get_columns(table_name)
    
    def list_indexes(self, table_name: str = None) -> list:
        """Get list of indexes"""
        return self.executor.catalog.get_indexes(table_name)
