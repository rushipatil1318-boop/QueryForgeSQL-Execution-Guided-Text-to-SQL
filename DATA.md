# Official BIRD data: small, pinned and separate from the demo

Use SQLite only for the first milestone. The canonical Mini-Dev repository was updated in October 2026; older JSON files are not interchangeable with the pinned release. Source revision, SHA-256 and licensing are in `SOURCES.md`.

## 1. Download and verify questions

In the repository root, with the project environment:

```powershell
.\.venv\Scripts\python.exe -m scripts.fetch_bird
```

What/why: download the official pinned question file over verified HTTPS, enforce a 5 MB response cap, verify its exact SHA-256, and cache it atomically. A connection failure gets up to three attempts. Input: pinned official URL and expected hash. Output: `data/raw/bird/mini_dev_sqlite.jsonl` plus `source.json`. This step does **not** obtain the database contents or run a model.

The current file has 500 SQLite records across 11 databases. All 500 reference queries passed the local AST-policy check during preparation; this does not establish that they execute in our runtime or answer correctly.

## 2. Obtain real offline databases

Use the official [Mini-Dev repository](https://github.com/bird-bench/mini_dev) and its **Download BIRD Mini-Dev Complete Package** link, or the canonical dataset card's official database distribution. The package link recorded during preparation is in `SOURCES.md`. It can be substantially larger than the question file; it is intentionally not downloaded automatically by the demo.

Extract the package locally. Find the `dev_databases` folder containing `california_schools/california_schools.sqlite`. The exact outer ZIP folder can differ; use the actual path on your machine. Keep original data outside the repository or in ignored `data/raw/`. Do not execute third-party setup scripts to open SQLite files.

Use closed, offline snapshots. A source with a `-wal` or `-journal` file is refused. Do not use the immutable read-only option on a changing live database. The importer copies selected databases to an experiment folder and fingerprints those copies; do not modify them during evaluation.

## 3. Import twelve questions first

Replace the example `--db-root` path with the parent that actually contains `california_schools`:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_bird --db-root "C:\Users\rushi\Downloads\MINIDEV\dev_databases" --db-ids california_schools --max-cases 12 --seed 42 --output data/bird_small
```

What/why: choose a bounded subset without inspecting model answers, copy the one selected database, inspect its schema in a bounded worker, and save exact selected IDs/hashes. Selection uses database/difficulty round-robin with seed-derived hash ordering inside each group; it is independent of source record order. Input: official question file and real database folder. Output: `data/bird_small/examples.jsonl`, `databases/`, and `manifest.json`.

Existing nonempty output folders are refused, so an experiment is not silently changed. Use a new `--output` for another selection. No reference query is dropped for being difficult or unsupported. Record reference execution failures and review them instead of hiding them.

## 4. Run a real model comparison

After checking one local model call using `MODELS.md`:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate --dataset data/bird_small --config configs/ollama.json --output runs/bird_base_v1 --seeds 42,43,44
.\.venv\Scripts\python.exe -m scripts.render_report --run runs/bird_base_v1 --output runs/bird_base_v1/report.html
```

What/why: compare the same cases, retrieval settings, model and initial seed between one-shot baseline and execution feedback. Input: frozen imported data/config and actual model service. Output: paired logs, per-seed summaries, difficulty/database breakdowns and an HTML inspector. This can make up to `12 × 3 × (1 + 3) = 144` model calls; start with one seed or fewer cases if CPU time/cost is limited. No cloud API is called unless you explicitly select its config and credentials.

This one-database small subset is for **development**, not an unseen-database result. See `EXPERIMENTS.md` before expanding or tuning. An API error, policy refusal, timeout, or reference failure is logged; it is never converted to a fabricated success.

## Schema/content scope

This baseline retrieves table names, columns and declared foreign keys. It does not read BIRD description CSVs or retrieve literal values from rows. That limitation can lower accuracy, especially on questions with indirect schema/value references; record it and compare retrieval changes separately. Every ordinary table in the selected database is approved for read access; retrieved tables guide generation rather than form a column-level privacy policy.
