# OmniFetch Pro

Desktop GUI front-end for `yt_dlp` built with Python (Tkinter).

## Features

- **Batch Downloading**: Process single or multiple URLs (one per line).
- **Video & Audio Modes**:
  - Video: MP4, MKV, WEBM (up to 4K / highest available resolution).
  - Audio extraction: MP3, M4A, FLAC, WAV, OPUS, OGG with configurable bitrates.
- **Post-Processing Options**: Subtitles (ID/EN), thumbnail embedding, metadata tags, description saving.
- **Download History**: Tracks completed files with direct play and folder open shortcuts.
- **Theme Support**: Dark and Light themes with persistent configuration.
- **FFmpeg Detection**: Automatic detection via system PATH or local directory.

## Usage

### Run from Source

```bash
python yt_dlp_gui.py
```

### Build Windows Executable (.exe)

Build standalone binary using PyInstaller:

```bash
pip install pyinstaller
pyinstaller OmniFetch.spec
```

Output binary: `dist/OmniFetch.exe`.

## Dependencies

- Python 3.9+
- FFmpeg (optional, recommended for video stream merging and audio extraction)

## License

See [LICENSE](LICENSE) and [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt).
