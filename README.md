# MyInsta

Local-first app for saving Instagram videos, extracting speech transcripts, and
chatting with the saved transcript text.

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

1. Paste an Instagram Reel/Post URL.
2. Download/process video locally with yt-dlp.
3. Extract audio with FFmpeg.
4. Transcribe speech with Whisper.
5. Save media, metadata, transcript, and chat history in SQLite/local files.
6. View, stream, edit, delete, and chat with saved videos.

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
