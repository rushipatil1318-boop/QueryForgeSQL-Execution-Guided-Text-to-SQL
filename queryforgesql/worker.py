"""One database request per short-lived process. Never import a model here.

This is process separation with resource limits, not a complete OS sandbox.
Use the documented container boundary for deployment with hostile inputs.
"""

import base64
import json
import math
from pathlib import Path
import sqlite3
import sys
import time

from .config import Limits
from .validation import SAFE_FUNCTIONS, validate_sql


def apply_os_limits(limits: Limits) -> dict:
    applied = {"process_address_space": False, "process_cpu": False}
    if sys.platform.startswith("linux"):
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (limits.process_memory_mb * 1048576,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        applied = {"process_address_space": True, "process_cpu": True}
    return applied


def open_readonly(path: Path, limits: Limits) -> sqlite3.Connection:
    if not path.is_file() or path.suffix.casefold() not in {".sqlite", ".db"}:
        raise ValueError("An existing .sqlite or .db snapshot is required")
    # Immutable is valid only for OFFLINE snapshots. Reject active journal files.
    if any(Path(str(path) + ending).exists() for ending in ("-wal", "-journal")):
        raise ValueError("Use an offline database snapshot without WAL/journal files")
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=0.1)
    con.enable_load_extension(False)
    con.execute("PRAGMA query_only=ON")
    con.execute("PRAGMA trusted_schema=OFF")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA mmap_size=0")
    con.execute("PRAGMA cache_size=-2048")
    requested = limits.sqlite_heap_mb * 1048576
    heap = con.execute(f"PRAGMA hard_heap_limit={requested}").fetchone()
    if not heap or not 0 < heap[0] <= requested:
        con.close()
        raise ValueError("This SQLite build cannot enforce hard_heap_limit")
    for category, value in (
        (sqlite3.SQLITE_LIMIT_LENGTH, min(1000000, limits.max_result_bytes)),
        (sqlite3.SQLITE_LIMIT_SQL_LENGTH, limits.max_sql_chars * 4),
        (sqlite3.SQLITE_LIMIT_COLUMN, 256),
        (sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 100),
        (sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 10),
        (sqlite3.SQLITE_LIMIT_ATTACHED, 0),
        (sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 0),
        (sqlite3.SQLITE_LIMIT_LIKE_PATTERN_LENGTH, 1000),
        (sqlite3.SQLITE_LIMIT_TRIGGER_DEPTH, 0),
    ):
        con.setlimit(category, value)
    return con


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def inspect_schema(con: sqlite3.Connection) -> dict:
    """Read schema only. Never send database rows or gold SQL to the model."""
    rows = con.execute(
        "SELECT name, sql FROM sqlite_schema WHERE type='table' ORDER BY name"
    ).fetchall()
    tables = {}
    for name, ddl in rows:
        if name.casefold().startswith("sqlite_"):
            continue
        if not ddl or "CREATE VIRTUAL TABLE" in ddl.upper():
            continue
        if len(tables) >= 150:
            raise ValueError("Schema table budget exceeded")
        columns = [
            {"name": row[1], "type": row[2], "primary_key": bool(row[5])}
            for row in con.execute(f"PRAGMA table_info({quote_identifier(name)})")
        ]
        foreign_keys = [
            {"column": row[3], "target_table": row[2], "target_column": row[4]}
            for row in con.execute(f"PRAGMA foreign_key_list({quote_identifier(name)})")
        ]
        tables[name] = {"columns": columns, "foreign_keys": foreign_keys}
    if not tables:
        raise ValueError("Database has no approved ordinary tables")
    return {"tables": tables}


def make_authorizer(schema: dict):
    tables = {name.casefold(): {c["name"].casefold() for c in table["columns"]}
              for name, table in schema["tables"].items()}

    def authorize(action, arg1, arg2, database, source):
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            table = (arg1 or "").casefold()
            column = (arg2 or "").casefold()
            # SQLite reports database=None for the zero-column COUNT(*) fast path.
            # No attached/temp databases can be created in this connection.
            approved_database = database == "main" or (database is None and not column)
            if approved_database and table in tables and (not column or column in tables[table]):
                return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").casefold() in SAFE_FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    return authorize


def json_cell(value):
    if isinstance(value, bytes):
        return {"blob_base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_float": str(value)}
    return value


def handle_request(request: dict) -> dict:
    started = time.perf_counter()
    limits = Limits(**request.get("limits", {}))
    applied = apply_os_limits(limits)
    deadline = time.perf_counter() + limits.wall_seconds
    con = open_readonly(Path(request["db_path"]), limits)
    try:
        con.set_progress_handler(lambda: int(time.perf_counter() > deadline), 1000)
        schema = inspect_schema(con)
        if request["action"] == "schema":
            return {"status": "ok", "schema": schema, "limits_applied": applied}
        sql = validate_sql(request["sql"], limits)
        con.set_authorizer(make_authorizer(schema))
        cursor = con.execute(sql)
        columns = [description[0] for description in cursor.description]
        rows, result_bytes = [], 0
        for row in cursor:
            if len(rows) >= limits.max_rows:
                return {"status": "row_limit", "error": "Result exceeds max_rows; no partial result is scored"}
            row = [json_cell(value) for value in row]
            result_bytes += len(json.dumps(row, ensure_ascii=True).encode("utf-8"))
            if result_bytes > limits.max_result_bytes:
                return {"status": "byte_limit", "error": "Result byte budget exceeded; no partial result is scored"}
            rows.append(row)
        return {"status": "ok", "columns": columns, "rows": rows,
                "row_count": len(rows), "sqlite_heap_limit_bytes": limits.sqlite_heap_mb * 1048576,
                "limits_applied": applied, "execution_seconds": time.perf_counter() - started}
    finally:
        con.close()


def main():
    try:
        request = json.loads(sys.stdin.buffer.read(200000))
        result = handle_request(request)
    except sqlite3.Error as exc:
        code = getattr(exc, "sqlite_errorname", "unknown")
        status = {
            "SQLITE_INTERRUPT": "timeout", "SQLITE_NOMEM": "resource_limit",
            "SQLITE_TOOBIG": "resource_limit", "SQLITE_AUTH": "authorization_error",
            "SQLITE_ERROR": "sql_error",
        }.get(code, "error")
        result = {"status": status, "error_type": type(exc).__name__,
                  "sqlite_errorname": code, "error": str(exc)[:800]}
    except (Exception, MemoryError) as exc:
        result = {"status": "error", "error_type": type(exc).__name__, "error": str(exc)[:800]}
    sys.stdout.write(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
