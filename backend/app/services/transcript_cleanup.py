import re


_REPEATED_WORD_RE = re.compile(r"\b([\w'\u0600-\u06ff]+)(\s+\1\b)+", re.IGNORECASE)
_REPEATED_PHRASE_RE = re.compile(
    r"\b((?:[\w'\u0600-\u06ff]+[\s,;:]+){1,4}[\w'\u0600-\u06ff]+)(?:[\s,;:]+\1\b)+",
    re.IGNORECASE,
)
_SENTENCE_END_RE = re.compile(r"[.!?\u061f]\s*$")
_SPLIT_AFTER_RE = re.compile(
    r"\b(and then|then|but|so|because|after that|next|finally|what to do|"
    r"لكن|ثم|بعد ذلك|لذلك|وأخيراً|واخيرا)\b",
    re.IGNORECASE,
)


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _remove_repeats(text: str) -> str:
    previous = None
    current = text
    while previous != current:
        previous = current
        current = _REPEATED_WORD_RE.sub(r"\1", current)
        current = _REPEATED_PHRASE_RE.sub(r"\1", current)
    return current


def _sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _finish_sentence(text: str) -> str:
    text = text.strip(" ,;:")
    if not text:
        return ""
    if _SENTENCE_END_RE.search(text):
        return _sentence_case(text)
    return f"{_sentence_case(text)}."


def _split_long_text(text: str, max_words: int = 28) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]

    sentences: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        joined = " ".join(current)
        should_split = len(current) >= max_words and (
            _SPLIT_AFTER_RE.search(joined) or len(current) >= max_words + 12
        )
        if should_split:
            sentences.append(" ".join(current))
            current = []

    if current:
        sentences.append(" ".join(current))
    return sentences


def _speaker_label(segment: dict) -> str | None:
    for key in ("speaker", "speaker_label", "speaker_id"):
        value = segment.get(key)
        if value:
            label = str(value).strip()
            if label:
                return label if label.lower().startswith("speaker") else f"Speaker {label}"
    return None


def _chunks_from_segments(segments: list[dict] | None) -> list[tuple[str | None, str]]:
    chunks: list[tuple[str | None, str]] = []
    for segment in segments or []:
        text = _normalize_spaces(str(segment.get("text") or ""))
        if text:
            chunks.append((_speaker_label(segment), text))
    return chunks


def _chunks_from_text(text: str) -> list[tuple[str | None, str]]:
    rough_sentences = re.split(r"(?<=[.!?\u061f])\s+", text)
    chunks: list[tuple[str | None, str]] = []
    for sentence in rough_sentences:
        cleaned = _normalize_spaces(sentence)
        if cleaned:
            chunks.extend((None, item) for item in _split_long_text(cleaned))
    return chunks


def clean_transcript_text(full_text: str, segments: list[dict] | None = None) -> str:
    """Make Whisper transcript text easier to read without external AI calls."""
    source = _normalize_spaces(full_text or "")
    if not source:
        raise ValueError("Transcript is empty.")

    chunks = _chunks_from_segments(segments) or _chunks_from_text(source)
    sentences: list[str] = []
    current_speaker: str | None = None

    for speaker, chunk in chunks:
        cleaned = _finish_sentence(_remove_repeats(chunk))
        if not cleaned:
            continue
        if speaker and speaker != current_speaker:
            sentences.append(f"{speaker}: {cleaned}")
            current_speaker = speaker
        elif speaker:
            sentences.append(cleaned)
        else:
            sentences.append(cleaned)

    paragraphs = []
    for index in range(0, len(sentences), 3):
        paragraphs.append(" ".join(sentences[index:index + 3]))

    return "\n\n".join(paragraphs).strip()
