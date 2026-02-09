"""
Aggregation helper functions for GROUP BY and aggregate functions
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict


def parse_aggregate_function(col_expr: str) -> Tuple[str, str]:
    """
    Parse aggregate function expression
    
    Returns: (function_name, column_name) or (None, col_expr)
    
    Examples:
        "COUNT(*)" -> ("COUNT", "*")
        "SUM(salary)" -> ("SUM", "salary")
        "name" -> (None, "name")
    """
    col_expr = col_expr.strip()
    
    for func in ["COUNT", "SUM", "AVG", "MIN", "MAX"]:
        if col_expr.upper().startswith(func + "("):
            # Extract argument
            start = col_expr.index("(") + 1
            end = col_expr.rindex(")")
            arg = col_expr[start:end].strip()
            return (func, arg)
    
    return (None, col_expr)


def group_rows(rows: List[Dict], group_by_cols: List[str]) -> Dict[Tuple, List[Dict]]:
    """
    Group rows by specified columns
    
    Returns: Dict mapping group key -> list of rows in that group
    """
    groups = defaultdict(list)
    
    for row in rows:
        # Create group key from group_by columns
        key = tuple(row.get(col) for col in group_by_cols)
        groups[key].append(row)
    
    return dict(groups)


def compute_aggregate(func_name: str, column: str, rows: List[Dict]) -> Any:
    """
    Compute aggregate function over a group of rows
    
    Args:
        func_name: COUNT, SUM, AVG, MIN, MAX
        column: Column name or "*" for COUNT(*)
        rows: List of row dicts in this group
    
    Returns:
        Aggregated value
    """
    if func_name == "COUNT":
        if column == "*":
            return len(rows)
        else:
            # COUNT(col) - count non-null values
            return sum(1 for row in rows if row.get(column) is not None)
    
    # For other functions, extract values
    values = []
    for row in rows:
        val = row.get(column)
        if val is not None:
            # Convert to number if needed
            if isinstance(val, str) and val.replace(".", "").replace("-", "").isdigit():
                val = float(val) if "." in val else int(val)
            values.append(val)
    
    if not values:
        return None
    
    if func_name == "SUM":
        return sum(values)
    elif func_name == "AVG":
        return sum(values) / len(values)
    elif func_name == "MIN":
        return min(values)
    elif func_name == "MAX":
        return max(values)
    else:
        raise ValueError(f"Unknown aggregate function: {func_name}")


def apply_aggregates(
    rows: List[Dict],
    select_columns: List[str],
    group_by_cols: List[str] = None
) -> List[Tuple]:
    """
    Apply aggregate functions and grouping
    
    Args:
        rows: Input rows
        select_columns: SELECT column expressions (may include aggregates)
        group_by_cols: GROUP BY columns (None if no grouping)
    
    Returns:
        List of result tuples
    """
    # Parse which columns are aggregates
    col_info = []
    has_aggregates = False
    
    for col_expr in select_columns:
        func, arg = parse_aggregate_function(col_expr)
        col_info.append((col_expr, func, arg))
        if func:
            has_aggregates = True
    
    # No aggregates and no GROUP BY? Just return rows as-is
    if not has_aggregates and not group_by_cols:
        result = []
        for row in rows:
            result_row = []
            for col_expr, func, arg in col_info:
                result_row.append(row.get(arg))
            result.append(tuple(result_row))
        return result
    
    # Group rows if GROUP BY specified
    if group_by_cols:
        groups = group_rows(rows, group_by_cols)
    else:
        # No GROUP BY but has aggregates -> single group (entire dataset)
        groups = {(): rows}
    
    # Compute aggregates for each group
    result = []
    for group_key, rows_in_group in groups.items():
        result_row = []
        
        for col_expr, func, arg in col_info:
            if func:
                # Aggregate function
                value = compute_aggregate(func, arg, rows_in_group)
            else:
                # Regular column (must be in GROUP BY)
                if group_by_cols and arg in group_by_cols:
                    # Get value from first row in group (all same for GROUP BY cols)
                    value = rows_in_group[0].get(arg) if rows_in_group else None
                else:
                    # Column not in GROUP BY - use first value
                    value = rows_in_group[0].get(arg) if rows_in_group else None
            
            result_row.append(value)
        
        result.append(tuple(result_row))
    
    return result
