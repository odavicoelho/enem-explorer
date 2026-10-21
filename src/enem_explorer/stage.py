"""Stage raw CSVs as typed Parquet: read once (slow, Latin-1, ';'), query fast forever after."""

import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb

from enem_explorer.datasets import Dataset
from enem_explorer.ingest import zip_path

log = logging.getLogger(__name__)

# Types we never leave to auto-detection: codes are integers, answer strings stay text, scores are decimals.
PINNED_TYPES = {
    "results": {
        "NU_SEQUENCIAL": "BIGINT",
        "CO_ESCOLA": "BIGINT",
        "CO_MUNICIPIO_ESC": "BIGINT",
        "CO_MUNICIPIO_PROVA": "BIGINT",
        **{f"NU_NOTA_{a}": "DOUBLE" for a in ("CN", "CH", "LC", "MT", "REDACAO")},
        **{f"NU_NOTA_COMP{i}": "DOUBLE" for i in range(1, 6)},
        **{f"TX_RESPOSTAS_{a}": "VARCHAR" for a in ("CN", "CH", "LC", "MT")},
        **{f"TX_GABARITO_{a}": "VARCHAR" for a in ("CN", "CH", "LC", "MT")},
    },
    "participants": {"NU_INSCRICAO": "BIGINT", "CO_MUNICIPIO_PROVA": "BIGINT"},
    "items": {"CO_ITEM": "BIGINT", "CO_PROVA": "INTEGER", "TX_GABARITO": "VARCHAR"},
}


def stage(dataset: Dataset, raw_dir: Path, staged_dir: Path) -> dict[str, int]:
    """Convert every member of the dataset's zip to Parquet. Returns row counts per member."""
    out_dir = staged_dir / dataset.name
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with zipfile.ZipFile(zip_path(dataset, raw_dir)) as archive, tempfile.TemporaryDirectory() as tmp:
        for name, member in dataset.members.items():
            csv_path = Path(tmp) / f"{name}.csv"
            with archive.open(member) as src, csv_path.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            counts[name] = _to_parquet(
                csv_path, out_dir / f"{name}.parquet", dataset, PINNED_TYPES.get(name, {})
            )
            csv_path.unlink()
            log.info("staged dataset=%s member=%s rows=%d", dataset.name, name, counts[name])
    (out_dir / "_rows.json").write_text(json.dumps(counts, indent=2) + "\n")
    return counts


def _to_parquet(csv_path: Path, parquet_path: Path, dataset: Dataset, types: dict[str, str]) -> int:
    # SQL read_csv (unlike the Python relation API) supports Latin-1 input.
    type_struct = "{" + ", ".join(f"'{col}': '{typ}'" for col, typ in types.items()) + "}"
    tmp = parquet_path.with_suffix(".tmp.parquet")
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT * FROM read_csv(
                    '{csv_path}', delim = '{dataset.delimiter}', encoding = '{dataset.encoding}',
                    header = true, sample_size = 20000{f", types = {type_struct}" if types else ""}
                )
            ) TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)
            """
        )
        tmp.replace(parquet_path)  # never leave a half-written Parquet behind
        row = con.execute(f"SELECT count(*) FROM read_parquet('{parquet_path}')").fetchone()
        assert row is not None
        return int(row[0])
    finally:
        con.close()
