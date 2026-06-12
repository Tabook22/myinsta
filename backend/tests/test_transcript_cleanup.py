from app.services.transcript_cleanup import clean_transcript_text


def test_clean_transcript_removes_repeats_and_adds_paragraphs():
    text = (
        "hello hello this is a test and then we explain the feature "
        "it is useful useful for reels then we show the final result"
    )

    cleaned = clean_transcript_text(text)

    assert "hello hello" not in cleaned.lower()
    assert "useful useful" not in cleaned.lower()
    assert cleaned.startswith("Hello this is a test")
    assert cleaned.endswith(".")


def test_clean_transcript_keeps_speaker_labels_when_available():
    segments = [
        {"speaker": "1", "text": "hello hello welcome"},
        {"speaker": "2", "text": "thanks thanks for having me"},
    ]

    cleaned = clean_transcript_text("ignored when segments exist", segments)

    assert "Speaker 1: Hello welcome." in cleaned
    assert "Speaker 2: Thanks for having me." in cleaned
