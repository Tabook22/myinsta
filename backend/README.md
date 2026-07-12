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

## YouTube downloads (proven VPS runbook — Jul 2026)

**Status:** Working on production VPS when the checklist below is satisfied.

### What actually works (do not invent a different path)

| Piece | Working value |
|--------|----------------|
| App path | `/opt/myinsta` |
| API (systemd) | `127.0.0.1:**8010**` (not 8000) |
| Unit file | `/etc/systemd/system/myinsta.service` |
| Cookies path | `/home/nasser/.config/myinsta/youtube_cookies.txt` |
| Cookies shape | Small YouTube-only Netscape file (~3 KB) with **`LOGIN_INFO`** |
| Node | **v22+** (`node -v`) — required for yt-dlp EJS |
| Packages | `yt-dlp[default]` + `yt-dlp-ejs` |
| CLI that must succeed | see below |

App download path: `video_downloader.py` shells out to:

```bash
python -m yt_dlp --js-runtimes node --remote-components ejs:github \
  --cookies /home/nasser/.config/myinsta/youtube_cookies.txt \
  -f "best[ext=mp4]/best" -o OUT URL
```

Incomplete cookies (SID only, no `LOGIN_INFO`) are **skipped** — they make bot checks worse.

### Upload cookies from the website (recommended)

In the app UI: **⚙ Settings → YouTube cookies → choose cookies.txt → Upload & save**.

- API: `GET/POST /api/settings/youtube-cookies`
- File is written to `YOUTUBE_COOKIES_FILE` (or app default under `data/`)
- Rejects uploads **without `LOGIN_INFO`**
- No restart required after a successful upload — click **Retry** on a failed video
- **Privacy:** cookies are secrets; only use on a private self-hosted deploy

### Cookie rules (this caused most failures)

1. Export from **https://www.youtube.com** while **signed in** (avatar visible).
2. Play a video for a few seconds, then export with **Get cookies.txt LOCALLY**.
3. Prefer a **small YouTube-only** dump, not a 190 KB “all sites” dump.
4. File **must** contain `LOGIN_INFO` (and SID / `__Secure-1PSID`).
5. After export, **verify on PC** before scp:

```powershell
Select-String -Path "C:\Users\nmtab\Downloads\youtube_cookies.txt" -Pattern "LOGIN_INFO"
# size is often ~3KB when export is correct
```

6. scp the **exact** good file (check size after upload on VPS):

```powershell
scp "C:\Users\nmtab\Downloads\youtube_cookies.txt" nasser@VPS_IP:/home/nasser/.config/myinsta/youtube_cookies.txt
```

```bash
ls -la /home/nasser/.config/myinsta/youtube_cookies.txt   # expect ~3056, not ~190000
grep -c "LOGIN_INFO" /home/nasser/.config/myinsta/youtube_cookies.txt   # must be >= 1
```

7. If yt-dlp says cookies were **rotated**, re-export from a **dedicated Chrome profile**, close that profile, scp immediately (do not keep browsing YouTube in the same profile after export).

8. Re-export when downloads break or every 1–2 weeks.

### VPS verify (always use port 8010)

```bash
cd /opt/myinsta/backend && source .venv/bin/activate

yt-dlp --js-runtimes node --remote-components ejs:github \
  --cookies /home/nasser/.config/myinsta/youtube_cookies.txt \
  -f "best[ext=mp4]/best" -o "/tmp/yt-ok.%(ext)s" \
  "https://www.youtube.com/watch?v=jNQXAC9IVRw"

sudo systemctl restart myinsta.service
sleep 3
curl -sS http://127.0.0.1:8010/health
curl -sS http://127.0.0.1:8010/health/youtube | python3 -m json.tool
```

Health should show: `has_login_info: true`, `usable: true`, `node_ok_for_ejs: true`, Node **22+**.

### Env (VPS)

```text
YOUTUBE_COOKIES_FILE=/home/nasser/.config/myinsta/youtube_cookies.txt
YOUTUBE_COOKIES_FROM_BROWSER=
MYINSTA_MAX_YOUTUBE_DURATION_SECONDS=0
```

Do not use browser-cookie mode on the headless VPS. Keep only **one** of each env line (duplicates confuse debugging).

### Local Windows (optional)

```text
YOUTUBE_COOKIES_FILE=C:/Users/nmtab/Downloads/youtube_cookies.txt
# or: YOUTUBE_COOKIES_FROM_BROWSER=chrome
```

Local MyInsta is **not** required to validate VPS cookies — VPS CLI test is enough.

### Node / yt-dlp upgrades

```bash
# Node must be v22+ for yt-dlp-ejs
node -v

cd /opt/myinsta/backend
source .venv/bin/activate
pip install -U "yt-dlp[default]" yt-dlp-ejs
sudo systemctl restart myinsta.service
```

### Failure cheat sheet

| Symptom | Cause | Fix |
|---------|--------|-----|
| `login=no` / no LOGIN_INFO | Wrong or bulk cookie file on VPS | scp small YouTube-only export; verify size + grep |
| Cookies no longer valid | Browser rotated session after export | Dedicated profile; export → close → scp immediately |
| n challenge / no formats | Old Node or missing EJS | Node 22+; `pip install -U yt-dlp-ejs`; `--remote-components ejs:github` |
| curl health Not Found on :8000 | Wrong port | Use **8010** |
| curl right after restart fails | App not ready yet | `sleep 3` then retry |

The backend requires `yt-dlp[default]>=2026.6.9` and Node **>= 22** for current YouTube.

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
