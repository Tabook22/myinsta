"""Web search service.

Primary  : Brave Search API  (real web results, free tier 2000 req/month)
Fallback : Wikipedia Search API (no key needed, good for songs/artists)

Set MYINSTA_BRAVE_SEARCH_API_KEY in .env to enable Brave Search.
Without the key, Wikipedia is used automatically.
"""
import gzip
import json
import re
import urllib.parse
import urllib.request

from app.core.config import settings

_TIMEOUT = 10

# Detect "what song / identify song / search lyrics" questions
_SONG_PATTERNS = re.compile(
    r"\b(song|music|track|artist|singer|band|nasheed|nasyid|hymn|"
    r"what.+this|identify|find|search|lyrics|"
    r"who (is|sings|sang|made|wrote)|title|name of)\b",
    re.IGNORECASE,
)

_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


# ─────────────────────────────────────────────────────────────────────────────
# Low-level HTTP helper — handles gzip transparently
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_json(url: str, headers: dict | None = None) -> dict:
    """Fetch a URL and return parsed JSON. Handles gzip transparently."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        raw = resp.read()
        # Decompress if the server returned gzip
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Brave Search
# ─────────────────────────────────────────────────────────────────────────────

def brave_search_raw(query: str, count: int = 5) -> tuple[list[dict], str | None]:
    """
    Call Brave Search API.
    Returns (results_list, error_message).
    error_message is None on success.
    """
    api_key = (settings.brave_search_api_key or "").strip()
    if not api_key:
        return [], "No Brave API key configured (MYINSTA_BRAVE_SEARCH_API_KEY)"

    params = urllib.parse.urlencode({"q": query, "count": count})
    url = f"{_BRAVE_URL}?{params}"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
        "User-Agent": "MyInsta/1.0",
    }

    try:
        data = _fetch_json(url, headers)

        # Check for API-level errors
        if "error" in data:
            return [], f"Brave API error: {data['error']}"
        if "message" in data and "web" not in data:
            return [], f"Brave API message: {data['message']}"

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
            })

        if not results:
            return [], "Brave returned 0 results for this query"

        return results, None

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return [], f"Brave HTTP {exc.code}: {body[:300]}"
    except Exception as exc:
        return [], f"Brave request failed: {exc}"


def _format_results(source: str, question: str, results: list[dict]) -> str:
    lines = [f"🌐 {source} results for: \"{question}\"\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        if r["description"]:
            lines.append(r["description"])
        lines.append(f"🔗 {r['url']}\n")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Wikipedia fallback
# ─────────────────────────────────────────────────────────────────────────────

def _wikipedia_search(query: str, limit: int = 3) -> list[dict]:
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": limit,
        "srprop": "snippet",
        "origin": "*",
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    try:
        data = _fetch_json(url)
        results = []
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
            wiki_url = (
                "https://en.wikipedia.org/wiki/"
                + urllib.parse.quote(title.replace(" ", "_"))
            )
            results.append({"title": title, "description": snippet, "url": wiki_url})
        return results
    except Exception:
        return []


def _wikipedia_summary(title: str) -> str:
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "exintro": "true",
        "explaintext": "true",
        "format": "json",
        "origin": "*",
    })
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    try:
        data = _fetch_json(url)
        for page in data.get("query", {}).get("pages", {}).values():
            extract = (page.get("extract") or "").strip()
            if extract:
                para = extract.split("\n")[0]
                return para[:600] + ("..." if len(para) > 600 else "")
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic — called by the /api/search/test endpoint
# ─────────────────────────────────────────────────────────────────────────────

def diagnose() -> dict:
    """Return a dict describing the current search configuration and a test call."""
    api_key = (settings.brave_search_api_key or "").strip()
    key_preview = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else ("(not set)" if not api_key else "(too short)")

    results, error = brave_search_raw("Python programming language", count=1)
    return {
        "brave_key_configured": bool(api_key),
        "brave_key_preview": key_preview,
        "brave_test_error": error,
        "brave_test_results_count": len(results),
        "brave_test_first_title": results[0]["title"] if results else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def _is_song_question(question: str) -> bool:
    return bool(_SONG_PATTERNS.search(question))


# Detect questions specifically about the creator / uploader
_CREATOR_PATTERNS = re.compile(
    r"\b(creator|author|uploader|who (made|posted|uploaded|is|are)|"
    r"channel|account|profile|follow|about (him|her|them|this person|this creator))\b",
    re.IGNORECASE,
)


def _is_creator_question(question: str) -> bool:
    return bool(_CREATOR_PATTERNS.search(question))


def _lyrics_snippet(text: str, max_chars: int = 100) -> str:
    return text.strip()[:max_chars].strip()


def search_web(
    question: str,
    title: str | None = None,
    uploader: str | None = None,
    transcript_text: str | None = None,
    use_transcript_context: bool = False,
) -> str:
    """
    Search the web and return a human-readable answer string.
    Brave Search → Wikipedia → clickable manual links.

    Query strategy:
    - Song questions   → use transcript lyrics as search term
    - Creator questions → include uploader name
    - Hybrid mode (use_transcript_context) → blend title/transcript keywords with the question
    - General questions → use the question directly (no social media bias)
    """
    is_song_q    = _is_song_question(question)
    is_creator_q = _is_creator_question(question)

    context_parts = [
        p for p in [uploader, title]
        if p and p.lower() not in ("unknown", "none", "")
    ]

    # Build search queries — order matters (best query first)
    if is_song_q and transcript_text:
        # Use lyrics to identify the song
        snippet = _lyrics_snippet(transcript_text, 100)
        queries = [f'"{snippet}" song lyrics', question]
    elif is_creator_q and uploader:
        # User is asking about the creator → include their name
        queries = [f"{uploader} {question}", question]
    elif use_transcript_context and (title or transcript_text):
        # Hybrid chat: ground web search in the video topic
        topic_bits = [p for p in [title, uploader] if p]
        if transcript_text:
            words = re.findall(r"[A-Za-z\u0600-\u06FF0-9']+", transcript_text)
            # Keep a short topical snippet from the transcript
            topic_bits.append(" ".join(words[:18]))
        topic = " ".join(topic_bits).strip()
        queries = [
            f"{question} {topic}".strip(),
            question,
            topic if topic else question,
        ]
    else:
        # General web question → just use what the user typed, no social media bias
        queries = [question]

    # Remove empty/duplicate queries
    seen: set[str] = set()
    queries = [q for q in queries if q.strip() and not (q in seen or seen.add(q))]

    brave_errors: list[str] = []

    # ── 1. Brave Search ───────────────────────────────────────────────────────
    api_key = (settings.brave_search_api_key or "").strip()
    if api_key:
        for query in queries:
            results, error = brave_search_raw(query)
            if results:
                return _format_results("Brave Search", question, results)
            if error:
                brave_errors.append(error)
    else:
        brave_errors.append("Brave API key not configured")

    # ── 2. Wikipedia fallback ─────────────────────────────────────────────────
    for query in queries:
        results = _wikipedia_search(query)
        if results:
            # Enrich first result with article summary
            if results[0]["title"]:
                summary = _wikipedia_summary(results[0]["title"])
                if summary:
                    results[0]["description"] = (
                        results[0]["description"] + "\n\n" + summary
                    ).strip()
            return _format_results("Wikipedia", question, results)

    # ── 3. Nothing found — show what went wrong + manual links ────────────────
    error_note = ""
    if brave_errors:
        error_note = f"\n\n⚠️ Brave Search issue: {brave_errors[0]}"

    if is_song_q and transcript_text:
        snippet = _lyrics_snippet(transcript_text, 120)
        enc = urllib.parse.quote(snippet + " lyrics")
        return (
            f"🌐 Could not automatically identify this song.{error_note}\n\n"
            f'Lyrics found: "{snippet}"\n\n'
            f"Search manually:\n"
            f"• Google: https://www.google.com/search?q={enc}\n"
            f"• Genius: https://genius.com/search?q={urllib.parse.quote(snippet)}\n"
            f"• Shazam / SoundHound apps can identify songs by audio."
        )

    manual_q = urllib.parse.quote(" ".join(context_parts + [question]))
    return (
        f"🌐 No results found.{error_note}\n\n"
        f"Search manually:\n"
        f"• Google: https://www.google.com/search?q={manual_q}\n"
        f"• Wikipedia: https://en.wikipedia.org/w/index.php?search={manual_q}"
    )
