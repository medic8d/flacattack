# flacattack

**FLAC → 6+ stems via GPU + cloud buckets. FAST af.**

`flacattack` downloads FLAC files from an S3-compatible bucket, runs GPU-accelerated
stem separation using [Demucs](https://github.com/facebookresearch/demucs)
(`htdemucs_6s` – drums / bass / other / vocals / guitar / piano), and uploads the
resulting stems back to an output bucket.  Multiple files are processed concurrently
via a configurable thread-pool.

---

## Quick start

### 1 – Install

```bash
pip install flacattack
# or from source
pip install -e ".[dev]"
```

### 2 – Set credentials

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# For non-AWS providers (GCS, Backblaze B2, Cloudflare R2, …)
export S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

### 3 – Run

```bash
flacattack attack \
  --input-bucket  my-flac-bucket \
  --output-bucket my-stems-bucket \
  --input-prefix  uploads/ \
  --output-prefix stems/ \
  --device cuda \
  --workers 4
```

Every `*.flac` file under `uploads/` in `my-flac-bucket` will be processed and
its 6 stems uploaded under `stems/<track-name>/` in `my-stems-bucket`.

---

## CLI reference

```
Usage: flacattack attack [OPTIONS]

  Download FLACs from INPUT_BUCKET, separate into 6+ stems, upload to
  OUTPUT_BUCKET.

Options:
  -i, --input-bucket TEXT     S3 bucket containing source FLAC files.  [required]
  -o, --output-bucket TEXT    S3 bucket for separated stems.  [required]
  --input-prefix TEXT         Key prefix to filter source files.  [default: ]
  --output-prefix TEXT        Key prefix applied to output stems.  [default: stems]
  -m, --model TEXT            Demucs model.  [default: htdemucs_6s]
  -d, --device TEXT           Torch device: cuda, cpu, or auto.  [default: auto]
  -w, --workers INTEGER       Concurrent download/upload threads.  [default: 4]
  -j, --jobs INTEGER          Parallel jobs passed to Demucs per file.  [default: 1]
  --mp3                       Output MP3 stems instead of WAV.
  --float32 / --no-float32    Store WAV stems as 32-bit float.  [default: float32]
  --endpoint-url TEXT         Custom S3 endpoint (GCS / Backblaze / R2 / …).
  -v, --verbose               Enable debug logging.
  --version                   Show the version and exit.
```

All options can also be supplied via environment variables:

| Option            | Environment variable             |
|-------------------|----------------------------------|
| `--input-bucket`  | `FLACATTACK_INPUT_BUCKET`        |
| `--output-bucket` | `FLACATTACK_OUTPUT_BUCKET`       |
| `--input-prefix`  | `FLACATTACK_INPUT_PREFIX`        |
| `--output-prefix` | `FLACATTACK_OUTPUT_PREFIX`       |
| `--model`         | `FLACATTACK_MODEL`               |
| `--device`        | `FLACATTACK_DEVICE`              |
| `--workers`       | `FLACATTACK_WORKERS`             |
| `--jobs`          | `FLACATTACK_JOBS`                |
| `--endpoint-url`  | `S3_ENDPOINT_URL`                |

---

## Python API

```python
from flacattack.pipeline import run

results = run(
    input_bucket="my-flac-bucket",
    output_bucket="my-stems-bucket",
    input_prefix="uploads/",
    output_prefix="stems",
    model="htdemucs_6s",   # 6 stems: drums, bass, other, vocals, guitar, piano
    device="cuda",
    workers=4,
)
# results = {"uploads/track.flac": ["stems/track/bass.wav", ...], ...}
```

---

## Rented GPU tips

- **RunPod / Vast.ai / Lambda Labs**: pick any CUDA instance, `pip install flacattack`,
  export your bucket credentials, and run the CLI.
- Set `--workers` to the number of files you want to download/upload in parallel.
- Demucs processes one file at a time on the GPU; the workers only parallelize the
  I/O, keeping VRAM usage predictable.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```
