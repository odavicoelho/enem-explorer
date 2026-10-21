# ENEM Explorer · Architecture

## What it is
A data engineering pipeline that turns INEP's raw ENEM microdata (millions of rows, messy CSVs) into clean, tested, ready-to-use tables, plus a **public explorer**: how every school, city and state performed, and **which skills students miss the most**.

## The problem it solves
ENEM data is public, but practically unusable for most people: 2 GB of CSVs in Latin-1, coded columns, a data dictionary in a spreadsheet, answers stored as 45-character strings, and a certificate error on INEP's server just to download it. In practice it's used almost only by researchers and big education companies.

- **Parents** choosing a school can't easily see how it performs compared with others nearby.
- **Schools** can't benchmark themselves against similar schools (same city, same type) or see which skills their students miss.
- **Tutors and prep courses (cursinhos)** guess what to focus on. The data shows exactly which skills are missed most, by state and by school type.
- **City education departments, journalists and researchers** need comparisons by city and school type without building a pipeline first.

## What the data allows (ENEM 2024)
| | |
|---|---|
| Results | 4.33M rows: 4 area scores + 5 essay competencies, answers and answer keys |
| School link | 1.57M results have a school code; 29,400 schools, 23,023 published (≥10 students) |
| Geography | school city/state and exam city/state; 5,562 cities |
| School type | federal / state / municipal / private |
| Items | `ITENS_PROVA`: every question → skill (habilidade) + difficulty parameters |
| Profiles | `PARTICIPANTES`: socioeconomic questionnaire, **not linkable** to results (INEP uses different IDs since its LGPD restructuring) |
| School census | Censo Escolar 2024: names, neighborhood and facilities of 215,545 schools |

## Pipeline

```
 INEP: ENEM 2024 microdata              INEP: Censo Escolar 2024
            │  verified TLS (shipped intermediate cert), sha256 manifest, published md5 checked
            ▼
┌──────────────────────┐
│ 1. Ingest            │  download once, retries with backoff, atomic writes
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 2. Stage → Parquet   │  Latin-1 CSV → typed, zstd Parquet with DuckDB (~14 s for everything)
└──────────┬───────────┘  important column types pinned, never left to auto-detection
           ▼
┌──────────────────────┐
│ 3. Transform (dbt)   │  staging → intermediate → marts, all SQL, all tested
│    dbt-core + duckdb │
└──────────┬───────────┘
           ▼
┌──────────────────────┐        ┌──────────────────────────────────────┐
│ 4. Export            │──────▶ │ Open dataset: Parquet + CSV          │ GitHub Releases
└──────────┬───────────┘        │ + data dictionary from the dbt docs  │
           ▼                    └──────────────────────────────────────┘
┌──────────────────────┐
│ 5. Explorer (static) │  search a school, compare with its city/state/type, skill gaps
└──────────────────────┘  GitHub Pages, Portuguese UI
```

## dbt models
| Layer | Model | What |
|---|---|---|
| staging | `stg_results`, `stg_items`, `stg_schools` | readable column names, typed, codes decoded (1 → "Federal"…) |
| seed | `skills` | the 120 skills of INEP's reference matrix, extracted from its PDF |
| intermediate | `int_school_results` | students linked to a school who took every exam, with their overall average |
| | `int_item_answers` | every answer checked against its question and skill: ~210M rows, a **view** streamed straight into the marts, never stored. Handles the English/Spanish split in Languages and skips annulled questions |
| marts | `mart_school` | per school: averages, name and facilities, rank in state and among same-type schools, national percentile |
| | `mart_city`, `mart_state` | the same, aggregated |
| | `mart_school_type` | federal / state / municipal / private, per state and for Brazil |
| | `mart_skill_gaps` | % correct per skill × state × school type, with a difficulty rank |
| | `mart_school_skills` | % correct per skill for each school, next to same-state, same-type schools |

## Quality and privacy
- **93 dbt tests:** unique and not-null keys, accepted values, score ranges, staging that never drops a row, every published school has a name, and a consistency check proving the answer keys inside the results file match the item table for every booklet and position.
- **Privacy (LGPD):** only aggregates are published, and **any group with fewer than 10 students is suppressed**. The rule is a dbt test that fails the build, so it can't be skipped by accident. No individual row is ever republished.
- **Synthetic test data:** CI runs the whole pipeline on a generated sample with the exact layout of INEP's files (same columns, encoding and answer-string format) and made-up values, so no real row lives in the repository.
- **Documentation:** every published column has a description in dbt, and the dataset's data dictionary is generated from it.

## Explorer
- **Static site**, no server: the build writes small JSON files from the marts.
- **Built for phones:** the home page needs one ~3 KB file; search loads a compact name index only when it's used; each state and each school (~2 KB) loads only when opened.
- All text coming from the data is HTML-escaped before rendering.

## Stack
Python 3.12 · DuckDB · dbt-core + dbt-duckdb · Parquet · httpx · Typer · pytest · ruff · mypy · GitHub Actions · GitHub Pages · plain HTML/CSS/JS
