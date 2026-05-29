"""Web search service.

Primary  : Brave Search API  (real web results, free tier 2000 req/month)
Fallback : Wikipedia Search API (no key needed, good for songs/artists)

Set MYINSTA_BRAVE_SEARCH_API_KEY in .env to enable Brave Search.
Without the key, Wikipedia is used automatically.
"""
import json
import re
import urllib.parse
import urllib.request

from app.core.config import settings

_TIMEOUT = 10
_HEADERS = {"User-Agent": "MyInsta/1.0 (https://nasserdiary.com)"}

# Detect "what song / identify song / search lyrics" questions
_SONG_PATTERNS = re.compile(
    r"\b(song|music|track|artist|singer|band|nasheed|nasyid|hymn|"
    r"what.+this|identify|find|search|lyrics|"
    r"who (is|sings|sang|made|wrote)|title|name of)\b",
    re.IGNORECASE,
)


def _fetch_json(url: str, extra_headers: dict | None = None) -> dict:
    headers = {**_HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_song_question(question: str) -> bool:
    return bool(_SONG_PATTERNS.search(question))


def _lyrics_snippet(transcript_text: str, max_chars: int = 100) -> str:
    return transcript_text.strip()[:max_chars].strip()


# ─────────────────────────────────────────────────────────────────────────────
# Brave Search
# ─────────────────────────────────────────────────────────────────────────────

_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


def _brave_search(query: str, count: int = 5) -> list[dict]:
    """
    Call Brave Search API. Returns list of {title, description, url}.
    Requires MYINSTA_BRAVE_SEARCH_API_KEY in .env.
    """
    api_key = settings.brave_search_api_key
    if not api_key:
        return []

    params = urllib.parse.urlencode({"q": query, "count": count})
    url = f"{_BRAVE_URL}?{params}"
    extra_headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    try:
        data = _fetch_json(url, extra_headers)
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                }
            )
        return results
    except Exception as exc:
        # Key might be invalid / rate-limited — fall through to Wikipedia
        print(f"[web_search] Brave API error: {exc}")
        return []


def _format_brave_results(question: str, results: list[dict]) -> str:
    if not results:
        return ""
    lines = [f'🌐 Brave Search results for: "{question}"\n']
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['title']}**")
        if r["description"]:
            lines.append(r["description"])
        lines.append(f"🔗 {r['url']}\n")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Wikipedia fallback
# ─────────────────────────────────────────────────────────────────────────────

def _wikipedia_search(query: str, limit: int = 3) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": limit,
            "srprop": "snippet",
            "origin": "*",
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    try:
        data = _fetch_json(url)
        results = []
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
            wiki_url = (
                f"https://en.wikipedia.org/wiki/"
                f"{urllib.parse.quote(title.replace(' ', '_'))}"
            )
            results.append({"title": title, "description": snippet, "url": wiki_url})
        return results
    except Exception:
        return []


def _wikipedia_summary(title: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": "true",
            "explaintext": "true",
            "format": "json",
            "origin": "*",
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    try:
        data = _fetch_json(url)
        for page in data.get("query", {}).get("pages", {}).values():
            extract = (page.get("extract") or "").strip()
            if extract:
                first_para = extract.split("\n")[0]
                return first_para[:600] + ("..." if len(first_para) > 600 else "")
    except Exception:
        pass
    return ""


def _format_wikipedia_results(question: str, results: list[dict]) -> str:
    if not results:
        return ""
    lines = [f'🌐 Wikipedia search results for: "{question}"\n']
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['title']}**")
        if r["description"]:
            lines.append(r["description"])
        if i == 1:
            summary = _wikipedia_summary(r["title"])
            if summary and summary not in r["description"]:
                lines.append(f"\n{summary}")
        lines.append(f"🔗 {r['url']}\n")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def search_web(
    question: str,
    title: str | None = None,
    uploader: str | None = None,
    transcript_text: str | None = None,
) -> str:
    """
    Search the web and return a human-readable answer.

    Uses Brave Search (if API key set) → Wikipedia → manual links fallback.
    Song questions automatically include transcript lyrics in the search query.
    """
    is_song_q = _is_song_question(question)

    # ── Build smart queries ───────────────────────────────────────────────────
    context_parts = [p for p in [uploader, title] if p and p.lower() not in ("unknown", "none", "")]

    if is_song_q and transcript_text:
        # Use lyrics snippet as the primary search term
        snippet = _lyrics_snippet(transcript_text, 100)
        song_query = f'"{snippet}" song lyrics'
        queries = [song_query]
        if context_parts:
            queries.append(" ".join(context_parts) + " " + question)
    else:
        base = " ".join(context_parts + [question])
        queries = [base, question]

    # ── Try Brave Search first ────────────────────────────────────────────────
    if settings.brave_search_api_key:
        for query in queries:
            results = _brave_search(query)
            if results:
                return _format_brave_results(question, results)

    # ── Fall back to Wikipedia ────────────────────────────────────────────────
    for query in queries:
        results = _wikipedia_search(query)
        if results:
            return _format_wikipedia_results(question, results)

    # ── Nothing found — give clickable manual search links ────────────────────
    if is_song_q and transcript_text:
        snippet = _lyrics_snippet(transcript_text, 120)
        encoded = urllib.parse.quote(snippet + " lyrics")
        return (
            f"🌐 Could not automatically identify this song.\n\n"
            f'Lyrics detected: "{snippet}"\n\n'
            f"Search manually:\n"
            f"• Google: https://www.google.com/search?q={encoded}\n"
            f"• Genius: https://genius.com/search?q={urllib.parse.quote(snippet)}\n"
            f"• Shazam or SoundHound can identify the song from audio."
        )

    manual_q = urllib.parse.quote(" ".join(context_parts + [question]))
    return (
        f'🌐 No results found for: "{question}".\n\n'
        f"Search manually:\n"
        f"• Google: https://www.google.com/search?q={manual_q}\n"
        f"• Wikipedia: https://en.wikipedia.org/w/index.php?search={manual_q}"
    )
