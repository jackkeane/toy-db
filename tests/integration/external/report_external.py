#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from toydb import SQLDatabase
from runner import run_slt_file


def main():
    root = Path(__file__).parent
    corpora = root / "corpora"

    suite_summary = defaultdict(lambda: {"files": 0, "cases": 0, "passed": 0, "failed": 0})
    file_results = []

    for suite_dir in sorted([p for p in corpora.iterdir() if p.is_dir()]):
        for slt_file in sorted(suite_dir.glob("*.slt")):
            db_path = root / f".tmp_{suite_dir.name}_{slt_file.stem}.db"
            wal_path = Path(str(db_path) + ".wal")
            try:
                with SQLDatabase(str(db_path)) as db:
                    r = run_slt_file(db, slt_file)
                suite = suite_dir.name
                suite_summary[suite]["files"] += 1
                suite_summary[suite]["cases"] += r["total"]
                suite_summary[suite]["passed"] += r["passed"]
                suite_summary[suite]["failed"] += r["failed"]
                file_results.append({"suite": suite, **r})
            finally:
                if db_path.exists():
                    db_path.unlink()
                if wal_path.exists():
                    wal_path.unlink()

    print("External suite report")
    print("=====================")
    for suite, s in sorted(suite_summary.items()):
        print(f"- {suite}: files={s['files']} cases={s['cases']} passed={s['passed']} failed={s['failed']}")

    out = {
        "suite_summary": dict(suite_summary),
        "file_results": file_results,
    }
    out_path = root / "external_report.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    total_failed = sum(s["failed"] for s in suite_summary.values())
    raise SystemExit(1 if total_failed else 0)


if __name__ == "__main__":
    main()
