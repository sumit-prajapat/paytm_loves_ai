"""Export the backend's eval results for the /eval page (frontend-side helper; backend untouched).

Runs the backend's own eval/run_eval.py (offline, isolated temp DB) and writes
frontend/public/eval-results.json. Usage (from frontend/):  npm run eval:export
"""
import asyncio
import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "frontend", "public", "eval-results.json")

os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "eval"))

import run_eval  # noqa: E402  (backend module, used read-only)

run_eval.configure_env(live=False)
report = os.path.join(tempfile.mkdtemp(prefix="saarthi_eval_export_"), "report.md")  # keep eval/report.md untouched
result = asyncio.run(run_eval.run("eval/cases.jsonl", report))

cases = {}
with open("eval/cases.jsonl", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            c = json.loads(line)
            cases[c["id"]] = c
for row in result["rows"]:
    row["input"] = cases.get(row["id"], {}).get("input", "")

payload = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), **result}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=1)
print(f"Wrote {OUT}: {result['summary']['cases']} cases, accuracy {result['summary']['accuracy']}%")
