# MyInsta Backend

FastAPI backend for downloading Instagram and YouTube videos, extracting audio, transcribing speech, cleaning Whisper transcripts, translating transcripts to Arabic, and storing metadata/transcripts in SQLite.

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

## YouTube cookies

Some YouTube videos ask yt-dlp to prove the request is from a signed-in browser.
For local Windows development, set this in `backend/.env` and restart the
backend:

```text
YOUTUBE_COOKIES_FROM_BROWSER=chrome
```

Use `edge` or `firefox` instead if that is where you are signed in. Do not use
browser-cookie mode on a Hostinger VPS unless that server has a real logged-in
browser profile.

On a VPS, export a YouTube `cookies.txt` file from your local browser, copy it
to the server, and set this in `backend/.env`:

```text
YOUTUBE_COOKIES_FILE=/home/nasser/.config/myinsta/youtube_cookies.txt
```

YouTube also changes its player code often. If yt-dlp shows `n challenge
solving failed` or only lists storyboard/image formats, make sure Node.js is
installed and upgrade yt-dlp with its default EJS solver package inside the
backend virtualenv:

```bash
cd /opt/myinsta/backend
.venv/bin/python -m pip install --upgrade "yt-dlp[default]"
sudo systemctl restart myinsta.service
```

## Transcript and chat translation

`POST /api/videos/{video_id}/cleanup?target_language=en` cleans a ready
transcript into readable English and caches it on the transcript row.
`target_language=ar` translates that cleaned version into readable Arabic and
caches it separately.

`POST /api/videos/{video_id}/translate` translates a ready transcript to Arabic
and caches the result on the transcript row. The first request uses a lightweight
web translation call; later requests return the saved Arabic text.

`POST /api/videos/{video_id}/chat` accepts `answer_language` as `english`,
`arabic`, or `bilingual`. Arabic and bilingual chat answers translate the
grounded transcript/web answer before saving the assistant message.

## Key folders

- `app/routes`: HTTP routes
- `app/services`: yt-dlp, FFmpeg, Whisper service wrappers
- `app/db`: SQLite connection and schema
- `app/models`: Pydantic request/response models
- `data/downloads`: local video files
- `data/audio`: local audio files
