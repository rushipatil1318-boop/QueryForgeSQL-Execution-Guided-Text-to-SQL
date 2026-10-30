# Implementation validation — 2026-10-30

This is an **assistant Linux reference run** of the packaged learning baseline, not Rushikesh's Windows measurements and not a completed text-to-SQL research study.

Environment: Python 3.12.14, SQLite 3.53.1, SQLGlot 30.27.0, Linux. Exact platform/version strings, source fingerprint and observed command timings are in `verification.json`.

## Checks actually completed

- **51 automated tests passed.** Test coverage includes parser/runtime write protection, independent read-only enforcement, runtime function authorization, path restrictions, row/byte/deadline limits, schema retrieval, data integrity, seeded subset selection, local import using original teaching records, split-overlap detection, HTTP response contracts, bounded repairs, gold separation, scoring and evaluation resume. Provider/network responses are mocked where appropriate; they are not model inference.
- **4 optional Lesson 1 exercise checks passed** for the supplied reference exercise. This does not mean the learner has completed the exercise independently.
- The scripted six-question demo ran through both baseline and feedback, producing twelve saved case records, full attempt traces and a generated HTML report.
- Completed evaluations were rerun by the integration test without adding predictions or repeating model completions. A changed configuration was refused for resume.
- The official pinned BIRD SQLite question file was downloaded and verified against its declared SHA-256: **500 records, 11 database IDs**. All 500 reference queries passed this implementation's AST validation policy. Official BIRD database execution was **not** performed.

Raw local check outputs: `tests_output.txt`, `exercise_output.txt`, `demo_output.txt`, `html_report_output.txt`. Machine-readable record: `verification.json`. Actual scripted summary: `demo_reference.json`; case inspector: `demo_reference.html`.

The archive was also extracted into a fresh folder with no generated datasets or run caches. Its full test suite, exercise, demo, HTML rendering and completed-run resume passed. Both initial and resumed demo logs contained exactly twelve cases. See `clean_archive_extraction` in `verification.json`.

## Scripted cases observed

| Case | Baseline path | Feedback path | What this checks |
|---|---|---|---|
| Revenue last month | Missing column fails | Second candidate succeeds | Actual SQLite error enters repair |
| Count orders | Executable and reference-matching | Same | Basic read-only aggregate |
| List customers | DELETE rejected | SELECT succeeds | Validation rejection precedes execution |
| Stationery products | Executable, wrong answer | Still wrong; no oracle repair | Execution success is not correctness |
| Furniture products | Empty, reference-matching | Same | Empty results do not force repair |
| Total quantity | Missing column fails | Three calls, then stops | At most two repairs |

The corresponding strict fixture matches are 2/6 for the one-shot path and 4/6 for the feedback path. Responses were deliberately scripted to exercise those branches. **These are software-fixture outcomes, not LLM quality, BIRD accuracy, or evidence that execution feedback improves a model.** API usage/cost is unknown rather than fabricated from fixture calls.

## Not completed or claimed

- No real local or hosted language-model inference; no paid model API calls.
- No official BIRD database contents were available for execution. The local importer was tested with original teaching records/database, not a fake benchmark database.
- No actual-model baseline-versus-feedback comparison, unseen-database result, research significance or multi-seed model-quality conclusion.
- No LoRA implementation/training, adapter checkpoint, LoRA scores or multi-agent system.
- No Windows/macOS runtime validation, Docker image build/run, hosted CI success, cloud deployment or public endpoint.
- No claim of production security or immunity to malformed database/parser/runtime vulnerabilities.

Run the commands in `START_HERE_MR.md` on the target Windows machine, then progress through one actual model question and the official BIRD import/evaluation. Keep those results separate from this reference. The research report template deliberately leaves unrun measurements blank.
