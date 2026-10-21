"""Export the published marts as an open dataset: Parquet, CSV and a data dictionary from dbt's docs."""

import json
from pathlib import Path

import duckdb

# mart → also export as CSV? (the per-school skill table has millions of rows: Parquet only)
TABLES = {
    "mart_school": True,
    "mart_city": True,
    "mart_state": True,
    "mart_school_type": True,
    "mart_skill_gaps": True,
    "mart_school_skills": False,
}


def export(database: Path, out_dir: Path, manifest: Path | None = None) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    con = duckdb.connect(str(database), read_only=True)
    try:
        for table, csv in TABLES.items():
            name = table.removeprefix("mart_")
            con.execute(f"COPY {table} TO '{out_dir / name}.parquet' (FORMAT parquet, COMPRESSION zstd)")
            if csv:
                con.execute(f"COPY {table} TO '{out_dir / name}.csv' (HEADER, DELIMITER ',')")
            row = con.execute(f"SELECT count(*) FROM {table}").fetchone()
            assert row is not None
            counts[name] = int(row[0])
    finally:
        con.close()
    (out_dir / "DATA_DICTIONARY.md").write_text(dictionary(counts, manifest))
    return counts


def dictionary(counts: dict[str, int], manifest: Path | None) -> str:
    """Markdown data dictionary, using the model and column descriptions written in dbt."""
    nodes = {}
    if manifest is not None and manifest.exists():
        data = json.loads(manifest.read_text())
        nodes = {n["name"]: n for n in data["nodes"].values() if n["resource_type"] == "model"}
    lines = [
        "# ENEM Explorer · open dataset (ENEM 2024)",
        "",
        "Source: INEP microdata (ENEM 2024, Censo Escolar 2024). Only aggregates are published,",
        "and any group with fewer than 10 students is suppressed. Scores are averages of students",
        "finishing high school who took every exam.",
        "",
    ]
    for name, rows in counts.items():
        node = nodes.get(f"mart_{name}", {})
        lines += [f"## `{name}` · {rows:,} rows", "", node.get("description", ""), ""]
        columns = node.get("columns", {})
        if columns:
            lines += ["| Column | Description |", "|---|---|"]
            lines += [f"| `{c}` | {meta.get('description', '')} |" for c, meta in columns.items()]
            lines.append("")
    return "\n".join(lines)
