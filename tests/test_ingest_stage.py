import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import duckdb
import httpx
import pytest
import respx

from enem_explorer import ingest, stage
from enem_explorer.datasets import CENSO_2024, ENEM_2024

FIXTURE = Path(__file__).parent / "fixtures" / "enem_sample.zip"
URL = ENEM_2024.url


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    return tmp_path / "raw"


@respx.mock
def test_download_writes_file_and_manifest(raw_dir: Path) -> None:
    body = FIXTURE.read_bytes()
    respx.get(URL).mock(
        return_value=httpx.Response(200, content=body, headers={"content-length": str(len(body))})
    )

    with httpx.Client() as client:
        entry = ingest.download(ENEM_2024, raw_dir, client)

    assert (raw_dir / "enem_2024.zip").read_bytes() == body
    assert entry["sha256"] == hashlib.sha256(body).hexdigest()
    assert json.loads((raw_dir / "manifest.json").read_text())["enem_2024"]["bytes"] == len(body)
    assert not (raw_dir / "enem_2024.part").exists()


@respx.mock
def test_second_download_is_skipped(raw_dir: Path) -> None:
    body = FIXTURE.read_bytes()
    route = respx.get(URL).mock(return_value=httpx.Response(200, content=body))

    with httpx.Client() as client:
        ingest.download(ENEM_2024, raw_dir, client)
        ingest.download(ENEM_2024, raw_dir, client)

    assert route.call_count == 1


@respx.mock
def test_dropped_connections_are_retried(raw_dir: Path) -> None:
    body = FIXTURE.read_bytes()
    respx.get(URL).mock(side_effect=[httpx.ConnectError("reset by peer"), httpx.Response(200, content=body)])
    waits: list[float] = []

    with httpx.Client() as client:
        ingest.download(ENEM_2024, raw_dir, client, sleep=waits.append)

    assert waits == [5.0]
    assert (raw_dir / "enem_2024.zip").exists()


@respx.mock
def test_truncated_download_never_gets_the_final_name(raw_dir: Path) -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"short", headers={"content-length": "999"}))

    with httpx.Client() as client, pytest.raises(OSError, match="incomplete download"):
        ingest.download(ENEM_2024, raw_dir, client)

    assert not (raw_dir / "enem_2024.zip").exists()


def test_tls_context_trusts_the_shipped_intermediate() -> None:
    context = ingest.tls_context()
    subjects = [dict(x[0] for x in c["subject"]) for c in context.get_ca_certs()]
    assert any(s.get("commonName") == "RNP ICPEdu GR46 OV TLS CA 2025" for s in subjects)


def test_stage_produces_typed_parquet(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(FIXTURE, raw / "enem_2024.zip")

    counts = stage.stage(ENEM_2024, raw, tmp_path / "staged")

    assert counts == {"results": 600, "participants": 600, "items": 370}
    con = duckdb.connect()
    results = tmp_path / "staged" / "enem_2024" / "results.parquet"
    types = dict(
        con.execute(f"SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM '{results}')").fetchall()
    )
    assert types["CO_ESCOLA"] == "BIGINT"
    assert types["NU_NOTA_MT"] == "DOUBLE"
    assert types["TX_RESPOSTAS_MT"] == "VARCHAR"
    # Latin-1 decoded correctly
    names = {r[0] for r in con.execute(f"SELECT DISTINCT NO_MUNICIPIO_PROVA FROM '{results}'").fetchall()}
    assert "São Paulo" in names


CENSO_FIXTURE = Path(__file__).parent / "fixtures" / "censo_sample.zip"


def test_stage_verifies_published_md5(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(CENSO_FIXTURE, raw / "censo_escolar_2024.zip")

    assert stage.stage(CENSO_2024, raw, tmp_path / "staged") == {"schools": 15}


def test_stage_rejects_a_file_that_does_not_match_its_md5(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    with zipfile.ZipFile(CENSO_FIXTURE) as src, zipfile.ZipFile(raw / "censo_escolar_2024.zip", "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith("microdados_ed_basica_2024.csv"):
                data = data.replace(b"ESCOLA TESTE", b"ESCOLA FALSA")  # tampered after the checksum
            dst.writestr(info, data)

    with pytest.raises(stage.ChecksumError, match="md5"):
        stage.stage(CENSO_2024, raw, tmp_path / "staged")


def test_dictionary_uses_dbt_descriptions(tmp_path: Path) -> None:
    from enem_explorer.export import dictionary

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "nodes": {
                    "model.x.mart_state": {
                        "resource_type": "model",
                        "name": "mart_state",
                        "description": "One row per state.",
                        "columns": {"state": {"description": "State (UF)."}},
                    }
                }
            }
        )
    )

    text = dictionary({"state": 27}, manifest)

    assert "## `state` · 27 rows" in text
    assert "| `state` | State (UF). |" in text
