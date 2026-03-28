# flacattack

**flacattack** converts FLAC audio files into separated stems (vocals, drums, bass, and other instruments) using AI-powered source separation.

## Features

- Accepts FLAC audio files as input
- Splits a mixed track into individual stems: vocals, drums, bass, and other
- Outputs stems as separate audio files

## Requirements

- Python 3.8+
- [Demucs](https://github.com/facebookresearch/demucs) (audio source separation)
- [ffmpeg](https://ffmpeg.org/)

## Installation

```bash
pip install demucs
```

Make sure `ffmpeg` is installed and available on your `PATH`.

## Usage

```bash
python flacattack.py <input.flac>
```

Stems will be saved to an output directory alongside the source file.

## Output

Each run produces the following stems:

| Stem    | Description              |
|---------|--------------------------|
| vocals  | Lead and backing vocals  |
| drums   | Percussion and drums     |
| bass    | Bass guitar / bass line  |
| other   | Everything else          |

## License

MIT
