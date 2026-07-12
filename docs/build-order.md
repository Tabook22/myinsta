# Build Order and Current State

MyInsta is past the skeleton phase. The local MVP supports submitting an
Instagram or YouTube video URL, downloading media with yt-dlp, extracting audio
with FFmpeg, transcribing with Whisper, saving files into the dated local
library, editing metadata/transcript text, soft-deleting and restoring videos,
streaming local video, cleaning Whisper transcripts into readable English or
Arabic, translating to Arabic, generating professional reviews, building MyWiki
markdown, and asking transcript-grounded chat questions with English, Arabic, or
bilingual answer modes.

## Implemented

1. FastAPI backend with `/health`, `/api/videos`, and search routes.
2. SQLite schema for `videos`, `transcripts`, `chat_messages`, and `wiki_documents`.
3. Background processing pipeline:
   - yt-dlp download into `backend/data/downloads`
   - FFmpeg audio extraction into `backend/data/audio`
   - Whisper transcription
   - permanent storage under `backend/data/library/YYYY/MM/...`
4. React UI for URL submission, processing steps, saved library (list/grid),
   local playback, transcript display, editing, trash, and chat.
5. Arabic transcript/description translation on demand (cached in SQLite).
6. Transcript cleanup for readable English and Arabic output.
7. Professional review generation.
8. Chat answer-language modes for English, Arabic, and bilingual replies.
9. Retry endpoint for failed videos (`POST /api/videos/{id}/retry`).
10. User-facing pipeline error messages for common download/FFmpeg/Whisper failures.
11. Backend tests covering health, create/list/get, edit/delete/stream,
    translation, cleanup, chat, retry, and friendly error mapping.
12. Controlled YouTube support with optional duration guard.
13. FastAPI lifespan startup (replaces deprecated `on_event`).

## Local Verification

Backend:

```bash
cd backend
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run dev
```

On Windows PowerShell, use `npm.cmd run build` or `npm.cmd run dev` if script
execution policy blocks `npm.ps1`.

VPS frontend deploy:

```bash
cd ~/hermes-work/myinsta
git reset --hard origin/main
git pull origin main
cd frontend
npm install
npm run build
sudo rsync -a --delete dist/ /opt/myinsta/frontend/dist/
sudo systemctl restart nginx
sudo systemctl restart myinsta.service
```

## Next Work

1. Add more tests around partial pipeline failures and library file cleanup.
2. Consider subtitle/caption import for YouTube before falling back to Whisper.
3. Small UX polish: auto-dismiss backend-online banner, richer empty states.
4. Only after MVP polish, design transcript chunking and future vector retrieval.
