import re
from datetime import datetime, timezone
from pathlib import Path

from app.services.library_storage import slugify


def make_wiki_filename(video_id: int, title: str | None, when: datetime | None = None) -> str:
    when = when or datetime.now(timezone.utc)
    safe_title = slugify(title or f"video-{video_id}", max_len=60)
    return f"{when.strftime('%Y%m%d_%H%M%S')}_video-{video_id}_{safe_title}.md"


def _clean_html_notes(notes: str | None) -> str:
    if not notes:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", notes, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _metadata_line(label: str, value: object) -> str:
    if value is None or value == "":
        return f"- **{label}:** Not recorded"
    return f"- **{label}:** {value}"


def _discussion_markdown(messages: list[dict]) -> str:
    if not messages:
        return "No discussion has been saved for this video yet."

    lines: list[str] = []
    for item in messages:
        role = str(item.get("role") or "").capitalize() or "Message"
        created_at = item.get("created_at") or ""
        content = str(item.get("content") or "").strip()
        lines.append(f"### {role} - {created_at}".strip())
        lines.append("")
        lines.append(content or "_Empty message_")
        lines.append("")
    return "\n".join(lines).strip()


def build_wiki_markdown(
    *,
    video: dict,
    transcript: dict | None,
    messages: list[dict],
) -> str:
    title = video.get("title") or f"Video #{video['id']}"
    transcript_text = (transcript or {}).get("full_text") or ""
    professional_review = (transcript or {}).get("professional_review") or ""
    cleaned_text = (transcript or {}).get("cleaned_text") or ""
    notes = _clean_html_notes(video.get("notes"))
    tags = video.get("tags") or []
    if isinstance(tags, str):
        tags_text = tags
    else:
        tags_text = ", ".join(tags) if tags else "None"

    generated_at = datetime.now(timezone.utc).isoformat()
    sections = [
        f"# {title}",
        "## Metadata",
        "\n".join([
            _metadata_line("Video ID", video.get("id")),
            _metadata_line("Platform", video.get("platform")),
            _metadata_line("Creator", video.get("uploader")),
            _metadata_line("Source URL", video.get("source_url")),
            _metadata_line("Duration seconds", video.get("duration_seconds")),
            _metadata_line("Storage folder", video.get("storage_folder")),
            _metadata_line("Tags", tags_text),
            _metadata_line("Generated at", generated_at),
        ]),
        "## Description",
        video.get("description") or "No description saved.",
        "## Professional Summary and Review",
        professional_review or "No professional review has been generated yet.",
        "## Cleaned Transcript",
        cleaned_text or "No cleaned transcript has been generated yet.",
        "## Original Transcript",
        transcript_text or "No transcript is available.",
        "## My Notes",
        notes or "No personal notes saved yet.",
        "## Discussion History",
        _discussion_markdown(messages),
    ]
    return "\n\n".join(section.strip() for section in sections).strip() + "\n"


def write_wiki_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def delete_wiki_file(path: str | Path | None) -> None:
    if not path:
        return
    target = Path(path)
    if target.exists() and target.is_file():
        target.unlink()
