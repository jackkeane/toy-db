"""
Query Executor - Execute parsed SQL queries against storage engine
"""

from typing import List, Tuple, Any, Optional, Union, Set
from .ast_nodes import *
from .parser import parse_sql
from .catalog import Catalog
from .planner import QueryPlanner, plan_to_string
from .aggregates import apply_aggregates


class Executor:
    """
    Query executor for ToyDB
    
    Executes SQL queries against the storage engine
    """
    
    def __init__(self, storage_engine):
        """
        Args:
            storage_engine: TransactionalStorageEngine or IndexedStorageEngine
        """
        self.engine = storage_engine
        # Persistent catalog for table schemas
        self.catalog = Catalog(storage_engine)
        # Query planner for optimization
        self.planner = QueryPlanner(self.catalog, storage_engine)
    
    def execute(self, sql: str) -> Optional[Union[List[Tuple], str]]:
        """
        Execute SQL statement
        
        Returns:
            - For SELECT: List of tuples (rows)
            - For EXPLAIN: String (query plan)
            - For INSERT/CREATE/etc: None
        """
        ast = parse_sql(sql)
        
        if isinstance(ast, ExplainStmt):
            return self.execute_explain(ast)
        elif isinstance(ast, CreateTableStmt):
            return self.execute_create_table(ast)
        elif isinstance(ast, DropTableStmt):
            return self.execute_drop_table(ast)
        elif isinstance(ast, AlterTableStmt):
            return self.execute_alter_table(ast)
        elif isinstance(ast, CreateIndexStmt):
            return self.execute_create_index(ast)
        elif isinstance(ast, DropIndexStmt):
            return self.execute_drop_index(ast)
        elif isinstance(ast, InsertStmt):
            return self.execute_insert(ast)
        elif isinstance(ast, SelectStmt):
            return self.execute_select(ast)
        elif isinstance(ast, UpdateStmt):
            return self.execute_update(ast)
        elif isinstance(ast, DeleteStmt):
            return self.execute_delete(ast)
        else:
            raise RuntimeError(f"Unsupported statement type: {type(ast)}")
    
    # ============================================================
    # DDL Execution
    # ============================================================
    
    def execute_create_table(self, stmt: CreateTableStmt) -> None:
        """Execute CREATE TABLE"""
        self.catalog.create_table(stmt.table_name, stmt.columns)
    
    def execute_drop_table(self, stmt: DropTableStmt) -> None:
        """Execute DROP TABLE"""
        self.catalog.drop_table(stmt.table_name)
    
    def execute_alter_table(self, stmt: AlterTableStmt) -> None:
        """Execute ALTER TABLE ADD COLUMN"""
        if stmt.action == "ADD_COLUMN":
            self.catalog.add_column(stmt.table_name, stmt.column)
        else:
            raise RuntimeError(f"Unsupported ALTER TABLE action: {stmt.action}")
    
    def execute_create_index(self, stmt: CreateIndexStmt) -> None:
        """Execute CREATE INDEX"""
        self.catalog.create_index(stmt.index_name, stmt.table_name, stmt.column_name)
    
    def execute_drop_index(self, stmt: DropIndexStmt) -> None:
        """Execute DROP INDEX"""
        self.catalog.drop_index(stmt.index_name)
    
    def execute_explain(self, stmt: ExplainStmt) -> str:
        """
        Execute EXPLAIN - show query plan
        
        Returns:
            String representation of the query plan
        """
        inner = stmt.query
        
        if not isinstance(inner, SelectStmt):
            return f"EXPLAIN only supported for SELECT (got {type(inner).__name__})"
        
        # Generate query plan
        plan = self.planner.plan(inner)
        
        # Format plan as string
        result = "Query Plan:\n"
        result += "=" * 50 + "\n"
        result += plan_to_string(plan) + "\n"
        result += "=" * 50 + "\n"
        result += f"Estimated cost: {plan.cost:.1f}\n"
        result += f"Estimated rows: {plan.estimated_rows}\n"
        
        return result
    
    # ============================================================
    # DML Execution
    # ============================================================
    
    def execute_insert(self, stmt: InsertStmt) -> None:
        """
        Execute INSERT INTO ... VALUES (...)
        
        Storage format:
        Key: table_name:row_id
        Value: col1|col2|col3|...
        """
        # Get table schema from catalog
        columns = self.catalog.get_columns(stmt.table_name)
        
        if len(stmt.values) != len(columns):
            raise RuntimeError(
                f"Column count mismatch: expected {len(columns)}, got {len(stmt.values)}"
            )
        
        # Generate unique row ID
        # Simple approach: use timestamp + counter
        import time
        row_id = int(time.time() * 1000000)
        
        # Serialize row data
        row_data = "|".join(str(v) for v in stmt.values)
        
        # Store in B-Tree
        key = f"{stmt.table_name}:{row_id:020d}"
        self.engine.insert(key, row_data)
        
        # Update statistics (row count)
        stats = self.catalog.get_stats(stmt.table_name)
        current_rows = stats.get("rows", 0)
        self.catalog.update_stats(stmt.table_name, current_rows + 1)
    
    def execute_update(self, stmt: UpdateStmt) -> None:
        """Execute UPDATE statement"""
        # Get table schema
        columns = self.catalog.get_columns(stmt.table_name)
        col_names = [col.name for col in columns]
        
        # Scan all rows
        start_key = f"{stmt.table_name}:"
        end_key = f"{stmt.table_name}:~"
        all_rows = self.engine.range_scan(start_key, end_key)
        
        updated_count = 0
        
        for key, value in all_rows:
            # Parse row
            values = value.split("|")
            row = {}
            for i, col in enumerate(columns):
                if i < len(values):
                    row[col.name] = self._cast_value(values[i], col.type)
            
            # Check WHERE condition
            if stmt.where is None or self._evaluate_expr(stmt.where, row):
                # Update the row
                for col_name, new_value in stmt.assignments.items():
                    if col_name in row:
                        row[col_name] = new_value
                
                # Serialize updated row
                new_values = []
                for col in columns:
                    new_values.append(str(row.get(col.name, "")))
                
                new_row_data = "|".join(new_values)
                self.engine.insert(key, new_row_data)
                updated_count += 1
        
        print(f"Updated {updated_count} row(s)")
    
    def execute_delete(self, stmt: DeleteStmt) -> None:
        """Execute DELETE statement"""
        # Get table schema
        columns = self.catalog.get_columns(stmt.table_name)
        
        # Scan all rows
        start_key = f"{stmt.table_name}:"
        end_key = f"{stmt.table_name}:~"
        all_rows = self.engine.range_scan(start_key, end_key)
        
        # Collect keys to delete
        keys_to_delete = []
        
        for key, value in all_rows:
            # Parse row
            values = value.split("|")
            row = {}
            for i, col in enumerate(columns):
                if i < len(values):
                    row[col.name] = self._cast_value(values[i], col.type)
            
            # Check WHERE condition
            if stmt.where is None or self._evaluate_expr(stmt.where, row):
                keys_to_delete.append(key)
        
        # Mark as deleted (we still don't have physical DELETE)
        for key in keys_to_delete:
            self.engine.insert(key, "DELETED")
        
        # Update statistics
        stats = self.catalog.get_stats(stmt.table_name)
        current_rows = stats.get("rows", 0)
        self.catalog.update_stats(stmt.table_name, max(0, current_rows - len(keys_to_delete)))
        
        print(f"Deleted {len(keys_to_delete)} row(s)")
    
    def execute_select(self, stmt: SelectStmt) -> List[Tuple]:
        """
        Execute SELECT ... FROM ... WHERE ...
        
        Now supports:
        1. JOINs
        2. Aggregate functions (COUNT, SUM, AVG, MIN, MAX)
        3. GROUP BY
        4. HAVING
        5. ORDER BY
        6. LIMIT
        """
        # Get table schema from catalog
        columns = self.catalog.get_columns(stmt.table_name)
        
        # Table scan: get all rows
        start_key = f"{stmt.table_name}:"
        end_key = f"{stmt.table_name}:~"  # ~ is after all digits
        
        all_rows = self.engine.range_scan(start_key, end_key)
        
        # Parse rows
        rows = []
        for key, value in all_rows:
            # Skip deleted rows and metadata
            if value == "DELETED" or key.startswith("__"):
                continue
            
            # Parse row data
            values = value.split("|")
            
            # Create row dict
            row = {}
            for i, col in enumerate(columns):
                if i < len(values):
                    row[col.name] = self._cast_value(values[i], col.type)
                else:
                    row[col.name] = None
            
            rows.append(row)
        
        # Handle JOIN if present
        if stmt.join:
            rows = self._execute_join(rows, stmt, columns)
        
        # Filter by WHERE clause
        if stmt.where:
            rows = [r for r in rows if self._evaluate_expr(stmt.where, r)]
        
        # Handle aggregates and GROUP BY
        if stmt.group_by or self._has_aggregates(stmt.columns):
            result = apply_aggregates(rows, stmt.columns, stmt.group_by)
            
            # Apply HAVING filter (after grouping)
            if stmt.having:
                # HAVING filter on aggregated results
                # For simplicity, we skip this for now
                pass
        else:
            # No aggregates - regular projection
            # Order by
            if stmt.order_by:
                rows.sort(key=lambda r: self._resolve_column_value(stmt.order_by, r))
            
            # Limit
            if stmt.limit:
                rows = rows[:stmt.limit]
            
            # Project columns
            if stmt.columns == ["*"]:
                # Return all columns from the base table schema
                result = []
                for row in rows:
                    result.append(tuple(row.get(col.name) for col in columns))
            else:
                # Return requested columns with ambiguity checks
                result = []
                for row in rows:
                    result.append(tuple(self._resolve_column_value(col, row, strict_ambiguous=True) for col in stmt.columns))
        
        return result
    
    def _has_aggregates(self, columns: List[str]) -> bool:
        """Check if any column is an aggregate function"""
        for col in columns:
            if any(func in col.upper() for func in ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX("]):
                return True
        return False
    
    def _execute_join(self, left_rows: List[Dict], stmt: SelectStmt, left_cols: List) -> List[Dict]:
        """Execute JOIN operation"""
        join = stmt.join
        left_table = stmt.table_name
        left_ref = stmt.table_alias or left_table
        right_table = join.table_name
        right_ref = join.alias or right_table
        
        # Get right table schema
        right_cols = self.catalog.get_columns(right_table)
        
        # Scan right table
        start_key = f"{right_table}:"
        end_key = f"{right_table}:~"
        right_data = self.engine.range_scan(start_key, end_key)
        
        # Parse right rows
        right_rows = []
        for key, value in right_data:
            if value == "DELETED" or key.startswith("__"):
                continue
            
            values = value.split("|")
            row = {}
            for i, col in enumerate(right_cols):
                if i < len(values):
                    row[col.name] = self._cast_value(values[i], col.type)
            right_rows.append(row)
        
        # Perform JOIN (nested loop join)
        result = []
        
        for left_row in left_rows:
            for right_row in right_rows:
                combined = {}
                ambiguous_cols: Set[str] = set()

                # Add left columns (qualified by table + alias, plus unqualified)
                for col_name, col_value in left_row.items():
                    combined[f"{left_table}.{col_name}"] = col_value
                    if left_ref != left_table:
                        combined[f"{left_ref}.{col_name}"] = col_value
                    combined[col_name] = col_value
                
                # Add right columns (qualified by table + alias; detect unqualified ambiguity)
                for col_name, col_value in right_row.items():
                    combined[f"{right_table}.{col_name}"] = col_value
                    if right_ref != right_table:
                        combined[f"{right_ref}.{col_name}"] = col_value

                    if col_name in combined:
                        ambiguous_cols.add(col_name)
                        # Remove unqualified ambiguous key so callers must qualify
                        combined.pop(col_name, None)
                    else:
                        combined[col_name] = col_value

                if ambiguous_cols:
                    combined["__ambiguous_cols__"] = ambiguous_cols
                
                # Check ON condition
                if self._evaluate_join_condition(join.on_condition, combined, left_table, right_table, left_ref, right_ref):
                    result.append(combined)
        
        return result
    
    def _evaluate_join_condition(
        self,
        expr: Expr,
        row: dict,
        left_table: str,
        right_table: str,
        left_ref: Optional[str] = None,
        right_ref: Optional[str] = None,
    ) -> bool:
        """Evaluate JOIN ON condition with strict column resolution"""
        if isinstance(expr, BinaryOp):
            left_val = self._get_join_expr_value(expr.left, row, left_table, right_table, left_ref, right_ref)
            right_val = self._get_join_expr_value(expr.right, row, left_table, right_table, left_ref, right_ref)
            
            if expr.op == "=":
                return left_val == right_val
            elif expr.op == "!=":
                return left_val != right_val
            elif expr.op == "<":
                return left_val < right_val
            elif expr.op == ">":
                return left_val > right_val
            elif expr.op == "<=":
                return left_val <= right_val
            elif expr.op == ">=":
                return left_val >= right_val
            elif expr.op == "AND":
                return left_val and right_val
            elif expr.op == "OR":
                return left_val or right_val
            else:
                raise RuntimeError(f"Unsupported operator: {expr.op}")
        
        return True
    
    def _get_join_expr_value(
        self,
        expr: Expr,
        row: dict,
        left_table: str,
        right_table: str,
        left_ref: Optional[str] = None,
        right_ref: Optional[str] = None,
    ):
        """Get expression value for JOIN with strict (SQL-like) resolution"""
        if isinstance(expr, ColumnRef):
            col_name = expr.name

            # Explicitly qualified reference
            if "." in col_name:
                if col_name in row:
                    return row[col_name]
                raise RuntimeError(f"Column not found in JOIN condition: {col_name}")

            # Unqualified reference: detect ambiguity first
            if col_name in row.get("__ambiguous_cols__", set()):
                raise RuntimeError(f"Ambiguous column in JOIN condition: {col_name}")

            # Try known qualification variants
            candidates = [
                f"{left_table}.{col_name}",
                f"{right_table}.{col_name}",
            ]
            if left_ref:
                candidates.append(f"{left_ref}.{col_name}")
            if right_ref:
                candidates.append(f"{right_ref}.{col_name}")

            values = [row[c] for c in candidates if c in row]
            if len(values) == 1:
                return values[0]
            if len(values) > 1:
                raise RuntimeError(f"Ambiguous column in JOIN condition: {col_name}")

            raise RuntimeError(f"Column not found in JOIN condition: {col_name}")
        
        elif isinstance(expr, Literal):
            return expr.value
        
        elif isinstance(expr, BinaryOp):
            left = self._get_join_expr_value(expr.left, row, left_table, right_table, left_ref, right_ref)
            right = self._get_join_expr_value(expr.right, row, left_table, right_table, left_ref, right_ref)
            
            if expr.op == "+":
                return left + right
            elif expr.op == "-":
                return left - right
            elif expr.op == "*":
                return left * right
            elif expr.op == "/":
                return left / right
            else:
                # For comparison operators, return the comparison result
                if expr.op == "=":
                    return left == right
                elif expr.op == "!=":
                    return left != right
                elif expr.op == "<":
                    return left < right
                elif expr.op == ">":
                    return left > right
                elif expr.op == "<=":
                    return left <= right
                elif expr.op == ">=":
                    return left >= right
        
        return None
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _cast_value(self, value: str, type_: str) -> Any:
        """Cast string value to appropriate type"""
        try:
            if type_ == "INT":
                return int(value)
            elif type_ == "FLOAT":
                return float(value)
            else:  # TEXT
                return value
        except (ValueError, TypeError):
            # If casting fails, return as string
            return value
    
    def _resolve_column_value(self, column: str, row: dict, strict_ambiguous: bool = False) -> Any:
        """Resolve column references, including qualified names and ambiguity checks."""
        if "." in column:
            return row.get(column)

        if strict_ambiguous and column in row.get("__ambiguous_cols__", set()):
            raise RuntimeError(f"Ambiguous column reference: {column}")

        return row.get(column)

    def _evaluate_expr(self, expr: Expr, row: dict) -> bool:
        """Evaluate WHERE clause expression against a row"""
        if isinstance(expr, BinaryOp):
            left = self._get_expr_value(expr.left, row)
            right = self._get_expr_value(expr.right, row)
            
            # Try to convert to numbers for comparison if both look numeric
            try:
                if isinstance(left, str) and left.replace(".", "").replace("-", "").isdigit():
                    left = float(left) if "." in left else int(left)
                if isinstance(right, str) and right.replace(".", "").replace("-", "").isdigit():
                    right = float(right) if "." in right else int(right)
            except (ValueError, AttributeError):
                pass
            
            op = expr.op.upper()
            if op == "=":
                return left == right
            elif op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
            elif op == "!=":
                return left != right
            elif op == "AND":
                return left and right
            elif op == "OR":
                return left or right
            else:
                raise RuntimeError(f"Unknown operator: {op}")
        
        elif isinstance(expr, ColumnRef):
            return self._resolve_column_value(expr.name, row, strict_ambiguous=True)
        
        elif isinstance(expr, Literal):
            return expr.value
        
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")
    
    def _get_expr_value(self, expr: Expr, row: dict) -> Any:
        """Get value of expression in context of a row"""
        if isinstance(expr, ColumnRef):
            return self._resolve_column_value(expr.name, row, strict_ambiguous=True)
        elif isinstance(expr, Literal):
            return expr.value
        elif isinstance(expr, BinaryOp):
            # For AND/OR in sub-expressions
            return self._evaluate_expr(expr, row)
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")
