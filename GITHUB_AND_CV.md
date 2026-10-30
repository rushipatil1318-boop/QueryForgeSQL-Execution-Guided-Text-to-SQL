# Honest GitHub and CV presentation

Suggested repository name: `QueryForgeSQL-Execution-Guided-Text-to-SQL`.

Suggested description: “Reproducible text-to-SQL baseline with schema retrieval, read-only SQLite execution, bounded repairs and a BIRD evaluation harness. Research in progress.”

Keep `README.md` status accurate. The implementation scaffold and local software checks are not a completed BIRD/LoRA study. Do not replace the words “scripted demo” with “LLM experiment.”

## Before publishing or updating

- For this initial source upload, local tests may be deferred. Keep the project marked In progress, and keep the earlier assistant Linux reference validation separate from target-machine results. Run and record your own checks when you resume implementation.
- Understand the core pipeline, validation/runtime layers, repair budget and evaluator. Complete small exercises and record your own changes.
- Commit source, tests, configs without secrets, docs and honest reference reports. Raw data, model weights, `.venv`, private run logs and API keys are excluded.
- Review any HTML/JSON result before sharing: prompts, schema identifiers, SQL and result rows are stored for inspection.
- Do not copy validation counts or latency from the packaged Linux reference and label them as your Windows measurements.
- Distinguish MIT project code from separately licensed BIRD/model material; preserve attribution.
- Record assistance used honestly when relevant. Do not claim every line was written unaided if it was not. What you can explain, test, modify and investigate is the useful evidence.

## CV wording while learning

Use “In progress” and describe work you can demonstrate. For example, after reproducing and understanding the software baseline:

“Developing a reproducible text-to-SQL system with schema retrieval, read-only SQLite execution, SQL validation and a two-attempt repair loop; preparing controlled BIRD evaluations.”

This wording has no invented accuracy or completion claim. Do not add LoRA, state-of-the-art results, production security or cloud deployment until those are implemented, run and documented. Replace the wording with measured results only after actual experiments exist.

## Evidence to add progressively

Your own test output, a real model query trace, official dataset/model fingerprints, paired evaluation summaries, an inspected failure case, an experimental report and—later—an actually deployed demo. GitHub-hosted CI passing is verified only after the workflow runs; a workflow file alone is not proof of passing CI.
