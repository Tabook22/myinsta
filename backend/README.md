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

**Important:** A large cookies file is not enough. It must be a **fresh Netscape**
export from a browser **signed into youtube.com**, including `LOGIN_INFO` and/or
`SID` / `__Secure-1PSID`. Stale cookies often make the bot check *worse*.

1. On your PC, open Chrome/Firefox while signed into **https://www.youtube.com**.
2. Play any video (so the session is warm).
3. Install extension **Get cookies.txt LOCALLY**.
4. Export cookies for the current site → `youtube_cookies.txt`.
5. Copy to the server:

```bash
mkdir -p /home/nasser/.config/myinsta
# from your PC (example):
# scp youtube_cookies.txt nasser@YOUR_VPS:/home/nasser/.config/myinsta/youtube_cookies.txt
chmod 600 /home/nasser/.config/myinsta/youtube_cookies.txt
```

6. In `backend/.env`:

```text
YOUTUBE_COOKIES_FILE=/home/nasser/.config/myinsta/youtube_cookies.txt
YOUTUBE_COOKIES_FROM_BROWSER=
```

7. Restart and diagnose:

```bash
sudo systemctl restart myinsta.service
curl -sS http://127.0.0.1:8000/health/youtube | python3 -m json.tool
```

Look for `cookies.usable: true`, `has_login_info` / `has_session_ids`, and Node path.

Re-export cookies **weekly** (or whenever YouTube fails). If your VPS IP is
heavily rate-limited, set `YOUTUBE_PROXY` or try from another network.
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
