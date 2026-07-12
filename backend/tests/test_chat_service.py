from app.services.chat_service import answer_from_transcript, answer_hybrid


def test_answer_from_transcript_uses_relevant_segment():
    transcript = "We started with product design. Then we talked about marketing strategy for reels."
    segments = [
        {"text": "We started with product design.", "start": 0.0, "end": 3.0},
        {"text": "Then we talked about marketing strategy for reels.", "start": 3.0, "end": 8.0},
    ]

    answer = answer_from_transcript("What did they say about marketing?", transcript, segments)

    assert "marketing" in answer.lower()
    assert "[00:03]" in answer


def test_answer_from_transcript_summarizes_generic_question():
    transcript = "This video explains how to save Instagram reels locally and transcribe them."

    answer = answer_from_transcript("What is this video about?", transcript, None)

    assert "save instagram reels" in answer.lower()


def test_answer_hybrid_includes_transcript_and_web_sections():
    transcript = "This reel covers batch cooking healthy meals for the week."

    def fake_web(question, title=None, uploader=None, transcript_text=None, use_transcript_context=False):
        assert use_transcript_context is True
        return "Web says batch cooking saves time."

    answer = answer_hybrid(
        "What is this about?",
        transcript,
        None,
        title="Meal prep",
        web_search_fn=fake_web,
    )

    assert "From the transcript" in answer
    assert "From the web" in answer
    assert "batch cooking" in answer.lower()
    assert "saves time" in answer.lower()
