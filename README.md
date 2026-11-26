# QueryForgeSQL: Execution-Guided Text-to-SQL

**Status: in progress.** The pipeline and its tests work. Evaluation with a real model on BIRD databases is still to do.

QueryForgeSQL turns a natural-language question into a SQLite query. It retrieves the relevant part of the schema, asks a model for SQL, checks that SQL before running it, executes it read-only in a sandbox, and if something fails it sends the error back to the model for at most two repairs. The project compares this feedback loop against a plain one-shot baseline.

## How it works

1. **Schema retrieval.** Tables and columns are ranked by word overlap with the question, and related foreign keys are added to the prompt.
2. **Generation.** A provider adapter calls the model (a local Ollama model or an OpenAI-compatible API). A scripted `fixture` provider is used for the tests and the demo.
3. **Validation.** SQLGlot parses the SQL and allows only one read-only query. Writes, multiple statements and disallowed functions are rejected.
4. **Sandboxed execution.** Queries run in a separate SQLite worker process with time, memory, row and output limits.
5. **Repair.** Validation or execution errors (never the reference answer) go back to the model, at most twice.
6. **Evaluation.** Baseline and feedback run on the same questions with the same first prompt. Results are compared as multisets of rows; order only counts when the reference query sorts. Runs are logged and can be resumed.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m unittest discover -s tests -v
python -m scripts.check_environment
python -m scripts.run_demo           # scripted six-question demo, both arms
python -m scripts.render_report      # HTML report of the demo run
```

Ask one question with a local model (setup in [docs/MODELS.md](docs/MODELS.md)):

```bash
ollama pull qwen2.5-coder:1.5b
python -m scripts.ask --config configs/ollama.json --dataset data/demo --db-id shop \
  --question "How many distinct orders are there?"
```

## Demo output

[reports/demo_reference.html](reports/demo_reference.html) shows one run of the scripted demo on a small hand-made shop database. The model answers in the demo are scripted, so the numbers only show that the control flow works: a rejected write, a repaired execution error, a wrong but executable answer and exhausted repairs. They are not model accuracy.

## Project layout

```
queryforgesql/   config, data, retrieval, prompts, providers, validation, sandbox, worker, pipeline, evaluation
scripts/         run_demo, ask, evaluate, render_report, prepare_demo, fetch_bird, import_bird, check_splits
configs/         demo.json, ollama.json, api.example.json
tests/           unit and integration tests (standard library unittest)
docs/            data, models, execution boundary, sources
reports/         demo report
```

## Next steps

See [EXPERIMENTS.md](EXPERIMENTS.md): run a real model on the demo questions, then on a frozen BIRD Mini-Dev subset, report unseen databases separately, and only then add LoRA fine-tuning as a third and fourth arm.

## Data and licence

BIRD data is not included. [docs/DATA.md](docs/DATA.md) and [docs/SOURCES.md](docs/SOURCES.md) explain how to download it and its licence. Code licence: [LICENSE](LICENSE).
