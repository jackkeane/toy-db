# External SQL Corpus Integration (Starter)

This folder contains a lightweight external-test harness for ToyDB.

## Goals

- Reuse **real-world style** SQL tests from established ecosystems.
- Keep a stable, tiny starter corpus that runs fast in CI.
- Report pass/fail by source suite.

## Included starter suites

1. **sqllogictest_starter**
   - Inspired by sqllogictest format and conventions.
   - Source references:
     - https://sqlite.org/sqllogictest
     - https://duckdb.org/docs/stable/dev/sqllogictest/intro.html

2. **postgres_regress_starter**
   - Inspired by PostgreSQL regression style coverage areas.
   - Source references:
     - https://github.com/postgres/postgres
     - https://www.postgresql.org/docs/current/regress-run.html

> Note: These are curated/adapted starter cases for ToyDB's current SQL feature set.

## File format

Each `.slt` file supports:

- `statement ok` + SQL ending in `;`
- `statement error` + SQL ending in `;`
- `query` + SQL ending in `;` + expected rows after `----`

Example:

```text
statement ok
CREATE TABLE t (id INT, name TEXT);

query
SELECT id, name FROM t ORDER BY id;
----
1\tAlice
2\tBob
```

## Run

```bash
# Run external integration tests
~/anaconda3/bin/conda run -n py312 python -m pytest tests/integration/external -q

# Print suite-level report
~/anaconda3/bin/conda run -n py312 python tests/integration/external/report_external.py
```

## Converter script (sqllogictest -> ToyDB .slt)

Use this to bulk-convert upstream sqllogictest-style files.

```bash
~/anaconda3/bin/conda run -n py312 python \
  tests/integration/external/tools/convert_sqllogictest.py \
  --input-dir /path/to/upstream/sqllogictest \
  --output-dir tests/integration/external/corpora/generated_sqllogictest \
  --glob "*.test" \
  --max-files 50
```

What it does:
- keeps currently supported ToyDB statements (CREATE TABLE / INSERT / SELECT / UPDATE / DELETE)
- applies conservative filters to keep generated suites stable on ToyDB
- skips unsupported constructs (e.g. CTE/WINDOW/UNION/OUTER JOIN/HAVING and complex SELECT expression forms)
- writes a `conversion_manifest.json` with converted/skipped stats and reasons

## Reproducible larger-pack workflow (upstream sqllogictest)

The following commands pull a larger public upstream corpus and regenerate
`generated_sqllogictest` in a repeatable way.

```bash
# 1) Fetch upstream corpus snapshot
mkdir -p /tmp/upstream
cd /tmp/upstream
curl -L -H 'User-Agent: openclaw' \
  -o sqllogictest.zip \
  https://codeload.github.com/gregrahn/sqllogictest/zip/refs/heads/master
unzip -q -o sqllogictest.zip

# 2) Regenerate converted corpus (40 upstream files)
cd /home/zz79jk/clawd/toy-db
/home/zz79jk/anaconda3/envs/py312/bin/python -c "from pathlib import Path; import shutil; p=Path('tests/integration/external/corpora/generated_sqllogictest'); [shutil.rmtree(x) if x.is_dir() else x.unlink() for x in p.iterdir()] if p.exists() else None"
~/anaconda3/bin/conda run -n py312 python \
  tests/integration/external/tools/convert_sqllogictest.py \
  --input-dir /tmp/upstream/sqllogictest-master/test/random/expr \
  --output-dir tests/integration/external/corpora/generated_sqllogictest \
  --glob '*.test' \
  --max-files 40

# 3) Run external integration tests
~/anaconda3/bin/conda run -n py312 python -m pytest tests/integration/external -q
```
