"""Parse SQL before execution. Runtime authorization is an independent layer."""

import re
import sqlglot
from sqlglot import exp

from .config import Limits


class ValidationError(ValueError):
    pass


# Functions exposed to generated SQL. No extension loading, file I/O or PRAGMAs.
# The SQLite authorizer applies this list to ACTUAL runtime function names.
SAFE_FUNCTIONS = frozenset({
    "abs", "avg", "cast", "ceil", "ceiling", "char", "coalesce", "concat",
    "concat_ws", "count", "date", "datetime", "dense_rank", "first_value",
    "floor", "glob", "group_concat", "hex", "ifnull", "iif", "instr", "julianday",
    "lag", "last_value", "lead", "length", "like", "lower", "ltrim", "max",
    "min", "mod", "nth_value", "ntile", "nullif", "percent_rank", "pow", "power",
    "rank", "replace", "round", "row_number", "rtrim", "sign", "sqrt", "strftime",
    "substr", "substring", "sum", "time", "total", "trim", "typeof", "unicode",
    "unixepoch", "upper",
})


def extract_sql(response: str) -> str:
    """Accept plain SQL or one full SQL fence; never guess SQL out of prose."""
    text = response.strip()
    match = re.fullmatch(r"```(?:sql|sqlite)?\s*\n(.*?)\n```", text, re.S | re.I)
    return match.group(1).strip() if match else text


def validate_sql(sql: str, limits: Limits | None = None) -> str:
    """Return the ORIGINAL SQL after checking it. Do not rewrite its semantics."""
    limits = limits or Limits()
    if not isinstance(sql, str) or not sql.strip():
        raise ValidationError("Return one nonempty SQLite SELECT query")
    if len(sql) > limits.max_sql_chars or "\x00" in sql:
        raise ValidationError("Query length limit exceeded or NUL byte present")
    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except (sqlglot.errors.SqlglotError, RecursionError) as exc:
        raise ValidationError(f"SQL parse error: {str(exc)[:400]}") from exc
    statements = [node for node in statements if node is not None]
    if len(statements) != 1:
        raise ValidationError("Exactly one SQL statement is permitted")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValidationError("Only SELECT queries, including read-only CTEs, are permitted")
    forbidden = {
        "insert", "update", "delete", "create", "drop", "alter", "command", "pragma",
        "attach", "detach", "transaction", "commit", "rollback", "copy", "merge",
        "grant", "revoke", "into", "execute", "load_data", "lock", "use", "set",
    }
    nodes = list(tree.walk())
    if len(nodes) > limits.max_ast_nodes:
        raise ValidationError("Query AST is too large")
    for node in nodes:
        if node.key in {"currentdate", "currenttime", "currenttimestamp"}:
            raise ValidationError("Use an explicit reference date, not the current wall clock")
        if node.key in forbidden:
            raise ValidationError(f"Forbidden SQL operation: {node.key}")
        if isinstance(node, exp.Table):
            if not isinstance(node.this, exp.Identifier):
                raise ValidationError("Table-valued functions are not permitted")
            if node.catalog or (node.db and node.db.casefold() != "main"):
                raise ValidationError("Only the main database may be read")
            if node.name.casefold().startswith(("sqlite_", "pragma_")):
                raise ValidationError("SQLite metadata and PRAGMA tables are not query targets")
        if isinstance(node, exp.Anonymous) and node.name.casefold() not in SAFE_FUNCTIONS:
            raise ValidationError(f"Function is not approved: {node.name}")
        date_function = node.key in {"date", "time", "timetostr", "tsordstotimestamp"} or (
            isinstance(node, exp.Anonymous) and node.name.casefold() in {"date", "time", "datetime", "strftime", "julianday", "unixepoch"})
        if date_function:
            clock_literals = {literal.this.casefold() for literal in node.find_all(exp.Literal) if literal.is_string}
            if not list(node.iter_expressions()) or clock_literals.intersection({"now", "localtime", "utc"}):
                raise ValidationError("Use explicit, deterministic date inputs; clock/timezone modifiers are disabled")
        # Known functions can have different AST names (STRFTIME -> TimeToStr).
        # Their real SQLite names are checked again by the runtime authorizer.
    return sql.strip()
