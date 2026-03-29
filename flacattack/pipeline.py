"""End-to-end pipeline: download FLAC from bucket → separate stems → upload results."""

from __future__ import annotations

import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .bucket import download_file, list_flac_keys, upload_directory
from .separator import separate

logger = logging.getLogger(__name__)


def process_key(
    key: str,
    input_bucket: str,
    output_bucket: str,
    output_prefix: str = "",
    model: str = "htdemucs_6s",
    device: str = "auto",
    jobs: int = 1,
    mp3: bool = False,
    float32: bool = True,
    client_kwargs: dict | None = None,
) -> list[str]:
    """Download one FLAC, separate it, upload stems and return uploaded keys.

    Parameters
    ----------
    key:
        S3 object key of the source FLAC file.
    input_bucket:
        S3 bucket that holds the source FLAC.
    output_bucket:
        S3 bucket where stems will be uploaded.
    output_prefix:
        Key prefix applied to all uploaded stems.
    model:
        Demucs model (default ``htdemucs_6s``).
    device:
        ``"cuda"``, ``"cpu"``, or ``"auto"``.
    jobs:
        Parallel jobs for Demucs (``-j``).
    mp3:
        Produce MP3 stems instead of WAV.
    float32:
        32-bit float WAV output.
    client_kwargs:
        Extra keyword arguments forwarded to all S3 client calls
        (``endpoint_url``, ``aws_access_key_id``, …).
    """
    if client_kwargs is None:
        client_kwargs = {}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # ── 1. Download ──────────────────────────────────────────────────────
        local_flac = tmp_dir / "input" / Path(key).name
        logger.info("Downloading s3://%s/%s", input_bucket, key)
        download_file(input_bucket, key, local_flac, **client_kwargs)

        # ── 2. Separate ──────────────────────────────────────────────────────
        stems_root = tmp_dir / "stems"
        logger.info("Separating %s with model=%s device=%s", local_flac.name, model, device)
        stem_dir = separate(
            local_flac,
            stems_root,
            model=model,
            device=device,
            jobs=jobs,
            mp3=mp3,
            float32=float32,
        )

        # ── 3. Upload ────────────────────────────────────────────────────────
        track_name = Path(key).stem
        upload_prefix = f"{output_prefix}/{track_name}".strip("/")
        logger.info("Uploading stems to s3://%s/%s/", output_bucket, upload_prefix)
        uploaded = upload_directory(stem_dir, output_bucket, upload_prefix, **client_kwargs)

    return uploaded


def run(
    input_bucket: str,
    output_bucket: str,
    input_prefix: str = "",
    output_prefix: str = "",
    model: str = "htdemucs_6s",
    device: str = "auto",
    workers: int = 4,
    jobs: int = 1,
    mp3: bool = False,
    float32: bool = True,
    client_kwargs: dict | None = None,
) -> dict[str, list[str]]:
    """Process every FLAC in *input_bucket* and return a mapping of key → uploaded stems.

    Files are processed concurrently up to *workers* threads, each running
    Demucs in its own subprocess (GPU memory is shared across subprocesses).

    Parameters
    ----------
    input_bucket:
        S3 bucket containing source FLAC files.
    output_bucket:
        S3 bucket for output stems.
    input_prefix:
        Filter source files to this key prefix.
    output_prefix:
        Prepend this prefix to all output keys.
    model:
        Demucs model name.
    device:
        ``"cuda"``, ``"cpu"``, or ``"auto"``.
    workers:
        Number of concurrent download/upload threads.
    jobs:
        ``-j`` value passed to Demucs per file.
    mp3:
        Produce MP3 stems instead of WAV.
    float32:
        32-bit float WAV output.
    client_kwargs:
        Extra keyword arguments forwarded to S3 client calls.
    """
    if client_kwargs is None:
        client_kwargs = {}

    keys = list(list_flac_keys(input_bucket, prefix=input_prefix, **client_kwargs))
    logger.info("Found %d FLAC file(s) in s3://%s/%s", len(keys), input_bucket, input_prefix)

    results: dict[str, list[str]] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_key = {
            pool.submit(
                process_key,
                key,
                input_bucket=input_bucket,
                output_bucket=output_bucket,
                output_prefix=output_prefix,
                model=model,
                device=device,
                jobs=jobs,
                mp3=mp3,
                float32=float32,
                client_kwargs=client_kwargs,
            ): key
            for key in keys
        }

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
                logger.info("✓ %s → %d stems", key, len(results[key]))
            except Exception as exc:
                logger.error("✗ %s failed: %s", key, exc)
                results[key] = []

    return results
