# MyInsta

Local-first app for saving Instagram and YouTube videos, extracting speech transcripts, and
chatting with the saved transcript text in English, Arabic, or bilingual mode.

## Stack

- React + Vite
- FastAPI
- SQLite
- yt-dlp
- FFmpeg
- Whisper

## Status

Working local MVP.

Implemented:

1. Paste an Instagram Reel/Post URL or a YouTube video URL.
2. Download/process video locally with yt-dlp.
3. Extract audio with FFmpeg.
4. Transcribe speech with Whisper.
5. Clean Whisper transcripts into more readable English or Arabic.
6. Translate saved transcripts to Arabic on demand.
7. Save media, metadata, transcript, cleaned text, Arabic translation, and chat history in SQLite/local files.
8. View, stream, edit, delete, and chat with saved videos.
9. Ask chat questions with English, Arabic, or bilingual answer modes.

YouTube duration is configurable with `MYINSTA_MAX_YOUTUBE_DURATION_SECONDS`.
The default is `0`, which disables the hard duration guard. Long videos can take
more disk space and transcription time.

## Run Locally

Backend:

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm.cmd run dev
```

Open http://localhost:5173.

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
