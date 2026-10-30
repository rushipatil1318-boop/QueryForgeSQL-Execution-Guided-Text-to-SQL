# Controlled research plan

Research question: **How do execution feedback and LoRA fine-tuning compare, and does combining them improve text-to-SQL correctness?**

The current implementation supports the baseline/feedback half of this study. LoRA training and the full four-arm experiment are deliberately deferred until the first pipeline is reliable. This document is a protocol, not a result.

## Milestones and gates

1. Run unit/integration tests and the scripted demo. Inspect one rejected write, one repaired execution error, one wrong executable answer and exhausted repairs.
2. Connect an actual model. Check one question, then the six original teaching cases. Save the installed model version/digest and logs.
3. Obtain official BIRD databases, freeze a small development subset and compare baseline against feedback. Audit all reference/policy failures. Freeze the prompt, retrieval, execution limits and scoring implementation.
4. Evaluate on databases excluded from development. Report unseen-database performance separately. Add multiple seeds after measuring one run's cost and latency.
5. Only then add LoRA with a suitable GPU and a frozen training protocol, followed by all four arms on the same untouched evaluation cases.

## Four arms

| Arm | Weights | Runtime feedback | Current status |
|---|---|---|---|
| Baseline | Fixed base model | None; one generation call | Implemented |
| Feedback | Same base model | Validation/execution errors; at most two repairs | Implemented |
| LoRA | Same base model plus trained adapter | None | Planned |
| LoRA + feedback | Identical trained adapter | Same repair policy | Planned |

Hold fixed: tokenizer/model base revision, quantization, decoding options, retrieval method/budgets, schema formatting, evidence policy, selected question IDs, database snapshots, execution limits and metric definitions. Initial prompts are identical across baseline/feedback. Repairs alone add failed SQL and the actual validation/execution error; they never receive reference SQL, reference rows or a correctness score.

Baseline and feedback have different maximum model-call budgets. Report that tradeoff explicitly. An optional future control can make equally many independent attempts without feedback; this separates the value of error information from simply spending more generation compute. Do not claim that comparison has already been performed.

## Splits and leakage

- Mini-Dev is a development benchmark. Do not train LoRA on its reference answers and then call its performance held out.
- Obtain an official BIRD training release separately and record its provenance. Reserve training-database groups for LoRA development. Deduplicate normalized questions and audit semantically near duplicates.
- Before touching final evaluation answers, predeclare development database IDs and final held-out database IDs. A random row split of the same databases does not test unseen-database generalization.
- Do not expose training examples from evaluation databases in few-shot prompts or retrieval indexes. This baseline has no few-shot example retriever and no conversational memory across questions.
- Run `scripts.check_splits` on the train/development/test question files. It rejects shared database IDs and exact NFKC/casefold/whitespace-normalized questions. It cannot prove semantic deduplication or exclude foundation-model pretraining contamination.
- Keep the evaluation process outside generation. Code already excludes gold fields from public records and does not use evaluator failures as repair triggers.

Example split check, after the three files actually exist:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_splits --train data/splits/train.jsonl --development data/splits/development.jsonl --test data/splits/test.jsonl
```

What/why: fail early on known database/question overlap. Input: three explicit lists using the documented BIRD/common record format. Output: a pass or a leakage error; it does not create a split or silently remove examples. Record the checksums of those files in the experimental report.

## Measurements

Report strict execution accuracy and BIRD-style set accuracy with both all-case and scoreable-only denominators; disclose every reference failure. Also report initial/attempt validation failure rate, executability, executable-repair success, repair correctness, failures by type, per-difficulty and per-database accuracy, p50/p95 latency, provider calls and known cost. Model/API failure rates should be inspected from logs separately from invalid SQL.

`repair_executability_success_rate` conditions on an initially generated query that failed validation/execution. `repair_correctness_success_rate` counts those cases that finish with a strict reference match. An executable wrong query is not considered repair-eligible: the pipeline has no access to an oracle that says it is wrong.

Start with seeds 42, 43, 44 when feasible. Report the mean and sample standard deviation across seeds and paired per-seed accuracy deltas. At temperature 0, seed changes can produce identical outputs; report the observed variation honestly. Shared cases across seeds are not independent data points, and three seeds do not establish broad significance. Do not infer robust model improvement from twelve development examples.

Latency includes candidate-side worker startup but excludes gold execution and initial schema/hash checks. The implementation runs arms sequentially; loading/cache conditions can affect timings. For latency studies, warm up explicitly, counterbalance arm order in a separate frozen protocol, and measure repeats. Existing logs preserve the current order; do not compare them to numbers with different timing scopes.

## Error analysis and semantic checks

Classify failures: schema retrieval omission; wrong table/column; join error; aggregation/grouping; filter/value mismatch; date reasoning; ordering/ties; unsupported/policy-refused query; timeout/result cap; model/network failure; questionable reference annotation.

Manually inspect a preselected sample of correct and incorrect executable queries, ideally without seeing the arm label. Check question intent, column contract, duplicates, tie behavior and empty results. A reference match on one snapshot can happen by coincidence. Additional database variants or expert-reviewed semantic checks strengthen the evidence; these are future extensions, not current guarantees.

Policy changes must be applied equally to all arms. Do not relax the sandbox or raise caps only for a favored model. Freeze a new protocol/run directory when limits change. Never silently filter out a reference that our policy cannot execute.

## Future LoRA protocol

Select a suitable open base model after measuring local/GPU resources. Freeze base/tokenizer revisions, LoRA target modules, rank, alpha, dropout, sequence length, precision, optimizer, learning rate, training tokens/updates, seed and database-disjoint training manifest. Save adapter/optimizer/RNG state, training curves, held-out loss and sample generations. Evaluate the base and adapter under the exact same inference/feedback harness.

Do not describe a served model as “LoRA fine-tuned” without actual training artifacts and provenance. The present package contains no LoRA training script, adapter checkpoint, LoRA scores, or multi-agent system.
