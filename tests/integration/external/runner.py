from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Case:
    kind: str  # statement_ok | statement_error | query
    sql: str
    expected: List[str]
    line_no: int
    rowsort: bool = False


def _normalize_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def normalize_rows(rows) -> List[str]:
    out = []
    for row in rows:
        if not isinstance(row, tuple):
            row = (row,)
        out.append("\t".join(_normalize_value(v) for v in row))
    return out


def parse_slt(path: Path) -> List[Case]:
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    cases: List[Case] = []

    def skip_blanks_and_comments(idx: int) -> int:
        while idx < len(lines):
            s = lines[idx].strip()
            if not s or s.startswith("#"):
                idx += 1
            else:
                break
        return idx

    while i < len(lines):
        i = skip_blanks_and_comments(i)
        if i >= len(lines):
            break

        header = lines[i].strip().lower()
        start_line = i + 1
        if header == "statement ok":
            kind = "statement_ok"
        elif header == "statement error":
            kind = "statement_error"
        elif header.startswith("query"):
            kind = "query"
        else:
            raise ValueError(f"{path}:{i+1}: unknown header '{lines[i]}'")

        rowsort = kind == "query" and ("rowsort" in header.split())

        i += 1
        sql_lines = []
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
        i = skip_blanks_and_comments(i)
        if kind == "query":
            if i >= len(lines) or lines[i].strip() != "----":
                raise ValueError(f"{path}:{i+1}: query missing '----' expected separator")
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

        cases.append(Case(kind=kind, sql=sql, expected=expected, line_no=start_line, rowsort=rowsort))

    return cases


def run_slt_file(db, path: Path):
    cases = parse_slt(path)
    passed = 0
    failures = []

    for idx, c in enumerate(cases, start=1):
        try:
            if c.kind == "statement_ok":
                db.execute(c.sql)
            elif c.kind == "statement_error":
                try:
                    db.execute(c.sql)
                except Exception:
                    pass
                else:
                    raise AssertionError("Expected statement to fail, but it succeeded")
            else:
                got = db.execute(c.sql)
                got_rows = normalize_rows(got or [])
                exp_rows = list(c.expected)
                if c.rowsort:
                    got_rows = sorted(got_rows)
                    exp_rows = sorted(exp_rows)
                if got_rows != exp_rows:
                    raise AssertionError(
                        "Query result mismatch\n"
                        f"SQL: {c.sql}\n"
                        f"Expected: {exp_rows}\n"
                        f"Got: {got_rows}"
                    )
            passed += 1
        except Exception as e:
            failures.append(
                {
                    "case_index": idx,
                    "line_no": c.line_no,
                    "kind": c.kind,
                    "sql": c.sql,
                    "error": str(e),
                }
            )

    return {
        "file": str(path),
        "total": len(cases),
        "passed": passed,
        "failed": len(failures),
        "failures": failures,
    }
