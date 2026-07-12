import json
import re

GENERIC_QUESTION_PATTERNS = (
    r"\bwhat is this\b",
    r"\bwhat's this\b",
    r"\babout\b",
    r"\bsummarize\b",
    r"\bsummary\b",
    r"\btell me\b",
    r"\bexplain\b",
    r"\boverview\b",
)

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "who", "how", "when", "where", "why", "which", "this", "that",
    "do", "does", "did", "can", "could", "would", "should", "will", "about",
    "in", "on", "at", "to", "for", "of", "and", "or", "it", "its", "me", "my",
    "you", "your", "video", "reel", "instagram", "tell", "say", "please",
}


def _tokenize(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9']+", text.lower()) if word not in STOPWORDS}


def _format_timestamp(seconds: float | None) -> str:
    if seconds is None:
        return ""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"[{minutes:02d}:{secs:02d}]"


def _is_generic_question(question: str) -> bool:
    lowered = question.lower()
    return any(re.search(pattern, lowered) for pattern in GENERIC_QUESTION_PATTERNS)


def _build_chunks(full_text: str, segments: list[dict] | None) -> list[dict]:
    if segments:
        chunks = []
        for segment in segments:
            text = (segment.get("text") or "").strip()
            if text:
                chunks.append(
                    {
                        "text": text,
                        "start": segment.get("start"),
                        "end": segment.get("end"),
                    }
                )
        if chunks:
            return chunks

    sentences = re.split(r"(?<=[.!?])\s+", full_text.strip())
    return [{"text": sentence.strip(), "start": None, "end": None} for sentence in sentences if sentence.strip()]


def answer_from_transcript(question: str, full_text: str, segments: list[dict] | None = None) -> str:
    """Answer a question using simple transcript retrieval (local, no vector DB)."""
    cleaned = full_text.strip()
    if not cleaned:
        return "This video does not have a transcript yet, so I cannot answer questions about it."

    question_words = _tokenize(question)
    chunks = _build_chunks(cleaned, segments)

    scored: list[tuple[int, dict]] = []
    for chunk in chunks:
        chunk_words = _tokenize(chunk["text"])
        overlap = len(question_words & chunk_words)
        if overlap:
            scored.append((overlap, chunk))

    if scored:
        ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:3]
        lines = [
            "Based on the transcript, here are the most relevant parts.",
            "Click a timestamp in the app to jump to that moment in the video.\n",
        ]
        for _, chunk in ranked:
            stamp = _format_timestamp(chunk.get("start"))
            if stamp:
                lines.append(f"{stamp} {chunk['text']}")
            else:
                lines.append(f"- {chunk['text']}")
        return "\n".join(lines)

    if _is_generic_question(question):
        # Prefer opening chunks with timestamps when available
        if chunks and chunks[0].get("start") is not None:
            lines = [
                "Based on the transcript, here is what this video covers:\n",
            ]
            for chunk in chunks[:5]:
                stamp = _format_timestamp(chunk.get("start"))
                text = chunk["text"]
                if len(text) > 220:
                    text = f"{text[:220].rstrip()}..."
                lines.append(f"{stamp} {text}" if stamp else f"- {text}")
            return "\n".join(lines)

        preview = cleaned if len(cleaned) <= 900 else f"{cleaned[:900].rstrip()}..."
        return (
            "Based on the transcript, here is what this video covers:\n\n"
            f"{preview}"
        )

    preview = cleaned if len(cleaned) <= 500 else f"{cleaned[:500].rstrip()}..."
    return (
        "I could not find an exact match for that question, but here is a transcript excerpt:\n\n"
        f"{preview}"
    )


def answer_hybrid(
    question: str,
    full_text: str,
    segments: list[dict] | None,
    *,
    title: str | None = None,
    uploader: str | None = None,
    web_search_fn=None,
) -> str:
    """
    Combine transcript-grounded retrieval with a web search answer.

    web_search_fn is injected to avoid circular imports (pass search_web).
    """
    transcript_part = answer_from_transcript(question, full_text, segments)

    if web_search_fn is None:
        web_part = "Web search is unavailable."
    else:
        web_part = web_search_fn(
            question,
            title=title,
            uploader=uploader,
            transcript_text=(full_text or None),
            use_transcript_context=True,
        )

    return (
        "📜 From the transcript\n"
        "────────────────────\n"
        f"{transcript_part}\n\n"
        "🌐 From the web\n"
        "────────────────────\n"
        f"{web_part}"
    )
