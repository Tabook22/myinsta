# MyInsta

Local-first personal library for Instagram and YouTube videos. Paste a link,
download media locally, transcribe speech with Whisper, clean/translate text,
take notes, export wiki markdown, and ask transcript-grounded questions in
English, Arabic, or bilingual mode.

## Stack

- React + Vite (frontend)
- FastAPI + SQLite (backend)
- yt-dlp (download)
- FFmpeg (audio extraction)
- Whisper (transcription)

## Status

Working local MVP with a polished capture → process → study workflow.

Implemented:

1. Paste an Instagram Reel/Post URL or a YouTube video URL.
2. Download/process video locally with yt-dlp.
3. Extract audio with FFmpeg (WAV for Whisper, MP3 for playback).
4. Transcribe speech with Whisper.
5. Clean Whisper transcripts into more readable English or Arabic.
6. Translate saved transcripts/descriptions to Arabic on demand.
7. Professional review summary of the transcript.
8. Save media, metadata, transcript, cleaned text, Arabic translation, notes,
   tags, and chat history in SQLite/local files.
9. View, stream, edit, soft-delete (trash/restore), permanently delete, and chat
   with saved videos.
10. Chat answer modes: English, Arabic, bilingual; transcript or web mode.
11. MyWiki markdown archive per video, CSV library export, Notion export.
12. Retry processing for failed videos, with clearer pipeline error messages.
13. Bilingual UI (EN/AR), dark mode, keyboard shortcuts, stats, and onboarding.

YouTube duration is configurable with `MYINSTA_MAX_YOUTUBE_DURATION_SECONDS`.
The default is `0`, which disables the hard duration guard. Long videos can take
more disk space and transcription time.

## Run Locally

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # if present
uvicorn app.main:app --reload
```

Or without activating the venv:

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm.cmd run dev
```

Open http://localhost:5173.

## Tests

Backend:

```bash
cd backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

Frontend build check:

```bash
cd frontend
npm.cmd run build
```

## Main API

Base URL during development: `http://localhost:8000`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Backend health |
| POST | `/api/videos` | Submit Instagram/YouTube URL |
| GET | `/api/videos` | List library (paginated, `X-Total-Count`) |
| GET | `/api/videos/{id}` | Video + transcript details |
| PATCH | `/api/videos/{id}` | Edit title/description/transcript/notes/tags |
| DELETE | `/api/videos/{id}` | Soft-delete (trash) |
| POST | `/api/videos/{id}/retry` | Re-run pipeline for a **failed** video |
| POST | `/api/videos/{id}/restore` | Restore from trash |
| DELETE | `/api/videos/{id}/permanent` | Hard-delete from trash |
| GET | `/api/videos/{id}/stream` | Stream local video |
| GET | `/api/videos/{id}/audio` | Stream/download audio |
| GET/POST | `/api/videos/{id}/chat` | Chat history / ask question |
| POST | `/api/videos/{id}/translate` | Arabic transcript translation |
| POST | `/api/videos/{id}/cleanup` | Clean transcript |
| POST | `/api/videos/{id}/review` | Professional review |
| GET | `/api/videos/export` | CSV export |
| GET | `/api/videos/stats` | Library stats |
| GET | `/api/videos/trash` | Trash list |

## Local data layout

```text
backend/data/
├── myinsta.sqlite3
├── downloads/          # temporary downloads
├── audio/              # temporary extracted audio
├── library/YYYY/MM/... # permanent media + transcript
└── mywiki/             # markdown wiki files
```

Do not commit databases, downloads, library media, or `.env` secrets.

## VPS Deploy

The live nginx config serves the frontend from:

```text
/opt/myinsta/frontend/dist/
```

Deploy from the VPS with:

```bash
cd ~/hermes-work/myinsta
git reset --hard origin/main
git pull origin main

cd frontend
npm install
npm run build

sudo mkdir -p /opt/myinsta/frontend/dist
sudo rsync -a --delete dist/ /opt/myinsta/frontend/dist/

sudo systemctl restart myinsta.service
sudo systemctl restart nginx
```

Or run the helper script:

```bash
cd ~/hermes-work/myinsta
bash scripts/deploy-vps.sh
```

## Project docs

- `AGENTS.md` — agent/contributor guide
- `docs/build-order.md` — implementation status and next work
- `backend/README.md` / `frontend/README.md` — package-level notes
