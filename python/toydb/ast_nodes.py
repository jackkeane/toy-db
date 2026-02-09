"""
AST (Abstract Syntax Tree) node definitions for SQL queries
"""

from dataclasses import dataclass
from typing import List, Optional, Any, Dict


@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    pass


# ============================================================
# Data Definition Language (DDL)
# ============================================================

@dataclass
class ColumnDef:
    """Column definition: name and type"""
    name: str
    type: str  # INT, TEXT, FLOAT, etc.


@dataclass
class CreateTableStmt(ASTNode):
    """CREATE TABLE statement"""
    table_name: str
    columns: List[ColumnDef]


@dataclass
class DropTableStmt(ASTNode):
    """DROP TABLE statement"""
    table_name: str


@dataclass
class AlterTableStmt(ASTNode):
    """ALTER TABLE statement"""
    table_name: str
    action: str  # "ADD_COLUMN"
    column: Optional[ColumnDef] = None


@dataclass
class CreateIndexStmt(ASTNode):
    """CREATE INDEX statement"""
    index_name: str
    table_name: str
    column_name: str


@dataclass
class DropIndexStmt(ASTNode):
    """DROP INDEX statement"""
    index_name: str


@dataclass
class ExplainStmt(ASTNode):
    """EXPLAIN query (show query plan)"""
    query: ASTNode  # The query to explain


# ============================================================
# Data Manipulation Language (DML)
# ============================================================

@dataclass
class InsertStmt(ASTNode):
    """INSERT INTO table VALUES (...)"""
    table_name: str
    values: List[Any]  # List of values to insert


@dataclass
class SelectStmt(ASTNode):
    """SELECT columns FROM table WHERE condition"""
    columns: List[str]  # Column names, aggregate functions, or ['*']
    table_name: str
    where: Optional['Expr'] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None
    join: Optional['JoinClause'] = None
    group_by: Optional[List[str]] = None
    having: Optional['Expr'] = None


@dataclass
class JoinClause:
    """JOIN clause"""
    join_type: str  # INNER, LEFT, RIGHT, OUTER
    table_name: str
    on_condition: 'Expr'


@dataclass
class UpdateStmt(ASTNode):
    """UPDATE table SET col=val WHERE condition"""
    table_name: str
    assignments: Dict[str, Any]  # column -> new value
    where: Optional['Expr'] = None


@dataclass
class DeleteStmt(ASTNode):
    """DELETE FROM table WHERE condition"""
    table_name: str
    where: Optional['Expr'] = None


# ============================================================
# Expressions
# ============================================================

@dataclass
class Expr(ASTNode):
    """Base expression class"""
    pass


@dataclass
class ColumnRef(Expr):
    """Reference to a column"""
    name: str


@dataclass
class Literal(Expr):
    """Literal value (string, number, etc.)"""
    value: Any


@dataclass
class BinaryOp(Expr):
    """Binary operation: left OP right"""
    left: Expr
    op: str  # =, >, <, >=, <=, !=, AND, OR
    right: Expr


@dataclass
class FunctionCall(Expr):
    """Function call (e.g., COUNT(*), SUM(salary))"""
    function_name: str  # COUNT, SUM, AVG, MIN, MAX
    argument: Optional[Expr] = None  # None for COUNT(*)


# ============================================================
# Utility functions
# ============================================================

def ast_to_string(node: ASTNode, indent: int = 0) -> str:
    """Convert AST to readable string representation"""
    prefix = "  " * indent
    
    if isinstance(node, CreateTableStmt):
        cols = ", ".join(f"{c.name} {c.type}" for c in node.columns)
        return f"{prefix}CREATE TABLE {node.table_name} ({cols})"
    
    elif isinstance(node, InsertStmt):
        vals = ", ".join(repr(v) for v in node.values)
        return f"{prefix}INSERT INTO {node.table_name} VALUES ({vals})"
    
    elif isinstance(node, SelectStmt):
        cols = ", ".join(node.columns)
        result = f"{prefix}SELECT {cols} FROM {node.table_name}"
        
        if node.where:
            result += f" WHERE {expr_to_string(node.where)}"
        
        if node.order_by:
            result += f" ORDER BY {node.order_by}"
        
        if node.limit:
            result += f" LIMIT {node.limit}"
        
        return result
    
    elif isinstance(node, ColumnRef):
        return f"{prefix}{node.name}"
    
    elif isinstance(node, Literal):
        return f"{prefix}{repr(node.value)}"
    
    elif isinstance(node, BinaryOp):
        left = expr_to_string(node.left)
        right = expr_to_string(node.right)
        return f"{prefix}({left} {node.op} {right})"
    
    else:
        return f"{prefix}{node}"


def expr_to_string(expr: Expr) -> str:
    """Convert expression to string"""
    if isinstance(expr, ColumnRef):
        return expr.name
    elif isinstance(expr, Literal):
        return repr(expr.value)
    elif isinstance(expr, BinaryOp):
        left = expr_to_string(expr.left)
        right = expr_to_string(expr.right)
        return f"({left} {expr.op} {right})"
    else:
        return str(expr)
