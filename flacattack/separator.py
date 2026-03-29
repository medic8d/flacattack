"""Audio stem separator powered by Demucs (htdemucs_6s – 6 stems, GPU-ready)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# The default Demucs model that yields 6 stems:
# drums, bass, other, vocals, guitar, piano
DEFAULT_MODEL = "htdemucs_6s"


def separate(
    input_path: Path,
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    device: str = "auto",
    jobs: int = 1,
    mp3: bool = False,
    float32: bool = True,
) -> Path:
    """Run Demucs stem separation on *input_path*.

    Parameters
    ----------
    input_path:
        Path to the source FLAC (or any audio) file.
    output_dir:
        Directory where Demucs writes its results.
        Stems land in ``<output_dir>/<model>/<track_name>/``.
    model:
        Demucs model name.  Defaults to ``htdemucs_6s`` (6 stems, GPU-friendly).
    device:
        ``"cuda"``, ``"cpu"``, or ``"auto"`` (let Demucs decide).
    jobs:
        Number of parallel jobs passed to Demucs (``-j``).
    mp3:
        Output MP3 instead of WAV stems.
    float32:
        Store stems as 32-bit float WAV (better quality, larger files).

    Returns
    -------
    Path
        Directory containing the separated stems for *input_path*.
    """
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "demucs",
        "--model", model,
        "--out", str(output_dir),
        "-j", str(jobs),
    ]

    if device != "auto":
        cmd += ["--device", device]

    if mp3:
        cmd.append("--mp3")

    if float32:
        cmd.append("--float32")

    cmd.append(str(input_path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Demucs failed for {input_path}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # Demucs writes stems to <output_dir>/<model>/<track_stem_name>/
    track_name = input_path.stem
    stem_dir = output_dir / model / track_name
    return stem_dir


def list_stems(stem_dir: Path) -> list[Path]:
    """Return sorted list of stem audio files inside *stem_dir*."""
    if not stem_dir.is_dir():
        raise NotADirectoryError(stem_dir)
    return sorted(stem_dir.iterdir())
