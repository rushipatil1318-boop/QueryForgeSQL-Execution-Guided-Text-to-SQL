# Connect a real model after the software demo works

The fixture provider is explicitly scripted. It verifies orchestration and never counts as a real-model baseline. Two HTTP adapters are implemented; no pretrained model weights or API keys are bundled.

## Option A: local Ollama

Install Ollama from https://ollama.com/download using its official Windows instructions. The example model is `qwen2.5-coder:1.5b`; its official catalog page reports a roughly 986 MB quantized download as checked on 2026-10-30. Runtime RAM/context overhead is additional. Start small and measure on your hardware; no accuracy or speed is promised.

```powershell
ollama pull qwen2.5-coder:1.5b
ollama --version
ollama show qwen2.5-coder:1.5b
```

What/why: download a local instruction model and inspect its installed version/metadata. Input: a model tag. Output: locally cached weights and model details. Keep the model digest, quantization, context length, Ollama version and hardware in your experiment notes; a mutable tag alone is insufficient for exact replication. These commands do not train the model.

Keep the Ollama application/service running. If needed, start `ollama serve` in another terminal; if it reports the address is already in use, the service may already be running.

With the teaching database prepared, ask one real question:

```powershell
.\.venv\Scripts\python.exe -m scripts.ask --config configs/ollama.json --dataset data/demo --db-id shop --question "How many distinct orders are there?"
```

What/why: send a question and retrieved schema to the actual local model, then validate and execute its SQL with bounded repairs. Input: English question and the teaching database schema. Output: generated SQL, database rows, and a JSON trace under `runs/interactive/`. This interactive path has no reference answer and does not certify correctness.

For the example with relative dates, pass `--reference-date 2026-10-30` and evidence defining revenue as `quantity * unit_price`. This makes “last month” unambiguous. SQL using the current clock is explicitly restricted by the validation policy. Date functions over database column values still depend on those values; audit time-related SQL in a reproducibility review.

Then compare both pipeline arms on the teaching questions with a real model:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate --dataset data/demo --config configs/ollama.json --output runs/local_model_teaching_v1 --seeds 42
```

What/why: measure real generation and repair behavior before importing larger data. Input: six original teaching questions, actual model, same initial prompts for both arms. Output: measured execution matches and traces. These are real-model teaching results, still not BIRD results or an unseen-domain claim.

The client uses `/api/chat`, `stream=false`, seeded generation, temperature and a token limit. Record supported model options explicitly. A provider seed is a request, not a guarantee of deterministic inference across versions/hardware.

## Option B: compatible model API

Copy `configs/api.example.json` to `configs/api.local.json`, then edit the **file in VS Code**: set your trusted final HTTPS endpoint and exact model identifier. Set current token prices only when verified; otherwise leave them `null`. The client expects Chat Completions-style `messages`, `max_tokens`, `temperature`, `seed`, `choices` and `usage`; APIs that do not support this contract need an explicit adapter change. No universal provider compatibility is claimed.

Use a process environment variable for the key; do not commit it. For example, in PowerShell:

```powershell
$apiKey = Read-Host "API key" -AsSecureString
$env:QUERYFORGE_API_KEY = [System.Net.NetworkCredential]::new("", $apiKey).Password
.\.venv\Scripts\python.exe -m scripts.ask --config configs/api.local.json --dataset data/demo --db-id shop --question "How many distinct orders are there?"
Remove-Item Env:\QUERYFORGE_API_KEY
```

What/why: read the key without echoing it, make it available to this Python process, call the selected provider, and remove the environment variable after use. Input: your credentials and endpoint config. Output: a potentially billable model call and saved query trace. The SQL worker receives a reduced environment without model keys; the config/logs contain the environment variable name, not its value. `.env.example` is documentation; there is no automatic `.env` loader.

Remote model use sends question, evidence and schema identifiers to your chosen provider. The current pipeline does not send database result rows to that provider, though SQLite error text can contain schema identifiers. Review data and provider terms before using private databases. Avoid including secrets in questions/schema names; logs preserve prompts for reproducibility.

The client does not automatically retry model HTTP calls, preventing hidden duplicate requests. HTTP errors, nontext responses and output truncation are recorded as model failures. Redirects are refused so prompts and Authorization are not forwarded to another endpoint. Model-call counts represent provider invocations, including failures, not a billing audit.

No paid API calls or real model inference were made in the packaged local reference validation.
