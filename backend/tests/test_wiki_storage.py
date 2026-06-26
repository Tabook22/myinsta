from datetime import datetime, timezone

from app.services.wiki_storage import (
    build_wiki_markdown,
    delete_wiki_file,
    make_wiki_filename,
    write_wiki_markdown,
)


def test_make_wiki_filename_includes_timestamp_video_id_and_slug():
    filename = make_wiki_filename(
        42,
        "How to Choose Motor KV",
        datetime(2026, 6, 26, 10, 11, 12, tzinfo=timezone.utc),
    )

    assert filename == "20260626_101112_video-42_how-to-choose-motor-kv.md"


def test_build_wiki_markdown_contains_transcript_review_notes_and_discussion():
    markdown = build_wiki_markdown(
        video={
            "id": 7,
            "title": "Useful video",
            "platform": "youtube",
            "uploader": "Creator",
            "source_url": "https://example.com/video",
            "duration_seconds": 123,
            "storage_folder": "2026/06/example",
            "description": "A practical description.",
            "notes": "<p>Personal note</p>",
            "tags": ["ai", "study"],
        },
        transcript={
            "full_text": "Original transcript text.",
            "cleaned_text": "Cleaned transcript text.",
            "professional_review": "Professional review text.",
        },
        messages=[
            {"role": "user", "content": "What is the main idea?", "created_at": "2026-06-26 10:00:00"},
            {"role": "assistant", "content": "The main idea is preservation.", "created_at": "2026-06-26 10:00:01"},
        ],
    )

    assert "# Useful video" in markdown
    assert "## Professional Summary and Review" in markdown
    assert "Professional review text." in markdown
    assert "## Original Transcript" in markdown
    assert "Original transcript text." in markdown
    assert "Personal note" in markdown
    assert "### User - 2026-06-26 10:00:00" in markdown
    assert "The main idea is preservation." in markdown


def test_write_and_delete_wiki_markdown(tmp_path):
    path = tmp_path / "mywiki" / "video.md"

    write_wiki_markdown(path, "# Video\n")
    assert path.read_text(encoding="utf-8") == "# Video\n"

    delete_wiki_file(path)
    assert not path.exists()
