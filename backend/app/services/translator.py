import json
import re
import urllib.parse
import urllib.request


_ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
_CHUNK_SIZE = 4500


def _split_text(text: str, chunk_size: int = _CHUNK_SIZE) -> list[str]:
    paragraphs = re.split(r"(\n+)", text)
    chunks: list[str] = []
    current = ""

    def push_current() -> None:
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for part in paragraphs:
        if len(part) > chunk_size:
            push_current()
            for start in range(0, len(part), chunk_size):
                chunks.append(part[start:start + chunk_size])
            continue
        if len(current) + len(part) > chunk_size:
            push_current()
        current += part

    push_current()
    return chunks


def looks_arabic(text: str) -> bool:
    if not text:
        return False
    letters = re.findall(r"[A-Za-z\u0600-\u06ff]", text)
    if not letters:
        return False
    arabic_letters = _ARABIC_RE.findall("".join(letters))
    return len(arabic_letters) / len(letters) >= 0.45


def _translate_chunk_to_arabic(text: str, source_language: str | None = None) -> str:
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": source_language or "auto",
            "tl": "ar",
            "dt": "t",
            "q": text,
        }
    )
    request = urllib.request.Request(
        f"https://translate.googleapis.com/translate_a/single?{params}",
        headers={"User-Agent": "MyInsta/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    pieces = []
    for item in data[0] or []:
        if item and item[0]:
            pieces.append(item[0])
    return "".join(pieces)


def translate_to_arabic(text: str, source_language: str | None = None) -> str:
    """Translate transcript text into Arabic using a lightweight web translator."""
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Transcript is empty.")
    if looks_arabic(clean_text):
        return clean_text

    translated = [
        _translate_chunk_to_arabic(chunk, source_language)
        for chunk in _split_text(clean_text)
    ]
    return "".join(translated).strip()
