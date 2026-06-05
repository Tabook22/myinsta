# MyInsta Backend

FastAPI backend for downloading Instagram videos, extracting audio, transcribing speech, translating transcripts to Arabic, and storing metadata/transcripts in SQLite.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

If installing with `uv` and `openai-whisper` fails with a missing
`pkg_resources` error, run:

```bash
uv pip install setuptools==80.9.0 wheel
uv pip install --no-build-isolation -r requirements.txt
```

## API docs

Open http://localhost:8000/docs after starting the server.

## Transcript translation

`POST /api/videos/{video_id}/translate` translates a ready transcript to Arabic
and caches the result on the transcript row. The first request uses a lightweight
web translation call; later requests return the saved Arabic text.

## Key folders

- `app/routes`: HTTP routes
- `app/services`: yt-dlp, FFmpeg, Whisper service wrappers
- `app/db`: SQLite connection and schema
- `app/models`: Pydantic request/response models
- `data/downloads`: local video files
- `data/audio`: local audio files
