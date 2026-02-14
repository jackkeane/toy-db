#!/usr/bin/env python3
"""
Convert upstream sqllogictest-style files into ToyDB external .slt files.

Scope (v1):
- Parses headers: `statement ok`, `statement error`, `query ...`
- Preserves expected output blocks under `----`
- Filters out unsupported SQL/features for current ToyDB
- Emits converted files + manifest JSON with converted/skipped counts

Usage:
  python tests/integration/external/tools/convert_sqllogictest.py \
    --input-dir /path/to/upstream/tests \
    --output-dir tests/integration/external/corpora/generated_sqllogictest \
    --max-files 50
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


SUPPORTED_HEADER_RE = re.compile(r"^(statement\s+ok|statement\s+error|query\b.*)$", re.IGNORECASE)

# Heuristic filters for features not yet supported/reliable in ToyDB.
UNSUPPORTED_PATTERNS = [
    ("window_functions", re.compile(r"\bover\s*\(", re.IGNORECASE)),
    ("with_cte", re.compile(r"\bwith\b", re.IGNORECASE)),
    ("union", re.compile(r"\bunion\b", re.IGNORECASE)),
    ("except_intersect", re.compile(r"\b(except|intersect)\b", re.IGNORECASE)),
    ("having", re.compile(r"\bhaving\b", re.IGNORECASE)),
    ("outer_join", re.compile(r"\b(left|right|full)\s+outer\s+join\b", re.IGNORECASE)),
    ("alter", re.compile(r"\balter\s+table\b", re.IGNORECASE)),
    ("create_view", re.compile(r"\bcreate\s+view\b", re.IGNORECASE)),
    ("drop_view", re.compile(r"\bdrop\s+view\b", re.IGNORECASE)),
    ("transactions", re.compile(r"\b(begin|commit|rollback|savepoint)\b", re.IGNORECASE)),
]


@dataclass
class Block:
    header: str
    sql: str
    expected: List[str]


def parse_sqllogictest(path: Path) -> List[Block]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    i = 0
    out: List[Block] = []

    def skip_noise(idx: int) -> int:
        while idx < len(lines):
            s = lines[idx].strip()
            if not s or s.startswith("#"):
                idx += 1
            else:
                break
        return idx

    while i < len(lines):
        i = skip_noise(i)
        if i >= len(lines):
            break

        header = lines[i].strip()
        if not SUPPORTED_HEADER_RE.match(header):
            # Skip unknown sections conservatively
            i += 1
            continue

        i += 1
        sql_lines: List[str] = []
        while i < len(lines):
            raw = lines[i]
            if not raw.strip() and sql_lines:
                break
            sql_lines.append(raw)
            if raw.rstrip().endswith(";"):
                i += 1
                break
            i += 1

        sql = "\n".join(sql_lines).strip()
        expected: List[str] = []

        i = skip_noise(i)
        if header.lower().startswith("query"):
            if i < len(lines) and lines[i].strip() == "----":
                i += 1
                while i < len(lines):
                    raw = lines[i]
                    if not raw.strip():
                        break
                    if raw.strip().startswith("#"):
                        i += 1
                        continue
                    expected.append(raw.rstrip())
                    i += 1

        out.append(Block(header=header, sql=sql, expected=expected))

    return out


def classify_sql(sql: str) -> Tuple[bool, str]:
    s = sql.strip()
    if not s:
        return False, "empty_sql"

    lowered = s.lower()

    # Keep to current ToyDB core support.
    if not re.match(r"^(create\s+table|insert\s+into|select\b|update\b|delete\b)", s, re.IGNORECASE):
        return False, "unsupported_statement_type"

    for tag, pat in UNSUPPORTED_PATTERNS:
        if pat.search(s):
            return False, tag

    # Conservative compatibility filters so converted suites remain stable.
    if lowered.startswith("create table"):
        if re.search(r"\b(primary\s+key|constraint|foreign\s+key|references|check|unique|default|collate)\b", lowered):
            return False, "complex_create_table"

    if lowered.startswith("insert into"):
        # ToyDB currently expects INSERT ... VALUES(...) without explicit column list.
        if re.match(r"insert\s+into\s+\w+\s*\(", lowered):
            return False, "insert_column_list"

    if lowered.startswith("select"):
        if re.search(r"\b(distinct|all|in\s*\(|between\b|like\b|glob\b|regexp\b|case\b|cast\b|div\b|join\b|cross\b)\b", lowered):
            return False, "complex_select"
        if re.search(r"[+\-*/%]", lowered):
            return False, "select_expressions"

    return True, "ok"


def convert_file(src: Path, dst: Path):
    blocks = parse_sqllogictest(src)
    converted: List[Block] = []
    skipped_reason_counts = {}

    for b in blocks:
        ok, reason = classify_sql(b.sql)
        if ok:
            converted.append(b)
        else:
            skipped_reason_counts[reason] = skipped_reason_counts.get(reason, 0) + 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "# Auto-converted from sqllogictest-style source",
        f"# source: {src}",
        "",
    ]

    for b in converted:
        lines.append(b.header)
        lines.append(b.sql)
        lines.append("")
        if b.header.lower().startswith("query"):
            lines.append("----")
            lines.extend(b.expected)
            lines.append("")

    dst.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "source": str(src),
        "output": str(dst),
        "total_blocks": len(blocks),
        "converted_blocks": len(converted),
        "skipped_blocks": len(blocks) - len(converted),
        "skipped_reasons": skipped_reason_counts,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, help="Directory with upstream .test/.slt files")
    ap.add_argument("--output-dir", required=True, help="Directory for converted .slt files")
    ap.add_argument("--glob", default="*.test", help="Input file glob (default: *.test)")
    ap.add_argument("--max-files", type=int, default=100, help="Max files to convert")
    ap.add_argument("--manifest", default="conversion_manifest.json", help="Manifest filename")
    args = ap.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    files = sorted(in_dir.rglob(args.glob))[: args.max_files]
    if not files:
        # Also try .slt automatically when no .test files found
        files = sorted(in_dir.rglob("*.slt"))[: args.max_files]

    results = []
    for src in files:
        rel = src.relative_to(in_dir)
        dst = (out_dir / rel).with_suffix(".slt")
        results.append(convert_file(src, dst))

    summary = {
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "files_seen": len(files),
        "files_converted": len(results),
        "blocks_total": sum(r["total_blocks"] for r in results),
        "blocks_converted": sum(r["converted_blocks"] for r in results),
        "blocks_skipped": sum(r["skipped_blocks"] for r in results),
        "results": results,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / args.manifest
    manifest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("sqllogictest conversion complete")
    print(f"files: {summary['files_converted']}")
    print(f"blocks converted: {summary['blocks_converted']}/{summary['blocks_total']}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
