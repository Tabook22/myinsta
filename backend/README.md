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

## YouTube downloads (reliability)

YouTube actively blocks bots. Most MyInsta YouTube failures are fixed by:

1. **Fresh cookies** (signed-in browser)
2. **Latest `yt-dlp[default]`**
3. **Node.js** on PATH (signature / EJS challenges)
4. **FFmpeg** on PATH (merge video+audio when needed)

### Cookies on a VPS (recommended)

1. On your PC, open Chrome/Firefox while signed into YouTube.
2. Install extension **Get cookies.txt LOCALLY**.
3. Export `cookies.txt` for `youtube.com`.
4. Copy to the server, e.g. `/home/nasser/.config/myinsta/youtube_cookies.txt`.
5. In `backend/.env`:

```text
YOUTUBE_COOKIES_FILE=/home/nasser/.config/myinsta/youtube_cookies.txt
YOUTUBE_COOKIES_FROM_BROWSER=
```

6. Restart the backend.

Re-export cookies every few weeks (they expire) or whenever downloads start
failing with “sign in / not a bot”.

### Cookies on local Windows

```text
YOUTUBE_COOKIES_FROM_BROWSER=chrome
```

Use `edge` or `firefox` if that is where you are signed in. Do **not** use
browser-cookie mode on a headless VPS.

### Upgrade yt-dlp + Node

```bash
# Node (Ubuntu/Debian example)
sudo apt-get update && sudo apt-get install -y nodejs ffmpeg

cd /opt/myinsta/backend
source .venv/bin/activate
pip install -U "yt-dlp[default]"
sudo systemctl restart myinsta.service
```

### What the downloader tries now

- Normalizes `youtu.be` / Shorts / embed URLs
- Progressive MP4 first (fewer merge failures)
- Modern player clients: default, `android_vr`, `mweb`, `web_safari`, `tv`…
- Cookie file → browser cookies → cookieless fallback
- Clearer user-facing errors (403, age-gate, missing Node, bad formats)

The backend requires `yt-dlp[default]>=2026.6.9`; older builds fail on current
YouTube players even with valid cookies.

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
