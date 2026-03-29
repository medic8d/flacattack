"""Command-line interface for flacattack."""

from __future__ import annotations

import logging

import click

from . import __version__
from .pipeline import run


@click.group()
@click.version_option(__version__, prog_name="flacattack")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """flacattack – FLAC → 6+ stems via GPU + cloud buckets."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)


@main.command()
@click.option(
    "--input-bucket", "-i",
    required=True,
    envvar="FLACATTACK_INPUT_BUCKET",
    help="S3 bucket containing source FLAC files.",
)
@click.option(
    "--output-bucket", "-o",
    required=True,
    envvar="FLACATTACK_OUTPUT_BUCKET",
    help="S3 bucket for separated stems.",
)
@click.option(
    "--input-prefix",
    default="",
    show_default=True,
    envvar="FLACATTACK_INPUT_PREFIX",
    help="Key prefix to filter source files.",
)
@click.option(
    "--output-prefix",
    default="stems",
    show_default=True,
    envvar="FLACATTACK_OUTPUT_PREFIX",
    help="Key prefix applied to output stems.",
)
@click.option(
    "--model", "-m",
    default="htdemucs_6s",
    show_default=True,
    envvar="FLACATTACK_MODEL",
    help="Demucs model.  htdemucs_6s produces drums/bass/other/vocals/guitar/piano.",
)
@click.option(
    "--device", "-d",
    default="auto",
    show_default=True,
    envvar="FLACATTACK_DEVICE",
    help="Torch device: cuda, cpu, or auto.",
)
@click.option(
    "--workers", "-w",
    default=4,
    show_default=True,
    type=int,
    envvar="FLACATTACK_WORKERS",
    help="Number of concurrent download/upload threads.",
)
@click.option(
    "--jobs", "-j",
    default=1,
    show_default=True,
    type=int,
    envvar="FLACATTACK_JOBS",
    help="Parallel jobs passed to Demucs per file (-j).",
)
@click.option(
    "--mp3",
    is_flag=True,
    default=False,
    help="Output MP3 stems instead of WAV.",
)
@click.option(
    "--float32/--no-float32",
    default=True,
    show_default=True,
    help="Store WAV stems as 32-bit float (higher quality).",
)
@click.option(
    "--endpoint-url",
    default=None,
    envvar="S3_ENDPOINT_URL",
    help="Custom S3 endpoint (e.g. for GCS / Backblaze B2).",
)
def attack(
    input_bucket: str,
    output_bucket: str,
    input_prefix: str,
    output_prefix: str,
    model: str,
    device: str,
    workers: int,
    jobs: int,
    mp3: bool,
    float32: bool,
    endpoint_url: str | None,
) -> None:
    """Download FLACs from INPUT_BUCKET, separate into 6+ stems, upload to OUTPUT_BUCKET."""
    client_kwargs: dict = {}
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url

    results = run(
        input_bucket=input_bucket,
        output_bucket=output_bucket,
        input_prefix=input_prefix,
        output_prefix=output_prefix,
        model=model,
        device=device,
        workers=workers,
        jobs=jobs,
        mp3=mp3,
        float32=float32,
        client_kwargs=client_kwargs,
    )

    ok = sum(1 for v in results.values() if v)
    fail = len(results) - ok
    click.echo(f"\nDone: {ok} succeeded, {fail} failed out of {len(results)} file(s).")
    if fail:
        raise SystemExit(1)
