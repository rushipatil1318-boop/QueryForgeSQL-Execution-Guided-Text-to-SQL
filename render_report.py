"""Turn an actual saved run into a self-contained, inspectable HTML report."""

import argparse
import html
import json
from pathlib import Path


def render_report(run_dir: Path, output: Path):
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    experiment = json.loads((run_dir / "experiment.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    demo = summary["run_type"] == "scripted_plumbing_demo"
    title = "Scripted pipeline demonstration" if demo else "Text-to-SQL evaluation"
    notice = ("Scripted responses on an original teaching database. These scores verify software control flow; "
              "they are not LLM accuracy, BIRD performance, or evidence that feedback improves a model.") if demo else (
              "Results apply only to this model, dataset snapshot, prompts and execution policy. "
              "Execution match on one database is not semantic proof.")
    metric_rows = []
    for seed, arms in summary["by_seed"].items():
        for arm, metrics in arms.items():
            accuracy = metrics["strict_execution_accuracy"]
            metric_rows.append(f"<tr><td>{html.escape(seed)}</td><td>{arm}</td><td>{metrics['n']}</td>"
                               f"<td>{accuracy:.1%}</td><td>{metrics['model_calls_total']}</td>"
                               f"<td>{metrics['reference_failures']}</td><td>{metrics['latency_p50_seconds']:.3f}s</td></tr>")
    cases = []
    for record in records:
        pipeline = record["pipeline"]
        steps = " → ".join(attempt["status"] for attempt in pipeline["attempts"])
        details = html.escape(json.dumps({"attempts": pipeline["attempts"], "reference_result": record["reference_result"],
                                         "score": record["score"]}, ensure_ascii=False, indent=2))
        cases.append(f"<article><div class='meta'>seed {record['seed']} · {html.escape(record['arm'])} · "
                     f"{html.escape(record['db_id'])} · {html.escape(record['difficulty'])}</div>"
                     f"<h3>{html.escape(pipeline['question'])}</h3><p>{html.escape(steps)}</p>"
                     f"<p>Strict execution match: <strong>{record['score']['strict_match']}</strong></p>"
                     f"<pre>{html.escape(pipeline['final_sql'] or '(no SQL)')}</pre>"
                     f"<details><summary>Inspect queries, feedback, results and score</summary><pre>{details}</pre></details></article>")
    document = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QueryForgeSQL · Run report</title><style>
:root{font-family:system-ui,sans-serif;color:#172238;background:#eef2f7}body{max-width:1050px;margin:40px auto;padding:0 22px}
h1{font-size:2.6rem;letter-spacing:-.06em;margin:8px 0}h2{margin-top:35px}.eyebrow{font-weight:750;color:#2857bb;letter-spacing:.12em}
.notice{background:#fff5d9;border-left:5px solid #c79119;padding:20px;border-radius:8px;line-height:1.6}
table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:13px;border-bottom:1px solid #e3e8ef}
article{background:white;border:1px solid #dce4ee;border-radius:12px;padding:22px;margin:16px 0}.meta{color:#526783;font-size:.86rem}
h3{margin:12px 0;font-size:1.05rem;line-height:1.5}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6fa;padding:16px;border-radius:7px;font-size:.8rem}
summary{cursor:pointer;color:#2857bb;font-weight:650}footer{color:#526783;line-height:1.6;margin:35px 0}.scroll{overflow-x:auto}
</style><body><p class="eyebrow">QUERYFORGESQL / RESEARCH NOTEBOOK</p>
<h1>__TITLE__</h1><p class="notice">__NOTICE__</p><h2>Observed run</h2>
<div class="scroll"><table><thead><tr><th>Seed</th><th>Arm</th><th>Cases</th><th>Strict match</th><th>Provider calls</th><th>Reference failures</th><th>p50 latency</th></tr></thead>
<tbody>__METRICS__</tbody></table></div><h2>Inspect every case</h2>__CASES__
<footer>Model: __MODEL__<br>Code SHA-256: __CODE__<br>Unknown cost stays null in summary.json.
LoRA and unseen-database experiments are separate, later milestones.</footer></body></html>"""
    values = {"__TITLE__": html.escape(title), "__NOTICE__": html.escape(notice),
              "__METRICS__": "".join(metric_rows), "__CASES__": "".join(cases),
              "__MODEL__": html.escape(experiment["settings"]["model"]["model"]),
              "__CODE__": experiment["code_sha256"]}
    for key, value in values.items():
        document = document.replace(key, value)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("runs/demo"))
    parser.add_argument("--output", type=Path, default=Path("runs/demo/report.html"))
    args = parser.parse_args()
    render_report(args.run, args.output)
    print(f"Report saved: {args.output}")


if __name__ == "__main__":
    main()
