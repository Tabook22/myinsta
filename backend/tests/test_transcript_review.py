import pytest

from app.services.transcript_review import build_professional_review


def test_professional_review_contains_required_sections():
    review = build_professional_review(
        """
        Product teams should start with the user's real workflow. If the workflow
        is unclear, the team should interview users before building features.
        A small prototype can reveal whether the idea solves a real problem.
        Engineers should keep the first version simple and measure what changes.
        """,
        title="Building useful products",
        platform="youtube",
        uploader="Example Speaker",
        duration_seconds=120,
    )

    assert "# Professional Transcript Review: Building useful products" in review
    assert "## 2. Executive Summary" in review
    assert "## 3. Main Ideas" in review
    assert "## 4. Deep Analysis of Each Main Idea" in review
    assert "**Critical Analysis:**" in review
    assert "**Professional Opinion:**" in review
    assert "## 10. Final Conclusion" in review


def test_professional_review_is_evidence_aware():
    review = build_professional_review(
        "This tool will improve productivity. Teams should test it with real users.",
        title="Short claim",
    )

    assert "based only on the saved transcript" in review
    assert "unsupported claims should be verified" in review


def test_professional_review_rejects_empty_transcript():
    with pytest.raises(ValueError, match="Transcript is empty"):
        build_professional_review("   ")
