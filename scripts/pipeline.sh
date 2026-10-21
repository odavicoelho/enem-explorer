#!/usr/bin/env bash
# Run the whole pipeline: download → stage → dbt build → export → explorer.
# Usage: scripts/pipeline.sh            (real INEP data)
#        scripts/pipeline.sh --fixture  (synthetic sample, offline: what CI runs)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--fixture" ]]; then
  mkdir -p data/raw
  cp tests/fixtures/enem_sample.zip data/raw/enem_2024.zip
  cp tests/fixtures/censo_sample.zip data/raw/censo_escolar_2024.zip
else
  enem ingest enem_2024
  enem ingest censo_escolar_2024
fi

enem stage enem_2024
enem stage censo_escolar_2024
(cd dbt && dbt build --profiles-dir .)
enem export
enem site
