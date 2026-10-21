import logging
from pathlib import Path
from typing import Annotated

import typer

from enem_explorer import export as export_module
from enem_explorer import ingest
from enem_explorer import site as site_module
from enem_explorer import stage as stage_module
from enem_explorer.datasets import DATASETS, Dataset

app = typer.Typer(help="ENEM Explorer: turn INEP's raw ENEM microdata into clean, tested, ready-to-use data.")

DataDir = Annotated[Path, typer.Option("--data", help="Data directory")]
DatasetName = Annotated[str, typer.Argument(help=f"One of: {', '.join(DATASETS)}")]


@app.callback()
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _dataset(name: str) -> Dataset:
    if name not in DATASETS:
        raise typer.BadParameter(f"unknown dataset {name!r}; available: {', '.join(DATASETS)}")
    return DATASETS[name]


@app.command("ingest")
def ingest_command(name: DatasetName = "enem_2024", data: DataDir = Path("data")) -> None:
    """Download a dataset (skipped if an identical copy is already in the manifest)."""
    with ingest.make_client() as client:
        entry = ingest.download(_dataset(name), data / "raw", client)
    typer.echo(f"{name}: {entry['bytes']:,} bytes · sha256 {entry['sha256']}")


@app.command("stage")
def stage_command(name: DatasetName = "enem_2024", data: DataDir = Path("data")) -> None:
    """Convert a downloaded dataset to typed Parquet."""
    counts = stage_module.stage(_dataset(name), data / "raw", data / "staged")
    for member, rows in counts.items():
        typer.echo(f"  {member:<14} {rows:>12,} rows")


@app.command("export")
def export_command(data: DataDir = Path("data")) -> None:
    """Export the published marts as Parquet + CSV with a data dictionary (run after `dbt build`)."""
    manifest = Path(__file__).resolve().parents[2] / "dbt" / "target" / "manifest.json"
    counts = export_module.export(data / "enem.duckdb", data / "export", manifest)
    for table, rows in counts.items():
        typer.echo(f"  {table:<14} {rows:>12,} rows")


@app.command("site")
def site_command(
    data: DataDir = Path("data"), out: Annotated[Path, typer.Option("--out")] = Path("site")
) -> None:
    """Build the static explorer from the marts (run after `dbt build`)."""
    counts = site_module.build(data / "enem.duckdb", out)
    typer.echo(f"explorer written to {out}/: {counts['schools']:,} schools, {counts['states']} states")
