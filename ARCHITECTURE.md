# P1 · ENEM Explorer: architecture proposal

> Status: **approved 2026-10-21.** In progress.

## 1. What it is
A data engineering pipeline that turns INEP's raw ENEM microdata (millions of rows, messy CSVs) into clean, tested and ready-to-use tables, plus a **public explorer**: how every school, city and state performed, and **which skills students miss the most**.

## 2. Why it's valuable (the problem it solves)
ENEM data is public, but practically unusable for normal people: 2 GB of CSVs in Latin-1, coded columns, a data dictionary in a spreadsheet, answers stored as 45-character strings, and a certificate error on INEP's server just to download it. So it's almost only used by researchers and big education companies.

- **Parents** choosing a school can't easily see how it actually performs compared with others nearby.
- **Schools** can't benchmark themselves against similar schools (same city, same type) or see which skills their students miss.
- **Tutors and prep courses (cursinhos)** guess what to focus on. The data says exactly which skills are missed most, by state and by school type.
- **City education departments, journalists and researchers** need comparisons by city and school type, without building a pipeline first.

It's also the **first dataset of the data broker (Track C)**: clean, documented Brazilian public data that's hard to get elsewhere.

## 3. What the data allows (checked on the real 2024 files)
| | |
|---|---|
| Results | 4.33M rows: 4 area scores + 5 essay competencies, answers and answer keys |
| School link | 1.57M results have a school code; 29,400 schools; 23,051 with ≥10 students |
| Geography | school city/state and exam city/state; 5,562 cities |
| School type | federal / state / municipal / private |
| Items | `ITENS_PROVA`: every question → skill code (habilidade) + difficulty parameters |
| Profiles | `PARTICIPANTES`: socioeconomic questionnaire, **not linkable** to results (INEP uses different IDs since the LGPD restructuring) |

Sample finding: average math score is **616 at private schools vs 490 at state schools**.

## 4. Architecture

```
 INEP (download.inep.gov.br)         Censo Escolar (school names)
            │  verified TLS (pinned intermediate cert), checksums
            ▼
┌──────────────────────┐
│ 1. Ingest            │  download once, idempotent, record sha256 + size in a manifest
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 2. Stage → Parquet   │  Latin-1 CSV → typed Parquet with DuckDB (explicit schema from the dictionary)
└──────────┬───────────┘  102s per full scan of the CSV → ~2s on Parquet
           ▼
┌──────────────────────┐
│ 3. Transform (dbt)   │  staging → intermediate → marts, all SQL, all tested
│    dbt-core + duckdb │
└──────────┬───────────┘
           ▼
┌──────────────────────┐        ┌──────────────────────────────┐
│ 4. Export            │──────▶ │ Open dataset (Parquet + CSV) │ GitHub Releases
└──────────┬───────────┘        └──────────────────────────────┘
           ▼
┌──────────────────────┐
│ 5. Explorer (static) │  search a school, compare with its city/state/type, skill gaps
└──────────────────────┘  GitHub Pages, Portuguese UI
```

### dbt models
| Layer | Model | What |
|---|---|---|
| staging | `stg_results`, `stg_items`, `stg_schools` | rename, type, decode codes (1 → "Federal"…), drop absent candidates |
| intermediate | `int_item_answers` | unpacks each 45-char answer string against the answer key → right/wrong per question (only students with a school, ~280M comparisons; DuckDB handles it) |
| marts | `mart_school` | per school: n, average per area and essay, rank and percentile within state and type |
| | `mart_city`, `mart_state` | same, aggregated |
| | `mart_school_type` | federal / state / municipal / private comparison |
| | `mart_skill_gaps` | % correct per skill × state × school type, with the hardest skills ranked |

### Quality and privacy
- **dbt tests:** keys unique and not null, scores within 0–1000, codes within accepted values, and row counts reconciled against the raw file.
- **Privacy rule (LGPD):** only aggregates are published, and **any group with fewer than 10 students is suppressed.** It's enforced by a dbt test, so it can't be bypassed by accident. No individual row is ever republished.
- CI runs the whole pipeline on a **small sample fixture** (a few thousand rows), so it stays fast and offline.

## 5. Stack
Python 3.12 · DuckDB · **dbt-core + dbt-duckdb** · Parquet · pytest · ruff · mypy · GitHub Actions · GitHub Pages · a small static explorer (HTML + a bit of JS, written by Claude). **Cost: $0.**

## 6. Milestones (~6–8 days of work)
1. Ingest (verified download, manifest) + stage to Parquet
2. dbt staging + school/city/state/type marts + tests
3. Item-level skill gaps (`int_item_answers`, `mart_skill_gaps`)
4. School names from Censo Escolar + export the open dataset
5. Explorer + Pages + README (with diagram, design choices and "why it's valuable") → release

## 7. Decisions (Davi, 2026-10-21)
1. **Years:** 2024 only for now. Other years come later, when we return to this project.
2. **Transformations:** dbt.
3. **School names:** yes, joined from the Censo Escolar.
4. **Explorer:** static pages with search. No DuckDB-WASM.
5. **Name:** ENEM Explorer, repo `odavicoelho/enem-explorer`.
