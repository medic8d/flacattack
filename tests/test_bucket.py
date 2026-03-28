"""Tests for flacattack.bucket using moto S3 mocking."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from flacattack.bucket import (
    download_file,
    list_flac_keys,
    upload_directory,
    upload_file,
)

BUCKET = "test-bucket"
REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Set dummy AWS credentials so moto doesn't complain."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        yield BUCKET


# ──────────────────────────────────────────────────────────────────────────────
# list_flac_keys
# ──────────────────────────────────────────────────────────────────────────────

def test_list_flac_keys_empty(s3_bucket):
    keys = list(list_flac_keys(s3_bucket))
    assert keys == []


def test_list_flac_keys_returns_only_flac(s3_bucket, tmp_path):
    client = boto3.client("s3", region_name=REGION)
    # Put a FLAC and a non-FLAC
    client.put_object(Bucket=s3_bucket, Key="song.flac", Body=b"data")
    client.put_object(Bucket=s3_bucket, Key="notes.txt", Body=b"text")

    keys = list(list_flac_keys(s3_bucket))
    assert keys == ["song.flac"]


def test_list_flac_keys_prefix_filter(s3_bucket):
    client = boto3.client("s3", region_name=REGION)
    client.put_object(Bucket=s3_bucket, Key="music/track1.flac", Body=b"a")
    client.put_object(Bucket=s3_bucket, Key="other/track2.flac", Body=b"b")

    keys = list(list_flac_keys(s3_bucket, prefix="music/"))
    assert keys == ["music/track1.flac"]


# ──────────────────────────────────────────────────────────────────────────────
# download_file
# ──────────────────────────────────────────────────────────────────────────────

def test_download_file(s3_bucket, tmp_path):
    content = b"FLACSAMPLE"
    boto3.client("s3", region_name=REGION).put_object(
        Bucket=s3_bucket, Key="track.flac", Body=content
    )
    dest = tmp_path / "out" / "track.flac"
    result = download_file(s3_bucket, "track.flac", dest)
    assert result == dest
    assert dest.read_bytes() == content


# ──────────────────────────────────────────────────────────────────────────────
# upload_file
# ──────────────────────────────────────────────────────────────────────────────

def test_upload_file_success(s3_bucket, tmp_path):
    local = tmp_path / "track.flac"
    local.write_bytes(b"AUDIO")
    upload_file(local, s3_bucket, "uploads/track.flac")
    obj = boto3.client("s3", region_name=REGION).get_object(
        Bucket=s3_bucket, Key="uploads/track.flac"
    )
    assert obj["Body"].read() == b"AUDIO"


def test_upload_file_missing_raises(s3_bucket, tmp_path):
    with pytest.raises(FileNotFoundError):
        upload_file(tmp_path / "nonexistent.flac", s3_bucket, "missing.flac")


# ──────────────────────────────────────────────────────────────────────────────
# upload_directory
# ──────────────────────────────────────────────────────────────────────────────

def test_upload_directory(s3_bucket, tmp_path):
    src = tmp_path / "stems"
    src.mkdir()
    (src / "vocals.wav").write_bytes(b"vocals")
    (src / "bass.wav").write_bytes(b"bass")

    keys = upload_directory(src, s3_bucket, prefix="track1")
    assert sorted(keys) == ["track1/bass.wav", "track1/vocals.wav"]


def test_upload_directory_not_a_dir(s3_bucket, tmp_path):
    with pytest.raises(NotADirectoryError):
        upload_directory(tmp_path / "missing", s3_bucket)
