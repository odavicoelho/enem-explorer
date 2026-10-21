"""Download raw files once, verify them, and record what was downloaded in a manifest.

INEP's server doesn't send its intermediate TLS certificate, so most clients fail with
"unable to get local issuer certificate". Instead of disabling verification, we ship that
intermediate (issued by GlobalSign Root R46, which every system already trusts) and add it
to the normal trust store: the chain is still fully verified.
"""

import hashlib
import json
import logging
import ssl
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from enem_explorer.datasets import Dataset

log = logging.getLogger(__name__)

CERTS_DIR = Path(__file__).resolve().parents[2] / "certs"
CHUNK = 1024 * 1024


def tls_context(extra_certs: Path = CERTS_DIR) -> ssl.SSLContext:
    context = ssl.create_default_context()
    for pem in sorted(extra_certs.glob("*.pem")):
        context.load_verify_locations(cafile=pem)
    return context


def make_client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        verify=tls_context(),
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "enem-explorer (+https://github.com/odavicoelho/enem-explorer)"},
    )


def zip_path(dataset: Dataset, raw_dir: Path) -> Path:
    return raw_dir / f"{dataset.name}.zip"


def download(
    dataset: Dataset,
    raw_dir: Path,
    client: httpx.Client,
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    """Download the dataset's zip unless an identical copy is already recorded in the manifest.

    Government servers drop connections now and then, so transport errors are retried with backoff.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = zip_path(dataset, raw_dir)
    manifest = load_manifest(raw_dir)
    known = manifest.get(dataset.name)
    if known and target.exists() and target.stat().st_size == known["bytes"]:
        log.info("already downloaded dataset=%s bytes=%d", dataset.name, known["bytes"])
        return known

    partial = target.with_suffix(".part")
    for attempt in range(retries + 1):
        try:
            size, sha256, expected = _stream_to(client, dataset.url, partial)
            break
        except httpx.TransportError as exc:
            if attempt == retries:
                raise
            wait = 5.0 * 2**attempt
            log.warning("download interrupted (%s), retrying in %.0fs", type(exc).__name__, wait)
            sleep(wait)
    if expected is not None and size != expected:
        partial.unlink()
        raise OSError(f"incomplete download of {dataset.url}: got {size} of {expected} bytes")
    partial.replace(target)  # only a complete file ever gets the final name

    entry: dict[str, object] = {
        "url": dataset.url,
        "bytes": size,
        "sha256": sha256,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifest[dataset.name] = entry
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    log.info("downloaded dataset=%s bytes=%d sha256=%s", dataset.name, size, entry["sha256"])
    return entry


def _stream_to(client: httpx.Client, url: str, path: Path) -> tuple[int, str, int | None]:
    digest = hashlib.sha256()
    size = 0
    with client.stream("GET", url) as response:
        response.raise_for_status()
        expected = int(response.headers.get("content-length", 0)) or None
        with path.open("wb") as f:
            for chunk in response.iter_bytes(CHUNK):
                f.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    return size, digest.hexdigest(), expected


def load_manifest(raw_dir: Path) -> dict[str, dict[str, object]]:
    path = raw_dir / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}
