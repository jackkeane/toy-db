"""
System Catalog - Persistent storage for database metadata

The catalog stores:
- Table definitions (schemas)
- Index definitions
- Statistics
- Constraints (future)
"""

from typing import List, Optional, Dict
from .ast_nodes import ColumnDef


class Catalog:
    """
    System catalog for database metadata
    
    Uses special system tables:
    - __catalog__tables: Table definitions
    - __catalog__columns: Column definitions
    - __catalog__indexes: Index definitions
    - __catalog__stats: Table statistics
    """
    
    # System table prefixes
    TABLES_PREFIX = "__catalog__tables:"
    COLUMNS_PREFIX = "__catalog__columns:"
    INDEXES_PREFIX = "__catalog__indexes:"
    STATS_PREFIX = "__catalog__stats:"
    
    def __init__(self, storage_engine):
        """
        Args:
            storage_engine: TransactionalStorageEngine or IndexedStorageEngine
        """
        self.engine = storage_engine
    
    # ============================================================
    # Table Management
    # ============================================================
    
    def create_table(self, table_name: str, columns: List[ColumnDef]):
        """
        Register a new table in the catalog
        
        Stores:
        - Table metadata: __catalog__tables:table_name
        - Column metadata: __catalog__columns:table_name:col_name
        """
        # Check if table already exists
        if self.table_exists(table_name):
            raise RuntimeError(f"Table '{table_name}' already exists")
        
        # Store table metadata
        table_key = f"{self.TABLES_PREFIX}{table_name}"
        table_value = f"columns={len(columns)}"
        self.engine.insert(table_key, table_value)
        
        # Store column metadata
        for i, col in enumerate(columns):
            col_key = f"{self.COLUMNS_PREFIX}{table_name}:{col.name}"
            col_value = f"type={col.type},ordinal={i}"
            self.engine.insert(col_key, col_value)
    
    def drop_table(self, table_name: str):
        """Remove a table from the catalog"""
        if not self.table_exists(table_name):
            raise RuntimeError(f"Table '{table_name}' does not exist")
        
        # Note: In a real DB, we'd also delete all rows
        # For now, we just remove catalog entries
        
        # First, get the columns before marking as deleted
        # Scan column entries for this table
        start_key = f"{self.COLUMNS_PREFIX}{table_name}:"
        end_key = f"{self.COLUMNS_PREFIX}{table_name}:~"
        
        results = self.engine.range_scan(start_key, end_key)
        
        # Mark all columns as deleted
        for key, value in results:
            if value != "DELETED":
                self.engine.insert(key, "DELETED")
        
        # Remove table metadata
        table_key = f"{self.TABLES_PREFIX}{table_name}"
        # Note: We don't have DELETE yet, so we mark as deleted
        self.engine.insert(table_key, "DELETED")
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        table_key = f"{self.TABLES_PREFIX}{table_name}"
        # Use range_scan to check if table exists (more reliable than get)
        start_key = table_key
        end_key = table_key + "~"
        results = self.engine.range_scan(start_key, end_key)
        
        for key, value in results:
            if key == table_key and value != "DELETED":
                return True
        return False
    
    def get_tables(self) -> List[str]:
        """Get list of all tables"""
        # Scan all table entries
        start_key = self.TABLES_PREFIX
        end_key = self.TABLES_PREFIX + "~"
        
        results = self.engine.range_scan(start_key, end_key)
        
        tables = []
        for key, value in results:
            if value != "DELETED":
                # Extract table name from key
                table_name = key[len(self.TABLES_PREFIX):]
                tables.append(table_name)
        
        return sorted(tables)
    
    def get_columns(self, table_name: str) -> List[ColumnDef]:
        """Get column definitions for a table"""
        if not self.table_exists(table_name):
            raise RuntimeError(f"Table '{table_name}' does not exist")
        
        # Scan column entries for this table
        start_key = f"{self.COLUMNS_PREFIX}{table_name}:"
        end_key = f"{self.COLUMNS_PREFIX}{table_name}:~"
        
        results = self.engine.range_scan(start_key, end_key)
        
        columns = []
        for key, value in results:
            if value == "DELETED":
                continue
            
            # Parse column metadata
            # Format: type=INT,ordinal=0
            metadata = {}
            for part in value.split(","):
                k, v = part.split("=")
                metadata[k] = v
            
            # Extract column name from key
            col_name = key.split(":")[-1]
            
            columns.append((
                int(metadata["ordinal"]),
                ColumnDef(col_name, metadata["type"])
            ))
        
        # Sort by ordinal position
        columns.sort(key=lambda x: x[0])
        
        return [col for _, col in columns]
    
    def add_column(self, table_name: str, column: ColumnDef):
        """Add a column to an existing table (ALTER TABLE ADD COLUMN)"""
        if not self.table_exists(table_name):
            raise RuntimeError(f"Table '{table_name}' does not exist")
        
        # Get current columns to determine next ordinal
        current_cols = self.get_columns(table_name)
        next_ordinal = len(current_cols)
        
        # Store new column metadata
        col_key = f"{self.COLUMNS_PREFIX}{table_name}:{column.name}"
        col_value = f"type={column.type},ordinal={next_ordinal}"
        self.engine.insert(col_key, col_value)
        
        # Update table metadata
        table_key = f"{self.TABLES_PREFIX}{table_name}"
        table_value = f"columns={next_ordinal + 1}"
        self.engine.insert(table_key, table_value)
    
    # ============================================================
    # Index Management
    # ============================================================
    
    def create_index(self, index_name: str, table_name: str, column_name: str):
        """
        Register an index in the catalog
        
        Note: This only registers the index metadata.
        Building the actual index is handled by the executor.
        """
        if not self.table_exists(table_name):
            raise RuntimeError(f"Table '{table_name}' does not exist")
        
        # Verify column exists
        columns = self.get_columns(table_name)
        if column_name not in [col.name for col in columns]:
            raise RuntimeError(f"Column '{column_name}' does not exist in table '{table_name}'")
        
        # Store index metadata
        index_key = f"{self.INDEXES_PREFIX}{index_name}"
        index_value = f"table={table_name},column={column_name}"
        self.engine.insert(index_key, index_value)
    
    def drop_index(self, index_name: str):
        """Remove an index from the catalog"""
        index_key = f"{self.INDEXES_PREFIX}{index_name}"
        
        try:
            self.engine.get(index_key)
        except:
            raise RuntimeError(f"Index '{index_name}' does not exist")
        
        # Mark as deleted
        self.engine.insert(index_key, "DELETED")
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[Dict]:
        """
        Get index definitions
        
        Args:
            table_name: If specified, only return indexes for this table
        
        Returns:
            List of dicts with 'name', 'table', 'column'
        """
        # Scan all index entries
        start_key = self.INDEXES_PREFIX
        end_key = self.INDEXES_PREFIX + "~"
        
        results = self.engine.range_scan(start_key, end_key)
        
        indexes = []
        for key, value in results:
            if value == "DELETED":
                continue
            
            # Parse index metadata
            # Format: table=users,column=age
            metadata = {}
            for part in value.split(","):
                k, v = part.split("=")
                metadata[k] = v
            
            # Filter by table if specified
            if table_name and metadata["table"] != table_name:
                continue
            
            # Extract index name from key
            index_name = key[len(self.INDEXES_PREFIX):]
            
            indexes.append({
                "name": index_name,
                "table": metadata["table"],
                "column": metadata["column"]
            })
        
        return indexes
    
    # ============================================================
    # Statistics
    # ============================================================
    
    def update_stats(self, table_name: str, row_count: int):
        """Update table statistics (for query optimization)"""
        stats_key = f"{self.STATS_PREFIX}{table_name}"
        stats_value = f"rows={row_count}"
        self.engine.insert(stats_key, stats_value)
    
    def get_stats(self, table_name: str) -> Dict:
        """Get table statistics"""
        stats_key = f"{self.STATS_PREFIX}{table_name}"
        
        try:
            value = self.engine.get(stats_key)
            
            # Parse stats
            stats = {}
            for part in value.split(","):
                k, v = part.split("=")
                stats[k] = int(v) if v.isdigit() else v
            
            return stats
        except:
            return {"rows": 0}
