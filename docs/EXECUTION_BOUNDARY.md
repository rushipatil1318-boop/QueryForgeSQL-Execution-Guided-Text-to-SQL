# Execution boundary and resource scope

The goal is to run model-generated SQLite SELECT queries against explicitly approved **offline snapshots**, with bounded resource use. The SQL child does not receive API keys or a model client. Query text is stdin JSON, not shell code; `subprocess.run` receives an argument list and never uses `shell=True`.

## Layers implemented

1. Parse with pinned SQLGlot in the parent. Allow one SELECT/set query with read-only CTEs. Reject nested write nodes, multiple statements, PRAGMAs, ATTACH, metadata reads, table-valued functions and unapproved anonymous functions. Preserve original SQL rather than rewriting it into another dialect.
2. Start a fresh short-lived Python worker. It validates SQL again, so direct worker calls cannot skip the parser layer.
3. Open an existing file URI using `mode=ro&immutable=1` with `uri=True`. Refuse active WAL/journal sidecars. Enable query-only/trusted-schema-off, disable extension loading and memory mapping, and keep temporary SQLite storage in memory.
4. Read a bounded schema. Approve ordinary tables and their columns only; views/virtual tables are not model query targets. The runtime authorizer denies writes, attachment, transactions, metadata access and non-allowlisted runtime functions. The special zero-column SQLite `COUNT(*)` authorization path is handled without permitting attached databases.
5. Reduce SQLite SQL/string/column/expression/compound/attach/parameter/pattern/trigger limits. Enforce and verify a per-worker SQLite hard heap cap. Use a progress deadline to interrupt long VM work.
6. Bound rows and serialized result bytes. Exceeding either returns a failure with no partial rows for scoring. A parent process timeout kills a stuck worker; Linux also receives RLIMIT_AS, RLIMIT_CPU and zero file/core-size limits.

Default budgets are visible in the config. `PRAGMA hard_heap_limit` is process-wide inside that dedicated child; it limits SQLite-managed allocations, not all Python memory. On Linux, RLIMIT_AS is an address-space cap rather than a measured peak-RSS result. On Windows/macOS, OS process memory/CPU caps are not implemented. Parent timeouts include a two-second startup allowance above the worker's query deadline. Expensive work that does not hit a progress callback is still bounded by the parent deadline and applicable OS limits.

SQL parsing is also protected by SQL-character and AST-node budgets; it is not a complete parser exploit defense. API generation has its own socket timeout and output token/response-byte limits, outside the database worker's budgets.

## Assumptions and limits

- An offline database is not modified concurrently. The importer and pre-run SHA-256 check detect accidental changes between runs; they do not make a writable file immutable to other host processes. `immutable=1` is unsafe for a changing live DB.
- The whole selected ordinary-table schema is approved for read access. Retrieval guides the model; it is not row/column-level access control. Do not point this learning setup at private production databases.
- A child process shares the user's OS identity, filesystem privileges and host network capabilities. Reducing its environment does not constitute a full OS security sandbox. There are no custom file/network SQL functions, but vulnerabilities in the interpreter/parser/SQLite remain possible.
- Malicious database files need a stronger boundary. Schema inspection itself parses database content. Keep runtimes patched and use trusted public snapshots; do not advertise arbitrary-file upload support.
- Some safe SQLite expressions may be rejected. Policy-induced reference failures are logged and count in reported denominators. Do not bypass policy to improve a score.

Use container-level network, memory, CPU, PID and filesystem controls for stronger isolation before public/cloud use. See `CLOUD_LATER.md`. No production-security or Docker-validation claim is made by the local test report.
