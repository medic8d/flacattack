"""Tests for flacattack.pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from flacattack.pipeline import process_key, run

BUCKET_IN = "input-bucket"
BUCKET_OUT = "output-bucket"
REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture()
def s3_buckets():
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        yield client


def _put_flac(client, key: str, content: bytes = b"FLAC"):
    client.put_object(Bucket=BUCKET_IN, Key=key, Body=content)


def _make_fake_stem_dir(tmp_path: Path, track_name: str, model: str = "htdemucs_6s") -> Path:
    """Create a fake stem directory as Demucs would produce."""
    stem_dir = tmp_path / model / track_name
    stem_dir.mkdir(parents=True)
    for stem in ("drums.wav", "bass.wav", "other.wav", "vocals.wav", "guitar.wav", "piano.wav"):
        (stem_dir / stem).write_bytes(b"audio")
    return stem_dir


# ──────────────────────────────────────────────────────────────────────────────
# process_key
# ──────────────────────────────────────────────────────────────────────────────

def test_process_key_uploads_stems(s3_buckets):
    """process_key should download, separate, and upload stems."""
    _put_flac(s3_buckets, "tracks/song.flac")

    with mock_aws():
        # We need to re-create the buckets inside the mock context
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        client.put_object(Bucket=BUCKET_IN, Key="tracks/song.flac", Body=b"FLAC")

        def fake_separate(input_path, output_dir, **kwargs):
            stem_dir = output_dir / "htdemucs_6s" / input_path.stem
            stem_dir.mkdir(parents=True, exist_ok=True)
            for stem in ("drums.wav", "bass.wav", "vocals.wav"):
                (stem_dir / stem).write_bytes(b"audio")
            return stem_dir

        with patch("flacattack.pipeline.separate", side_effect=fake_separate):
            uploaded = process_key(
                "tracks/song.flac",
                input_bucket=BUCKET_IN,
                output_bucket=BUCKET_OUT,
                output_prefix="stems",
            )

    assert len(uploaded) == 3
    assert all("stems/song" in k for k in uploaded)


def test_process_key_raises_on_missing_key():
    """If the S3 key doesn't exist the download should raise."""
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        with pytest.raises(Exception):
            process_key(
                "missing.flac",
                input_bucket=BUCKET_IN,
                output_bucket=BUCKET_OUT,
            )


# ──────────────────────────────────────────────────────────────────────────────
# run
# ──────────────────────────────────────────────────────────────────────────────

def test_run_processes_all_flac_files():
    """run() should process every FLAC in the bucket."""
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        for track in ("a.flac", "b.flac"):
            client.put_object(Bucket=BUCKET_IN, Key=track, Body=b"DATA")

        def fake_process_key(key, **kwargs):
            return [f"stems/{Path(key).stem}/vocals.wav"]

        with patch("flacattack.pipeline.process_key", side_effect=fake_process_key):
            results = run(BUCKET_IN, BUCKET_OUT, workers=2)

    assert set(results.keys()) == {"a.flac", "b.flac"}
    for stems in results.values():
        assert len(stems) == 1


def test_run_empty_bucket():
    """run() on a bucket with no FLACs should return an empty dict."""
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET_IN)
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET_OUT)
        results = run(BUCKET_IN, BUCKET_OUT)

    assert results == {}


def test_run_records_failures():
    """run() should record an empty list for keys that fail."""
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        client.put_object(Bucket=BUCKET_IN, Key="bad.flac", Body=b"X")

        with patch(
            "flacattack.pipeline.process_key",
            side_effect=RuntimeError("boom"),
        ):
            results = run(BUCKET_IN, BUCKET_OUT)

    assert results["bad.flac"] == []
