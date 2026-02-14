# Video Translate

Japanese video to Traditional Chinese subtitle automation pipeline.

Extract audio from MP4, transcribe Japanese speech to text, and translate subtitles to Chinese — all in one command.

## Features

- **One-command pipeline** — `./run.sh video.mp4` handles everything
- **Local transcription** — faster-whisper (CTranslate2) for ~4x speedup over OpenAI Whisper
- **Gemini translation** — Google Gemini 2.0 Flash for high-quality Japanese → Chinese translation
- **Hallucination filtering** — auto-detects and removes repeated/nonsensical transcription segments
- **Device auto-detection** — GPU (float16) if available, CPU (INT8) fallback
- **Batch translation** — 20 subtitles per API call to reduce cost and latency
- **VLC ready** — output SRT files auto-load in VLC when placed alongside the video

## Workflow

```
MP4 Video
  ↓  extract_audio.py (FFmpeg)
WAV Audio (16kHz, mono)
  ↓  transcribe.py (faster-whisper, large-v3)
Japanese SRT (*.ja.srt)
  ↓  translate_srt.py (Gemini 2.0 Flash)
Chinese SRT (*.zh-TW.srt)
```

## Requirements

- Python 3.7+
- [FFmpeg](https://ffmpeg.org/) installed and in PATH
- [Google Gemini API Key](https://aistudio.google.com/apikey)

## Installation

```bash
git clone https://github.com/birdtasi/video-translate.git
cd video-translate

pip install -r requirements.txt
```

Create a `.env` file with your Gemini API key:

```bash
GEMINI_API_KEY=your-api-key-here
```

## Usage

### Full pipeline (recommended)

```bash
export GEMINI_API_KEY='your-api-key-here'
./run.sh /path/to/video.mp4
```

Output:
- `video.wav` — extracted audio
- `video.ja.srt` — Japanese transcript
- `video.zh-TW.srt` — Traditional Chinese subtitles

### Individual scripts

**Extract audio:**

```bash
python extract_audio.py video.mp4 -o video.wav -r 16000
```

**Transcribe (faster-whisper):**

```bash
python transcribe.py video.wav -o video.ja.srt -m large-v3
```

Supported models: `small`, `medium`, `large-v3`

**Translate subtitles:**

```bash
export INPUT_SRT_PATH="video.ja.srt"
export OUTPUT_SRT_PATH="video.zh-TW.srt"
export TARGET_LANG_CODE="zh-TW"
python translate_srt.py
```

Supports `zh-TW` (Traditional Chinese) and `zh-CN` (Simplified Chinese).

**Alternative: Gemini transcription:**

```bash
python transcribe_gemini.py video.wav -o video.ja.srt -l "Japanese"
```

Uses Gemini 2.5 Pro for cloud-based transcription as a backup method.

## File Naming Convention

| File | Description |
|------|-------------|
| `filename.mp4` | Input video |
| `filename.wav` | Extracted audio |
| `filename.ja.srt` | Japanese transcript |
| `filename.zh-TW.srt` | Traditional Chinese subtitles |

Place the `.zh-TW.srt` file in the same directory as the video — VLC will auto-load it.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Audio Extraction | FFmpeg |
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) |
| Translation | Google Gemini 2.0 Flash |
| Subtitle Format | SRT |

## License

MIT
