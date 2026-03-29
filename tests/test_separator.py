"""Tests for flacattack.separator (Demucs wrapper)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flacattack.separator import list_stems, separate


# ──────────────────────────────────────────────────────────────────────────────
# separate()
# ──────────────────────────────────────────────────────────────────────────────

def test_separate_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        separate(tmp_path / "nonexistent.flac", tmp_path / "out")


def test_separate_calls_demucs(tmp_path):
    """separate() should invoke Demucs via subprocess and return the stem dir."""
    flac = tmp_path / "song.flac"
    flac.write_bytes(b"FAKE_FLAC")

    out_dir = tmp_path / "out"
    stem_dir = out_dir / "htdemucs_6s" / "song"
    stem_dir.mkdir(parents=True)

    fake_result = MagicMock()
    fake_result.returncode = 0

    with patch("flacattack.separator.subprocess.run", return_value=fake_result) as mock_run:
        result = separate(flac, out_dir)

    assert result == stem_dir

    # Demucs should have been called with the expected flags
    cmd = mock_run.call_args[0][0]
    assert "--model" in cmd
    assert "htdemucs_6s" in cmd
    assert "--out" in cmd
    assert str(out_dir) in cmd
    assert str(flac) in cmd


def test_separate_custom_model(tmp_path):
    flac = tmp_path / "track.flac"
    flac.write_bytes(b"DATA")

    out_dir = tmp_path / "out"
    stem_dir = out_dir / "htdemucs" / "track"
    stem_dir.mkdir(parents=True)

    fake_result = MagicMock(returncode=0)
    with patch("flacattack.separator.subprocess.run", return_value=fake_result) as mock_run:
        result = separate(flac, out_dir, model="htdemucs")

    assert result == stem_dir
    cmd = mock_run.call_args[0][0]
    assert "htdemucs" in cmd


def test_separate_raises_on_demucs_failure(tmp_path):
    flac = tmp_path / "broken.flac"
    flac.write_bytes(b"BAD")

    fake_result = MagicMock(returncode=1, stdout="", stderr="error msg")
    with patch("flacattack.separator.subprocess.run", return_value=fake_result):
        with pytest.raises(RuntimeError, match="Demucs failed"):
            separate(flac, tmp_path / "out")


def test_separate_device_flag(tmp_path):
    flac = tmp_path / "t.flac"
    flac.write_bytes(b"X")
    out_dir = tmp_path / "out"
    (out_dir / "htdemucs_6s" / "t").mkdir(parents=True)

    fake_result = MagicMock(returncode=0)
    with patch("flacattack.separator.subprocess.run", return_value=fake_result) as mock_run:
        separate(flac, out_dir, device="cuda")

    cmd = mock_run.call_args[0][0]
    assert "--device" in cmd
    assert "cuda" in cmd


def test_separate_auto_device_no_flag(tmp_path):
    """When device='auto', --device flag should NOT be passed."""
    flac = tmp_path / "t.flac"
    flac.write_bytes(b"X")
    out_dir = tmp_path / "out"
    (out_dir / "htdemucs_6s" / "t").mkdir(parents=True)

    fake_result = MagicMock(returncode=0)
    with patch("flacattack.separator.subprocess.run", return_value=fake_result) as mock_run:
        separate(flac, out_dir, device="auto")

    cmd = mock_run.call_args[0][0]
    assert "--device" not in cmd


# ──────────────────────────────────────────────────────────────────────────────
# list_stems()
# ──────────────────────────────────────────────────────────────────────────────

def test_list_stems(tmp_path):
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    for name in ("bass.wav", "vocals.wav", "drums.wav"):
        (stem_dir / name).write_bytes(b"audio")

    stems = list_stems(stem_dir)
    assert [p.name for p in stems] == sorted(["bass.wav", "vocals.wav", "drums.wav"])


def test_list_stems_missing_dir(tmp_path):
    with pytest.raises(NotADirectoryError):
        list_stems(tmp_path / "missing")
