# Experimental report — fill after actual runs

Status: planned / running / complete. Author, date and research question: to be filled.

## Protocol

Record code commit/hash, dataset source/revision/license/checksums/selected IDs, approved database hashes, train/development/test database groups, split checks, evidence policy, retrieval budgets, prompt version and scoring contracts. Record any manual review and frozen exclusion rules before final testing.

Record model/base/tokenizer revisions, model digest, quantization, serving runtime, decoding settings, hardware/OS, seeds and execution resource limits. If LoRA is used later, include actual training data, hyperparameters and adapter/checkpoint provenance.

## Actual results

| Condition | Cases | Strict EX | BIRD-style set EX | Invalid SQL | Repair executability | Repair correctness | p50/p95 latency | Calls | Known API cost |
|---|---|---|---|---|---|---|---|---|---|
| Base / no feedback | Not run | — | — | — | — | — | — | — | — |
| Base / feedback | Not run | — | — | — | — | — | — | — | — |
| LoRA / no feedback | Planned | — | — | — | — | — | — | — | — |
| LoRA / feedback | Planned | — | — | — | — | — | — | — | — |

Report counts and denominators, reference failures, result caps, model/system failures, each seed and its variation, per-difficulty/per-database results and separately identified unseen-database results. Unknown cost stays unknown; no model usage is inferred from fixture calls.

## Error analysis

Inspect a predefined sample: schema retrieval, joins, aggregation, values, dates, order/ties, unsupported policy, timeout/result limit, model/network errors and reference ambiguity. Include real query traces and rows with sensitive data removed where necessary. An executable wrong query is a useful negative example.

## Interpretation and limits

Write only conclusions supported by actual paired measurements. Discuss extra feedback calls/latency, small sample size, development tuning, reference correctness, exact-match limitations, seed behavior, model contamination risk and any untested component.

## Reproduction

Include exact commands/config paths, environment versions, model/dataset fingerprints, raw log locations and any resume. Link the source commit corresponding to the run. Record what was not run and why.
