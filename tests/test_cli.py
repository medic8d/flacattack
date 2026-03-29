"""Tests for flacattack CLI."""

from __future__ import annotations

import boto3
import pytest
from click.testing import CliRunner
from moto import mock_aws
from unittest.mock import patch

from flacattack.cli import main

BUCKET_IN = "in-bucket"
BUCKET_OUT = "out-bucket"
REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "flacattack" in result.output


def test_attack_no_files():
    runner = CliRunner()
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET_IN)
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET_OUT)
        result = runner.invoke(
            main,
            [
                "attack",
                "--input-bucket", BUCKET_IN,
                "--output-bucket", BUCKET_OUT,
            ],
        )
    assert result.exit_code == 0
    assert "0 succeeded" in result.output


def test_attack_success():
    runner = CliRunner()
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        client.put_object(Bucket=BUCKET_IN, Key="song.flac", Body=b"DATA")

        with patch(
            "flacattack.pipeline.process_key",
            return_value=["stems/song/vocals.wav"],
        ):
            result = runner.invoke(
                main,
                [
                    "attack",
                    "--input-bucket", BUCKET_IN,
                    "--output-bucket", BUCKET_OUT,
                ],
            )

    assert result.exit_code == 0
    assert "1 succeeded" in result.output


def test_attack_failure_exits_nonzero():
    runner = CliRunner()
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_IN)
        client.create_bucket(Bucket=BUCKET_OUT)
        client.put_object(Bucket=BUCKET_IN, Key="bad.flac", Body=b"BAD")

        with patch(
            "flacattack.pipeline.process_key",
            side_effect=RuntimeError("GPU exploded"),
        ):
            result = runner.invoke(
                main,
                [
                    "attack",
                    "--input-bucket", BUCKET_IN,
                    "--output-bucket", BUCKET_OUT,
                ],
            )

    assert result.exit_code != 0


def test_attack_missing_required_options():
    runner = CliRunner()
    result = runner.invoke(main, ["attack"])
    assert result.exit_code != 0
    assert "input-bucket" in result.output or "Missing" in result.output
