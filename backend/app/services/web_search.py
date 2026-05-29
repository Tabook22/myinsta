"""Web search using the free DuckDuckGo Instant Answer API.

No API key required. Results are returned as plain text suitable for the chat response.
"""
import json
import urllib.parse
import urllib.request

_DDG_URL = "https://api.duckduckgo.com/"
_TIMEOUT = 8  # seconds


def _build_query(question: str, title: str | None, uploader: str | None) -> str:
    """Combine video context with the user question for a better search."""
    parts = []
    if uploader:
        parts.append(uploader)
    if title and title != uploader:
        parts.append(title)
    parts.append(question)
    return " ".join(parts)


def search_web(
    question: str,
    title: str | None = None,
    uploader: str | None = None,
) -> str:
    """Search DuckDuckGo and return a human-readable answer string."""
    query = _build_query(question, title, uploader)
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }
    )
    url = f"{_DDG_URL}?{params}"

    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "MyInsta/1.0 (web-search mode)"}
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return f"Web search is currently unavailable ({exc}). Try again later."

    lines: list[str] = []

    # Primary abstract (Wikipedia-style summary)
    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        source = data.get("AbstractSource") or "Web"
        lines.append(f"{abstract}\n\n— Source: {source}")

    # Definition (for simple queries)
    definition = (data.get("Definition") or "").strip()
    if definition and definition != abstract:
        def_source = data.get("DefinitionSource") or "Web"
        lines.append(f"{definition}\n\n— Source: {def_source}")

    # Related topics (up to 3)
    related = data.get("RelatedTopics") or []
    topic_lines: list[str] = []
    for topic in related[:4]:
        if isinstance(topic, dict):
            text = (topic.get("Text") or "").strip()
            if text:
                topic_lines.append(f"• {text}")
    if topic_lines:
        lines.append("Related:\n" + "\n".join(topic_lines))

    if lines:
        header = f'Web search results for: "{query}"\n\n'
        return header + "\n\n".join(lines)

    # Nothing found — fall back to a helpful message using video metadata
    if title or uploader:
        context = " — ".join(filter(None, [uploader, title]))
        return (
            f'No instant results found for "{query}".\n\n'
            f"Video context: {context}\n\n"
            "Try searching manually or rephrasing your question."
        )

    return (
        f'No web results found for "{query}". '
        "Try a more specific question or search manually."
    )
