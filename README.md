# J-TransCapture

Japanese video to Traditional Chinese subtitle automation pipeline.

Extract audio from MP4, transcribe Japanese speech to text, and translate subtitles to Chinese — all in one command.

## Features

- **One-command pipeline** — `./run.sh video.mp4` handles everything
- **Apple Silicon accelerated** — mlx-whisper for native Metal GPU transcription (~3x faster than CPU)
- **OpenRouter translation** — supports multiple LLM backends (Grok, GLM, Gemma) via OpenRouter API
- **Hallucination filtering** — auto-detects and removes repeated/nonsensical transcription segments
- **Batch translation** — 50 subtitles per API call to reduce cost and latency
- **Parallel translation** — concurrent API requests for faster processing
- **Retranslation tool** — detect and fix remaining Japanese segments in translated files
- **Batch processing** — process multiple videos with `batch_process.sh`
- **VLC ready** — output SRT files auto-load in VLC when placed alongside the video

## Workflow

```
MP4 Video
  ↓  extract_audio.py (FFmpeg)
WAV Audio (16kHz, mono)
  ↓  transcribe.py (mlx-whisper, large-v3)
Japanese SRT (*.ja.srt)
  ↓  translate_srt.py (OpenRouter LLM)
Chinese SRT (*.zh-TW.srt)
```

## Requirements

- Python 3.7+
- Apple Silicon Mac (for mlx-whisper GPU acceleration)
- [FFmpeg](https://ffmpeg.org/) installed and in PATH
- [OpenRouter API Key](https://openrouter.ai/) (for translation)

## Installation

```bash
git clone https://github.com/YuehChun/J-TransCapture.git
cd J-TransCapture

pip install -r requirements.txt
```

Create a `.env` file:

```bash
OPENROUTER_API_KEY=your-openrouter-key-here
GEMINI_API_KEY=your-gemini-key-here  # optional, for Gemini transcription
```

## Usage

### Full pipeline (recommended)

```bash
export OPENROUTER_API_KEY='your-api-key-here'
./run.sh /path/to/video.mp4
```

Output:
- `video.wav` — extracted audio
- `video.ja.srt` — Japanese transcript
- `video.zh-TW.srt` — Traditional Chinese subtitles

### Batch processing

```bash
./batch_process.sh
```

Processes multiple videos defined in the script. Skips already-completed files.

### Individual scripts

**Extract audio:**

```bash
python extract_audio.py video.mp4 -o video.wav -r 16000
```

**Transcribe (mlx-whisper):**

```bash
python transcribe.py video.wav -o video.ja.srt -m large-v3
```

Supported models: `small`, `medium`, `large-v3`

**Translate subtitles:**

```bash
export OPENROUTER_API_KEY='your-api-key-here'
export INPUT_SRT_PATH="video.ja.srt"
export OUTPUT_SRT_PATH="video.zh-TW.srt"
export TARGET_LANG_CODE="zh-TW"
python translate_srt.py
```

Supports `zh-TW` (Traditional Chinese) and `zh-CN` (Simplified Chinese).

**Retranslate (fix remaining Japanese):**

```bash
python retranslate.py
```

Scans translated SRT files for segments still containing Japanese and retranslates them.

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
| Speech-to-Text | [mlx-whisper](https://github.com/ml-explore/mlx-examples) (Apple Silicon GPU) |
| Translation | [OpenRouter](https://openrouter.ai/) (GLM / Grok / Gemma) |
| Subtitle Format | SRT |

## License

MIT
