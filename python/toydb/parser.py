"""
SQL Parser - Simple recursive descent parser for basic SQL statements
"""

import re
from typing import List, Optional, Any
from .ast_nodes import *


class ParseError(Exception):
    """Raised when SQL parsing fails"""
    pass


class SQLParser:
    """
    Simple SQL parser for ToyDB
    
    Supports:
    - CREATE TABLE table_name (col1 TYPE, col2 TYPE, ...)
    - INSERT INTO table_name VALUES (val1, val2, ...)
    - SELECT * FROM table_name
    - SELECT col1, col2 FROM table_name WHERE condition
    - SELECT ... ORDER BY col
    - SELECT ... LIMIT n
    """
    
    def __init__(self, sql: str):
        self.sql = sql.strip()
        self.tokens = self._tokenize(sql)
        self.pos = 0
    
    def _tokenize(self, sql: str) -> List[str]:
        """
        Tokenize SQL string into words and symbols
        
        Handles:
        - Keywords (SELECT, FROM, WHERE, etc.)
        - Identifiers (table names, column names)
        - Literals (strings, numbers)
        - Operators (=, >, <, etc.)
        - Punctuation (,, (, ), ;)
        """
        # Pattern: strings | numbers | identifiers | operators | punctuation
        pattern = r"'[^']*'|\"[^\"]*\"|\d+\.?\d*|\w+|>=|<=|!=|[=><(),;*]"
        tokens = re.findall(pattern, sql, re.IGNORECASE)
        return [t for t in tokens if t.strip()]  # Remove empty
    
    def current(self) -> Optional[str]:
        """Get current token without advancing"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def advance(self) -> str:
        """Consume and return current token"""
        token = self.current()
        if token is None:
            raise ParseError("Unexpected end of input")
        self.pos += 1
        return token
    
    def peek(self, offset: int = 1) -> Optional[str]:
        """Look ahead at token without consuming"""
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return None
    
    def expect(self, expected: str) -> str:
        """Consume token and verify it matches expected"""
        token = self.advance()
        if token.upper() != expected.upper():
            raise ParseError(f"Expected '{expected}', got '{token}'")
        return token
    
    def match(self, *keywords: str) -> bool:
        """Check if current token matches any of the keywords"""
        current = self.current()
        if current is None:
            return False
        return current.upper() in [k.upper() for k in keywords]
    
    def parse(self) -> ASTNode:
        """Parse SQL statement and return AST"""
        if not self.tokens:
            raise ParseError("Empty SQL statement")
        
        keyword = self.current().upper()
        
        if keyword == "EXPLAIN":
            # EXPLAIN <query>
            self.advance()  # Consume EXPLAIN
            inner_query = self.parse()
            return ExplainStmt(inner_query)
        elif keyword == "CREATE":
            # Could be CREATE TABLE or CREATE INDEX
            next_keyword = self.peek()
            if next_keyword and next_keyword.upper() == "TABLE":
                return self.parse_create_table()
            elif next_keyword and next_keyword.upper() == "INDEX":
                return self.parse_create_index()
            else:
                raise ParseError(f"Expected TABLE or INDEX after CREATE")
        elif keyword == "DROP":
            # Could be DROP TABLE or DROP INDEX
            next_keyword = self.peek()
            if next_keyword and next_keyword.upper() == "TABLE":
                return self.parse_drop_table()
            elif next_keyword and next_keyword.upper() == "INDEX":
                return self.parse_drop_index()
            else:
                raise ParseError(f"Expected TABLE or INDEX after DROP")
        elif keyword == "ALTER":
            return self.parse_alter_table()
        elif keyword == "INSERT":
            return self.parse_insert()
        elif keyword == "SELECT":
            return self.parse_select()
        elif keyword == "UPDATE":
            return self.parse_update()
        elif keyword == "DELETE":
            return self.parse_delete()
        else:
            raise ParseError(f"Unsupported statement: {keyword}")
    
    # ============================================================
    # DDL Parsing
    # ============================================================
    
    def parse_create_table(self) -> CreateTableStmt:
        """
        Parse: CREATE TABLE table_name (col1 TYPE, col2 TYPE, ...)
        """
        self.expect("CREATE")
        self.expect("TABLE")
        
        table_name = self.advance()
        
        self.expect("(")
        
        columns = []
        while not self.match(")"):
            col_name = self.advance()
            col_type = self.advance()
            
            columns.append(ColumnDef(col_name, col_type.upper()))
            
            if self.match(","):
                self.advance()  # Consume comma
        
        self.expect(")")
        
        return CreateTableStmt(table_name, columns)
    
    def parse_drop_table(self) -> DropTableStmt:
        """
        Parse: DROP TABLE table_name
        """
        self.expect("DROP")
        self.expect("TABLE")
        
        table_name = self.advance()
        
        return DropTableStmt(table_name)
    
    def parse_alter_table(self) -> AlterTableStmt:
        """
        Parse: ALTER TABLE table_name ADD COLUMN col_name TYPE
        """
        self.expect("ALTER")
        self.expect("TABLE")
        
        table_name = self.advance()
        
        self.expect("ADD")
        self.expect("COLUMN")
        
        col_name = self.advance()
        col_type = self.advance()
        
        return AlterTableStmt(
            table_name, 
            "ADD_COLUMN",
            ColumnDef(col_name, col_type.upper())
        )
    
    def parse_create_index(self) -> CreateIndexStmt:
        """
        Parse: CREATE INDEX index_name ON table_name (column_name)
        """
        self.expect("CREATE")
        self.expect("INDEX")
        
        index_name = self.advance()
        
        self.expect("ON")
        
        table_name = self.advance()
        
        self.expect("(")
        column_name = self.advance()
        self.expect(")")
        
        return CreateIndexStmt(index_name, table_name, column_name)
    
    def parse_drop_index(self) -> DropIndexStmt:
        """
        Parse: DROP INDEX index_name
        """
        self.expect("DROP")
        self.expect("INDEX")
        
        index_name = self.advance()
        
        return DropIndexStmt(index_name)
    
    # ============================================================
    # DML Parsing
    # ============================================================
    
    def parse_insert(self) -> InsertStmt:
        """
        Parse: INSERT INTO table_name VALUES (val1, val2, ...)
        """
        self.expect("INSERT")
        self.expect("INTO")
        
        table_name = self.advance()
        
        self.expect("VALUES")
        self.expect("(")
        
        values = []
        while not self.match(")"):
            value = self.parse_literal()
            values.append(value)
            
            if self.match(","):
                self.advance()
        
        self.expect(")")
        
        return InsertStmt(table_name, values)
    
    def parse_select(self) -> SelectStmt:
        """
        Parse: SELECT columns FROM table 
               [JOIN table ON condition]
               [WHERE condition] 
               [GROUP BY columns]
               [HAVING condition]
               [ORDER BY col] 
               [LIMIT n]
        """
        self.expect("SELECT")
        
        # Parse columns (including aggregate functions)
        columns = []
        if self.match("*"):
            columns.append("*")
            self.advance()
        else:
            while True:
                col_expr = self._parse_column_expression()
                columns.append(col_expr)
                
                if not self.match(","):
                    break
                self.advance()  # Consume comma
        
        self.expect("FROM")
        table_name = self.advance()
        
        # Optional JOIN
        join = None
        if self.match("INNER", "LEFT", "RIGHT", "JOIN"):
            join = self.parse_join()
        
        # Optional WHERE clause
        where = None
        if self.match("WHERE"):
            self.advance()
            where = self.parse_expression()
        
        # Optional GROUP BY
        group_by = None
        if self.match("GROUP"):
            self.advance()
            self.expect("BY")
            group_by = []
            while True:
                group_by.append(self.advance())
                if not self.match(","):
                    break
                self.advance()
        
        # Optional HAVING
        having = None
        if self.match("HAVING"):
            self.advance()
            having = self.parse_expression()
        
        # Optional ORDER BY
        order_by = None
        if self.match("ORDER"):
            self.advance()  # ORDER
            self.expect("BY")
            order_by = self.advance()
        
        # Optional LIMIT
        limit = None
        if self.match("LIMIT"):
            self.advance()
            limit = int(self.advance())
        
        return SelectStmt(columns, table_name, where, order_by, limit, join, group_by, having)
    
    def _parse_column_expression(self) -> str:
        """Parse a column expression (regular column, qualified column, or aggregate function)"""
        # Check for aggregate function
        if self.match("COUNT", "SUM", "AVG", "MIN", "MAX"):
            func_name = self.advance()
            self.expect("(")
            if self.match("*"):
                self.advance()
                col_expr = f"{func_name}(*)"
            else:
                arg = self.advance()
                # Check for qualified argument (table.column)
                if self.match("."):
                    self.advance()
                    arg = arg + "." + self.advance()
                col_expr = f"{func_name}({arg})"
            self.expect(")")
            return col_expr
        else:
            # Regular or qualified column
            col = self.advance()
            # Check for qualified column (table.column)
            if self.match("."):
                self.advance()  # Consume dot
                col = col + "." + self.advance()
            return col
    
    def parse_join(self) -> 'JoinClause':
        """Parse JOIN clause"""
        # Handle INNER JOIN, LEFT JOIN, etc.
        join_type = "INNER"
        if self.match("INNER", "LEFT", "RIGHT"):
            join_type = self.advance().upper()
        
        self.expect("JOIN")
        join_table = self.advance()
        
        self.expect("ON")
        on_condition = self.parse_expression()
        
        return JoinClause(join_type, join_table, on_condition)
    
    def parse_update(self) -> 'UpdateStmt':
        """
        Parse: UPDATE table SET col1=val1, col2=val2 WHERE condition
        """
        self.expect("UPDATE")
        table_name = self.advance()
        
        self.expect("SET")
        
        assignments = {}
        while True:
            col = self.advance()
            self.expect("=")
            val = self.parse_literal()
            assignments[col] = val
            
            if not self.match(","):
                break
            self.advance()
        
        # Optional WHERE
        where = None
        if self.match("WHERE"):
            self.advance()
            where = self.parse_expression()
        
        return UpdateStmt(table_name, assignments, where)
    
    def parse_delete(self) -> 'DeleteStmt':
        """
        Parse: DELETE FROM table WHERE condition
        """
        self.expect("DELETE")
        self.expect("FROM")
        table_name = self.advance()
        
        # Optional WHERE
        where = None
        if self.match("WHERE"):
            self.advance()
            where = self.parse_expression()
        
        return DeleteStmt(table_name, where)
    
    # ============================================================
    # Expression Parsing
    # ============================================================
    
    def parse_expression(self) -> Expr:
        """Parse WHERE clause expression"""
        return self.parse_or_expr()
    
    def parse_or_expr(self) -> Expr:
        """Parse OR expression"""
        left = self.parse_and_expr()
        
        while self.match("OR"):
            op = self.advance()
            right = self.parse_and_expr()
            left = BinaryOp(left, op.upper(), right)
        
        return left
    
    def parse_and_expr(self) -> Expr:
        """Parse AND expression"""
        left = self.parse_comparison()
        
        while self.match("AND"):
            op = self.advance()
            right = self.parse_comparison()
            left = BinaryOp(left, op.upper(), right)
        
        return left
    
    def parse_comparison(self) -> Expr:
        """Parse comparison: col = val, col > val, etc."""
        left = self.parse_primary()
        
        if self.match("=", ">", "<", ">=", "<=", "!="):
            op = self.advance()
            right = self.parse_primary()
            return BinaryOp(left, op, right)
        
        return left
    
    def parse_primary(self) -> Expr:
        """Parse primary expression (column or literal)"""
        token = self.current()
        
        if token is None:
            raise ParseError("Unexpected end of expression")
        
        # String literal
        if token.startswith("'") or token.startswith('"'):
            return Literal(self.parse_literal())
        
        # Number literal
        if token.replace(".", "").isdigit():
            return Literal(self.parse_literal())
        
        # Column reference
        return ColumnRef(self.advance())
    
    def parse_literal(self) -> Any:
        """Parse literal value (string or number)"""
        token = self.advance()
        
        # String literal
        if token.startswith("'") or token.startswith('"'):
            return token[1:-1]  # Remove quotes
        
        # Number literal
        if "." in token:
            return float(token)
        else:
            try:
                return int(token)
            except ValueError:
                return token  # Return as string if not a number


# ============================================================
# Convenience function
# ============================================================

def parse_sql(sql: str) -> ASTNode:
    """
    Parse SQL string and return AST
    
    Example:
        >>> ast = parse_sql("SELECT * FROM users WHERE age > 25")
        >>> print(ast)
    """
    parser = SQLParser(sql)
    return parser.parse()
