"""Web search using Wikipedia's free Search API + DuckDuckGo Instant Answers.

No API key required. Wikipedia is used as the primary source because it has
rich articles about songs, artists, and topics. DuckDuckGo is used as a fallback.
"""
import json
import re
import urllib.parse
import urllib.request

_TIMEOUT = 10
_HEADERS = {"User-Agent": "MyInsta/1.0 (https://nasserdiary.com)"}

# Keywords that indicate the user wants to identify a song / find lyrics
_SONG_PATTERNS = re.compile(
    r"\b(song|music|track|artist|singer|band|nasheed|nasyid|hymn|what.+this|"
    r"identify|find|search|lyrics|who (is|sings|sang|made|wrote)|title|name)\b",
    re.IGNORECASE,
)


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Wikipedia ─────────────────────────────────────────────────────────────────

def _wikipedia_search(query: str, limit: int = 3) -> list[dict]:
    """Return a list of {title, snippet, url} from Wikipedia full-text search."""
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
            wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
            results.append({"title": title, "snippet": snippet, "url": wiki_url})
        return results
    except Exception:
        return []


def _wikipedia_summary(title: str) -> str:
    """Fetch the introductory summary of a Wikipedia article."""
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
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            extract = (page.get("extract") or "").strip()
            if extract:
                # Return just the first paragraph (up to 600 chars)
                first_para = extract.split("\n")[0]
                return first_para[:600] + ("..." if len(first_para) > 600 else "")
    except Exception:
        pass
    return ""


# ── DuckDuckGo ────────────────────────────────────────────────────────────────

def _duckduckgo_instant(query: str) -> str:
    """Try DuckDuckGo Instant Answers — returns a short abstract or empty string."""
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }
    )
    url = f"https://api.duckduckgo.com/?{params}"
    try:
        data = _fetch_json(url)
        return (data.get("AbstractText") or "").strip()
    except Exception:
        return ""


# ── Query builder ─────────────────────────────────────────────────────────────

def _is_song_question(question: str) -> bool:
    return bool(_SONG_PATTERNS.search(question))


def _build_song_query(transcript_text: str | None, title: str | None, uploader: str | None) -> str:
    """Build the best search query to identify a song."""
    parts: list[str] = []

    # Use first ~80 chars of transcript as lyrics snippet
    if transcript_text:
        snippet = transcript_text.strip()[:80].strip()
        if snippet:
            parts.append(f'"{snippet}"')

    if uploader and uploader.lower() not in ("unknown", "none"):
        parts.append(uploader)

    parts.append("song OR nasheed OR lyrics")
    return " ".join(parts)


def _build_general_query(
    question: str, title: str | None, uploader: str | None
) -> str:
    parts: list[str] = []
    if uploader and uploader.lower() not in ("unknown", "none"):
        parts.append(uploader)
    if title and title != uploader:
        parts.append(title)
    parts.append(question)
    return " ".join(parts)


# ── Main entry point ──────────────────────────────────────────────────────────

def search_web(
    question: str,
    title: str | None = None,
    uploader: str | None = None,
    transcript_text: str | None = None,
) -> str:
    """
    Search the web and return a human-readable answer.

    Strategy:
    1. If question is about a song → search Wikipedia using lyrics snippet
    2. Otherwise → search Wikipedia using title + uploader + question
    3. Enrich first result with a Wikipedia article summary
    4. Fall back to DuckDuckGo if Wikipedia returns nothing
    """
    is_song_q = _is_song_question(question)

    if is_song_q and transcript_text:
        primary_query = _build_song_query(transcript_text, title, uploader)
        fallback_query = _build_general_query(question, title, uploader)
    else:
        primary_query = _build_general_query(question, title, uploader)
        fallback_query = question

    # ── Step 1: Wikipedia search ──────────────────────────────────────────────
    results = _wikipedia_search(primary_query)
    if not results and primary_query != fallback_query:
        results = _wikipedia_search(fallback_query)

    if results:
        lines: list[str] = [
            f'🌐 Web search results for: "{question}"\n'
        ]
        for i, r in enumerate(results, 1):
            lines.append(f"**{i}. {r['title']}**")
            if r["snippet"]:
                lines.append(r["snippet"])
            # Fetch full summary for the top result
            if i == 1:
                summary = _wikipedia_summary(r["title"])
                if summary and summary not in r["snippet"]:
                    lines.append(f"\n{summary}")
            lines.append(f"🔗 {r['url']}\n")

        return "\n".join(lines)

    # ── Step 2: DuckDuckGo fallback ───────────────────────────────────────────
    ddg_abstract = _duckduckgo_instant(primary_query)
    if ddg_abstract:
        return (
            f'🌐 Web search results for: "{question}"\n\n'
            f"{ddg_abstract}"
        )

    # ── Step 3: Nothing found — give helpful guidance ─────────────────────────
    context_parts = [p for p in [uploader, title] if p and p.lower() not in ("none", "unknown")]
    context = " — ".join(context_parts) if context_parts else None

    if is_song_q and transcript_text:
        snippet = transcript_text.strip()[:120]
        return (
            f'🌐 Could not automatically identify this song.\n\n'
            f'Lyrics detected: "{snippet}..."\n\n'
            f"Try searching manually:\n"
            f'• Google: https://www.google.com/search?q={urllib.parse.quote(snippet + " lyrics song")}\n'
            f'• Genius: https://genius.com/search?q={urllib.parse.quote(snippet)}\n'
            f'• Shazam or SoundHound apps can identify songs by playing audio.'
        )

    manual_q = urllib.parse.quote(primary_query)
    return (
        f'🌐 No results found for: "{question}".\n\n'
        + (f"Video: {context}\n\n" if context else "")
        + f"Try searching manually:\n"
        f"• Google: https://www.google.com/search?q={manual_q}\n"
        f"• Wikipedia: https://en.wikipedia.org/w/index.php?search={manual_q}"
    )
