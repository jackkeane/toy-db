from __future__ import annotations

from pathlib import Path

import pytest

from toydb import SQLDatabase
from .runner import run_slt_file


ROOT = Path(__file__).parent
CORPORA = ROOT / "corpora"


def _suite_files():
    suites = []
    for suite_dir in sorted([p for p in CORPORA.iterdir() if p.is_dir()]):
        files = sorted(suite_dir.glob("*.slt"))
        for f in files:
            suites.append((suite_dir.name, f))
    return suites


@pytest.mark.parametrize("suite_name,slt_file", _suite_files(), ids=lambda x: str(x))
def test_external_suite_file(temp_db_path, suite_name: str, slt_file: Path):
    db_path = temp_db_path
    with SQLDatabase(db_path) as db:
        result = run_slt_file(db, slt_file)

    assert result["failed"] == 0, (
        f"Suite={suite_name} file={slt_file.name} failed {result['failed']}/{result['total']} cases. "
        f"First failure: {result['failures'][0] if result['failures'] else 'n/a'}"
    )
