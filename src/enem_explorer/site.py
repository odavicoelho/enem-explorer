"""Build the static explorer: small JSON files from the marts + the HTML/JS/CSS shell.

Phones on 4G are the main audience, so nothing big loads up front: the home page needs one small
file, search loads a compact name index, a state page loads its rankings, and a school page loads
one ~2 KB file with that school's details.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import duckdb

TEMPLATE = Path(__file__).parent / "site_template"
AVERAGES = ["avg_natural_sciences", "avg_humanities", "avg_languages", "avg_math", "avg_essay", "avg_overall"]
# A school's skill result needs enough answers behind it before we compare it with anything.
MIN_SKILL_ANSWERS = 30


def build(database: Path, out_dir: Path) -> dict[str, int]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(TEMPLATE, out_dir)
    data_dir = out_dir / "data"
    (data_dir / "states").mkdir(parents=True)
    (data_dir / "schools").mkdir()
    con = duckdb.connect(str(database), read_only=True)
    try:
        _write(data_dir / "overview.json", overview(con))
        index = school_index(con)
        _write(data_dir / "schools-index.json", index)
        states = [row[0] for row in con.execute("SELECT state FROM mart_state ORDER BY state").fetchall()]
        for state in states:
            detail, schools = state_detail(con, state)
            _write(data_dir / "states" / f"{state}.json", detail)
            for school in schools:
                _write(data_dir / "schools" / f"{school['school_id']}.json", school)
    finally:
        con.close()
    return {"schools": len(index["rows"]), "states": len(states)}


def overview(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    return {
        "totals": _one(con, "SELECT count(*) AS schools, sum(students) AS students FROM mart_school"),
        "school_types": _all(
            con,
            f"SELECT school_type, schools, students, {', '.join(AVERAGES)} "
            "FROM mart_school_type WHERE state = 'BR' ORDER BY avg_overall DESC",
        ),
        "states": _all(
            con,
            f"SELECT state, schools, students, {', '.join(AVERAGES)} "
            "FROM mart_state ORDER BY avg_overall DESC",
        ),
        "hardest_skills": _all(
            con,
            "SELECT school_type, area, skill, skill_description, pct_correct FROM mart_skill_gaps "
            "WHERE state = 'BR' AND difficulty_rank <= 3 ORDER BY school_type, area, difficulty_rank",
        ),
    }


TYPE_CODES = {"Federal": "F", "Estadual": "E", "Municipal": "M", "Privada": "P"}


def school_index(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Compact rows (arrays, one-letter school types) so the search index stays small."""
    columns = ["school_id", "school_name", "city", "state", "school_type", "avg_overall"]
    rows = con.execute(f"SELECT {', '.join(columns)} FROM mart_school ORDER BY school_name").fetchall()
    return {
        "columns": columns,
        "types": {code: name for name, code in TYPE_CODES.items()},
        "rows": [[*r[:4], TYPE_CODES[r[4]], r[5]] for r in rows],
    }


def state_detail(con: duckdb.DuckDBPyConnection, state: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The state page (rankings as compact rows) and one detail record per school in it."""
    params = [state]
    schools = _all(con, "SELECT * FROM mart_school WHERE state = ? ORDER BY rank_in_state", params)
    skills = _all(
        con,
        f"""
        SELECT school_id, area, skill, skill_description, pct_correct, benchmark_pct_correct, gap_vs_benchmark
        FROM mart_school_skills JOIN mart_school USING (school_id)
        WHERE mart_school.state = ? AND answers >= {MIN_SKILL_ANSWERS}
        """,
        params,
    )
    by_school: dict[int, list[dict[str, Any]]] = {}
    for s in skills:
        by_school.setdefault(s.pop("school_id"), []).append(s)
    cities = {c["city_id"]: c for c in _all(con, "SELECT * FROM mart_city WHERE state = ?", params)}
    state_row = _one(con, "SELECT * FROM mart_state WHERE state = ?", params)
    types = {t["school_type"]: t for t in _all(con, "SELECT * FROM mart_school_type WHERE state = ?", params)}
    for school in schools:
        ranked = sorted(by_school.get(school["school_id"], []), key=lambda s: s["gap_vs_benchmark"])
        school["weakest_skills"] = ranked[:5]
        school["strongest_skills"] = [s for s in ranked[-5:][::-1] if s["gap_vs_benchmark"] > 0]
        # What the school page compares against: its city, its state, and same-type schools in the state.
        school["compare"] = {
            "city": _pick(cities.get(school["city_id"], {})),
            "state": _pick(state_row),
            "same_type": _pick(types.get(school["school_type"], {})),
        }
    ranking_columns = [
        "school_id",
        "school_name",
        "city",
        "school_type",
        "students",
        "avg_overall",
        "rank_in_state",
    ]
    detail = {
        "state": state_row,
        "school_types": sorted(types.values(), key=lambda t: -t["avg_overall"]),
        "cities": sorted(cities.values(), key=lambda c: c["rank_in_state"]),
        "hardest_skills": _all(
            con,
            "SELECT school_type, area, skill, skill_description, pct_correct FROM mart_skill_gaps "
            "WHERE state = ? AND difficulty_rank <= 3 ORDER BY school_type, area, difficulty_rank",
            params,
        ),
        "ranking": {
            "columns": ranking_columns,
            "rows": [
                [TYPE_CODES[s[c]] if c == "school_type" else s[c] for c in ranking_columns] for s in schools
            ],
        },
    }
    return detail, schools


def _pick(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row.get(k) for k in ["students", *AVERAGES]}


def _all(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    cursor = con.execute(sql, params or [])
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _one(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> dict[str, Any]:
    rows = _all(con, sql, params)
    return rows[0] if rows else {}


def _write(path: Path, data: Any) -> None:
    # Compact separators: these files are downloaded on phones.
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
