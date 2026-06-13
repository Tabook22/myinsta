# Build Order and Current State

MyInsta is now past the skeleton phase. The local MVP supports submitting an
Instagram or YouTube video URL, downloading media with yt-dlp, extracting audio with
FFmpeg, transcribing with Whisper, saving files into the dated local library,
editing metadata/transcript text, deleting saved videos, streaming local video,
cleaning Whisper transcripts into readable English or Arabic, and asking simple
transcript-grounded chat questions with English, Arabic, or bilingual answer
modes.

## Implemented

1. FastAPI backend with `/health` and `/api/videos` routes.
2. SQLite schema for `videos`, `transcripts`, and `chat_messages`.
3. Background processing pipeline:
   - yt-dlp download into `backend/data/downloads`
   - FFmpeg audio extraction into `backend/data/audio`
   - Whisper transcription
   - permanent storage under `backend/data/library/YYYY/MM/...`
4. React UI for URL submission, processing status, saved library, local
   playback, transcript display, editing, deletion, and chat.
5. Arabic transcript translation on demand, with the translated text cached in SQLite.
6. Transcript cleanup for readable English and Arabic output.
7. Chat answer-language modes for English, Arabic, and bilingual replies.
8. Backend tests covering health, create/list/get, edit/delete/stream, translation, cleanup, and chat.
9. Controlled YouTube support using the same local media/audio/transcript
   pipeline, with an optional configurable duration guard.

## Local Verification

Backend:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
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

1. Add clearer user-facing failure messages for common yt-dlp, FFmpeg, and
   Whisper failures.
2. Add more tests around partial pipeline failures and library file cleanup.
3. Keep README/API docs aligned as behavior changes.
4. Consider subtitle/caption import for YouTube before falling back to Whisper.
5. Only after MVP polish, design transcript chunking and future vector retrieval.
