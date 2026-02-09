"""
Query Planner - Cost-based query optimization

Generates optimal execution plans for SQL queries by:
- Analyzing available indexes
- Estimating costs for different access methods
- Choosing between table scan vs index scan
- Collecting and using statistics
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from .ast_nodes import *
from .catalog import Catalog


@dataclass
class PlanNode:
    """Base class for query plan nodes"""
    cost: float = 0.0
    estimated_rows: int = 0


@dataclass
class TableScanNode(PlanNode):
    """Full table scan"""
    table_name: str = ""
    
    def __str__(self):
        return f"TableScan({self.table_name}) [cost={self.cost:.1f}, rows={self.estimated_rows}]"


@dataclass
class IndexScanNode(PlanNode):
    """Index-based scan"""
    table_name: str = ""
    index_name: str = ""
    column_name: str = ""
    condition: Optional[Expr] = None
    
    def __str__(self):
        cond = f" WHERE {expr_to_string(self.condition)}" if self.condition else ""
        return f"IndexScan({self.table_name}, {self.index_name}){cond} [cost={self.cost:.1f}, rows={self.estimated_rows}]"


@dataclass
class FilterNode(PlanNode):
    """Filter (WHERE clause)"""
    child: Optional[PlanNode] = None
    condition: Optional[Expr] = None
    selectivity: float = 0.1  # Estimated fraction of rows passing filter
    
    def __str__(self):
        return f"Filter({expr_to_string(self.condition)}) [selectivity={self.selectivity:.2f}, rows={self.estimated_rows}]\n  {self.child}"


@dataclass
class ProjectNode(PlanNode):
    """Projection (SELECT columns)"""
    child: Optional[PlanNode] = None
    columns: List[str] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = []
    
    def __str__(self):
        cols = ", ".join(self.columns)
        return f"Project({cols})\n  {self.child}"


@dataclass
class SortNode(PlanNode):
    """Sorting (ORDER BY)"""
    child: Optional[PlanNode] = None
    column: str = ""
    
    def __str__(self):
        return f"Sort({self.column})\n  {self.child}"


@dataclass
class LimitNode(PlanNode):
    """Limit results"""
    child: Optional[PlanNode] = None
    limit: int = 0
    
    def __str__(self):
        return f"Limit({self.limit})\n  {self.child}"


class QueryPlanner:
    """
    Cost-based query planner
    
    Responsibilities:
    - Analyze SELECT queries
    - Choose optimal access method (table scan vs index scan)
    - Estimate costs and cardinalities
    - Generate execution plan
    """
    
    # Cost parameters (arbitrary units)
    COST_TABLE_SCAN_PER_ROW = 1.0
    COST_INDEX_SEEK = 10.0  # Cost to position in index
    COST_INDEX_SCAN_PER_ROW = 0.5  # Cheaper than table scan (no parsing)
    COST_FILTER_PER_ROW = 0.1
    COST_SORT_PER_ROW = 2.0  # O(n log n) but simplified
    
    def __init__(self, catalog: Catalog, storage_engine):
        self.catalog = catalog
        self.engine = storage_engine
    
    def plan(self, stmt: SelectStmt) -> PlanNode:
        """
        Generate optimal query plan for SELECT statement
        
        Steps:
        1. Get table statistics
        2. Analyze WHERE clause for index opportunities
        3. Choose access method (table scan vs index scan)
        4. Add filter node if needed
        5. Add sort node if ORDER BY
        6. Add limit node if LIMIT
        7. Add projection node for SELECT columns
        """
        # Get table statistics
        stats = self.catalog.get_stats(stmt.table_name)
        total_rows = stats.get("rows", 0)
        
        # If no stats, estimate by counting
        if total_rows == 0:
            total_rows = self._estimate_row_count(stmt.table_name)
            self.catalog.update_stats(stmt.table_name, total_rows)
        
        # Choose access method
        scan_node = self._choose_access_method(stmt, total_rows)
        
        # Apply filters (if WHERE clause not already handled by index)
        plan = scan_node
        if stmt.where and not isinstance(scan_node, IndexScanNode):
            # Add filter node
            selectivity = self._estimate_selectivity(stmt.where)
            plan = FilterNode(
                child=scan_node,
                condition=stmt.where,
                selectivity=selectivity,
                cost=scan_node.cost + (scan_node.estimated_rows * self.COST_FILTER_PER_ROW),
                estimated_rows=int(scan_node.estimated_rows * selectivity)
            )
        
        # Apply ORDER BY
        if stmt.order_by:
            plan = SortNode(
                child=plan,
                column=stmt.order_by,
                cost=plan.cost + (plan.estimated_rows * self.COST_SORT_PER_ROW),
                estimated_rows=plan.estimated_rows
            )
        
        # Apply LIMIT
        if stmt.limit:
            limited_rows = min(stmt.limit, plan.estimated_rows)
            plan = LimitNode(
                child=plan,
                limit=stmt.limit,
                cost=plan.cost * (limited_rows / max(plan.estimated_rows, 1)),
                estimated_rows=limited_rows
            )
        
        # Apply projection (SELECT columns)
        plan = ProjectNode(
            child=plan,
            columns=stmt.columns,
            cost=plan.cost,
            estimated_rows=plan.estimated_rows
        )
        
        return plan
    
    def _choose_access_method(self, stmt: SelectStmt, total_rows: int) -> PlanNode:
        """
        Choose between table scan and index scan
        
        Logic:
        - If no WHERE clause, use table scan
        - If WHERE has condition on indexed column, consider index scan
        - Compare costs and choose cheaper option
        """
        # Default: table scan
        table_scan = TableScanNode(
            table_name=stmt.table_name,
            cost=total_rows * self.COST_TABLE_SCAN_PER_ROW,
            estimated_rows=total_rows
        )
        
        # No WHERE clause? Must use table scan
        if not stmt.where:
            return table_scan
        
        # Check if WHERE clause can use an index
        index_option = self._find_index_for_condition(stmt.table_name, stmt.where)
        
        if not index_option:
            # No applicable index
            return table_scan
        
        index_name, column_name, estimated_rows = index_option
        
        # Estimate index scan cost
        index_scan_cost = (
            self.COST_INDEX_SEEK +
            estimated_rows * self.COST_INDEX_SCAN_PER_ROW
        )
        
        index_scan = IndexScanNode(
            table_name=stmt.table_name,
            index_name=index_name,
            column_name=column_name,
            condition=stmt.where,
            cost=index_scan_cost,
            estimated_rows=estimated_rows
        )
        
        # Choose cheaper option
        if index_scan_cost < table_scan.cost:
            return index_scan
        else:
            return table_scan
    
    def _find_index_for_condition(
        self, 
        table_name: str, 
        condition: Expr
    ) -> Optional[tuple]:
        """
        Find an index that can be used for the WHERE condition
        
        Returns:
            (index_name, column_name, estimated_rows) or None
        """
        # Get indexes for this table
        indexes = self.catalog.get_indexes(table_name)
        
        if not indexes:
            return None
        
        # Simple heuristic: look for equality condition on indexed column
        if isinstance(condition, BinaryOp):
            if condition.op == "=" and isinstance(condition.left, ColumnRef):
                col_name = condition.left.name
                
                # Check if this column has an index
                for idx in indexes:
                    if idx["column"] == col_name:
                        # Estimate: equality matches ~1% of rows (arbitrary)
                        stats = self.catalog.get_stats(table_name)
                        total_rows = stats.get("rows", 100)
                        estimated_rows = max(1, int(total_rows * 0.01))
                        
                        return (idx["name"], col_name, estimated_rows)
            
            # Range condition (>, <, >=, <=)
            elif condition.op in [">", "<", ">=", "<="] and isinstance(condition.left, ColumnRef):
                col_name = condition.left.name
                
                for idx in indexes:
                    if idx["column"] == col_name:
                        # Estimate: range matches ~30% of rows
                        stats = self.catalog.get_stats(table_name)
                        total_rows = stats.get("rows", 100)
                        estimated_rows = max(1, int(total_rows * 0.3))
                        
                        return (idx["name"], col_name, estimated_rows)
        
        return None
    
    def _estimate_selectivity(self, condition: Expr) -> float:
        """
        Estimate fraction of rows that pass the filter
        
        Simple heuristics:
        - Equality (=): 0.01 (1%)
        - Inequality (!=): 0.99
        - Range (>, <, >=, <=): 0.33 (33%)
        - AND: multiply selectivities
        - OR: add selectivities (capped at 1.0)
        """
        if isinstance(condition, BinaryOp):
            if condition.op == "=":
                return 0.01
            elif condition.op == "!=":
                return 0.99
            elif condition.op in [">", "<", ">=", "<="]:
                return 0.33
            elif condition.op == "AND":
                left_sel = self._estimate_selectivity(condition.left)
                right_sel = self._estimate_selectivity(condition.right)
                return left_sel * right_sel
            elif condition.op == "OR":
                left_sel = self._estimate_selectivity(condition.left)
                right_sel = self._estimate_selectivity(condition.right)
                return min(1.0, left_sel + right_sel)
        
        return 0.1  # Default: 10%
    
    def _estimate_row_count(self, table_name: str) -> int:
        """
        Estimate number of rows by counting
        
        This is expensive, so results should be cached in catalog stats.
        """
        start_key = f"{table_name}:"
        end_key = f"{table_name}:~"
        
        try:
            results = self.engine.range_scan(start_key, end_key)
            return len(results)
        except:
            return 0


def plan_to_string(plan: PlanNode, indent: int = 0) -> str:
    """Pretty-print query plan"""
    prefix = "  " * indent
    result = prefix + str(plan).replace("\n", f"\n{prefix}")
    return result
