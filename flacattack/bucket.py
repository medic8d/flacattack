"""S3-compatible bucket helpers (upload / download / list)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import boto3
from botocore.exceptions import ClientError


def _client(
    endpoint_url: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    region_name: str | None = None,
):
    """Return a boto3 S3 client.

    Credentials are read from the environment when not supplied explicitly:
      AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION,
      S3_ENDPOINT_URL  (useful for non-AWS providers like GCS / Backblaze).
    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or os.environ.get("S3_ENDPOINT_URL"),
        aws_access_key_id=aws_access_key_id
        or os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=aws_secret_access_key
        or os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=region_name or os.environ.get("AWS_DEFAULT_REGION"),
    )


def list_flac_keys(bucket: str, prefix: str = "", **client_kwargs) -> Generator[str, None, None]:
    """Yield every *.flac object key found under *prefix* in *bucket*."""
    s3 = _client(**client_kwargs)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key: str = obj["Key"]
            if key.lower().endswith(".flac"):
                yield key


def download_file(bucket: str, key: str, dest: Path, **client_kwargs) -> Path:
    """Download *key* from *bucket* to *dest* and return *dest*.

    Creates any missing parent directories automatically.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    s3 = _client(**client_kwargs)
    s3.download_file(bucket, key, str(dest))
    return dest


def upload_file(local_path: Path, bucket: str, key: str, **client_kwargs) -> None:
    """Upload *local_path* to *bucket* under *key*.

    Raises :class:`FileNotFoundError` when *local_path* does not exist.
    """
    if not local_path.exists():
        raise FileNotFoundError(local_path)
    s3 = _client(**client_kwargs)
    try:
        s3.upload_file(str(local_path), bucket, key)
    except ClientError as exc:
        raise RuntimeError(f"Upload failed for {local_path} → s3://{bucket}/{key}") from exc


def upload_directory(local_dir: Path, bucket: str, prefix: str = "", **client_kwargs) -> list[str]:
    """Upload every file inside *local_dir* (recursively) and return the list of uploaded keys."""
    if not local_dir.is_dir():
        raise NotADirectoryError(local_dir)
    uploaded: list[str] = []
    for path in sorted(local_dir.rglob("*")):
        if path.is_file():
            relative = path.relative_to(local_dir)
            key = f"{prefix}/{relative}".lstrip("/") if prefix else str(relative)
            upload_file(path, bucket, key, **client_kwargs)
            uploaded.append(key)
    return uploaded
