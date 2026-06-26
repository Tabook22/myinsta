import re
from collections import Counter
from dataclasses import dataclass


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+|[\u0600-\u06ff]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?\u061f])\s+")

_STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been",
    "before", "being", "but", "can", "could", "did", "does", "doing",
    "done", "for", "from", "get", "got", "had", "has", "have", "how",
    "into", "just", "like", "make", "many", "more", "much", "not", "now",
    "one", "only", "our", "out", "over", "really", "see", "should",
    "some", "take", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "through", "time", "use", "was",
    "way", "what", "when", "where", "which", "who", "why", "will",
    "with", "would", "you", "your",
}

_DOMAIN_KEYWORDS = {
    "AI": {"ai", "model", "prompt", "agent", "automation", "data", "training", "machine"},
    "Software Engineering": {"code", "software", "system", "api", "backend", "frontend", "architecture", "debug"},
    "Business": {"business", "customer", "market", "sales", "revenue", "strategy", "cost", "value"},
    "Product Development": {"product", "user", "feature", "design", "workflow", "prototype", "mvp"},
    "Leadership": {"team", "leader", "decision", "management", "culture", "communication"},
    "Education": {"learn", "teach", "student", "lesson", "course", "knowledge", "study"},
    "Personal Productivity": {"habit", "focus", "time", "productivity", "routine", "priority"},
    "Entrepreneurship": {"startup", "founder", "risk", "opportunity", "launch", "build"},
}


@dataclass(frozen=True)
class Idea:
    title: str
    sentence: str
    keywords: list[str]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _words(text: str) -> list[str]:
    return [word.lower() for word in _WORD_RE.findall(text or "")]


def _content_words(text: str) -> list[str]:
    return [
        word for word in _words(text)
        if len(word) > 2 and word not in _STOPWORDS
    ]


def _sentences(full_text: str, segments: list[dict] | None = None) -> list[str]:
    if segments:
        items = [_normalize(str(segment.get("text") or "")) for segment in segments]
    else:
        items = [_normalize(item) for item in _SENTENCE_RE.split(full_text or "")]

    sentences: list[str] = []
    for item in items:
        if not item:
            continue
        if len(item.split()) > 45:
            chunks = item.split(", ")
            sentences.extend(_normalize(chunk) for chunk in chunks if _normalize(chunk))
        else:
            sentences.append(item)
    return sentences


def _sentence_score(sentence: str, frequencies: Counter[str]) -> int:
    return sum(frequencies[word] for word in set(_content_words(sentence)))


def _shorten(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return f"{' '.join(words[:max_words]).rstrip(' ,;:')}..."


def _idea_title(sentence: str, keywords: list[str]) -> str:
    if keywords:
        return " ".join(word.capitalize() for word in keywords[:4])
    return _shorten(sentence, 6).rstrip(".")


def _extract_ideas(sentences: list[str], max_items: int = 6) -> list[Idea]:
    frequencies = Counter(_content_words(" ".join(sentences)))
    ranked = sorted(
        sentences,
        key=lambda item: (_sentence_score(item, frequencies), len(_content_words(item))),
        reverse=True,
    )

    ideas: list[Idea] = []
    used_keywords: set[str] = set()
    for sentence in ranked:
        keywords = [word for word, _ in Counter(_content_words(sentence)).most_common(5)]
        if not keywords:
            continue
        overlap = len(set(keywords) & used_keywords)
        if ideas and overlap >= min(3, len(keywords)):
            continue
        ideas.append(Idea(_idea_title(sentence, keywords), _shorten(sentence, 30), keywords))
        used_keywords.update(keywords)
        if len(ideas) >= max_items:
            break

    if not ideas and sentences:
        first = _shorten(sentences[0], 30)
        ideas.append(Idea("Core Message", first, _content_words(first)[:5]))
    return ideas


def _detect_domains(text: str) -> list[str]:
    words = set(_content_words(text))
    matches = [
        name for name, keywords in _DOMAIN_KEYWORDS.items()
        if words & keywords
    ]
    return matches or ["Education", "Personal Productivity"]


def _infer_audience(domains: list[str]) -> str:
    if "Software Engineering" in domains or "AI" in domains:
        return "technical builders, product-minded operators, and learners who want to turn the idea into practice"
    if "Business" in domains or "Entrepreneurship" in domains:
        return "founders, managers, operators, and professionals evaluating practical decisions"
    if "Education" in domains:
        return "learners, educators, and anyone studying the topic for later reuse"
    return "viewers who want a practical understanding of the topic rather than a passive summary"


def _quote_candidates(sentences: list[str], frequencies: Counter[str]) -> list[str]:
    ranked = sorted(sentences, key=lambda item: _sentence_score(item, frequencies), reverse=True)
    quotes: list[str] = []
    for sentence in ranked:
        word_count = len(sentence.split())
        if 6 <= word_count <= 24:
            quotes.append(sentence.strip("\" "))
        if len(quotes) >= 4:
            break
    return quotes


def _section(title: str, body: list[str]) -> str:
    return f"## {title}\n\n" + "\n\n".join(item for item in body if item).strip()


def build_professional_review(
    full_text: str,
    segments: list[dict] | None = None,
    *,
    title: str | None = None,
    description: str | None = None,
    platform: str | None = None,
    uploader: str | None = None,
    duration_seconds: float | None = None,
) -> str:
    """Create a grounded professional knowledge document from a transcript.

    This is deterministic and local-first. It organizes the transcript and adds
    evidence-aware critical framing, but it does not claim external fact-checking.
    """
    transcript = _normalize(full_text)
    if not transcript:
        raise ValueError("Transcript is empty.")

    sentences = _sentences(transcript, segments)
    ideas = _extract_ideas(sentences)
    frequencies = Counter(_content_words(transcript))
    domains = _detect_domains(" ".join([transcript, description or "", title or ""]))
    audience = _infer_audience(domains)
    word_count = len(transcript.split())
    duration = f"{round(duration_seconds / 60, 1)} minutes" if duration_seconds else "unknown duration"
    source = platform.capitalize() if platform else "Video"
    label = title or "Untitled video"
    speaker = uploader or "the speaker"

    executive_summary = (
        f"This {source} video, `{label}`, appears to focus on "
        f"{', '.join(idea.title.lower() for idea in ideas[:3])}. The transcript is about "
        f"{word_count} words from a {duration} recording, so this review should be read as a "
        "grounded study aid rather than an external fact-check. It matters because the speaker "
        f"is trying to preserve or explain ideas that can be reused later by {audience}. "
        "The strongest takeaways are the recurring themes, the practical decisions implied by "
        "those themes, and the places where the transcript does not provide enough evidence to "
        "treat claims as established facts."
    )

    context = [
        f"**Overall purpose:** Help the viewer understand and reuse the main ideas in `{label}`.",
        f"**Speaker objective:** {speaker} appears to be explaining, persuading, teaching, or preserving practical knowledge around the topic.",
        f"**Likely target audience:** {audience}.",
        "**Evidence note:** This review is based only on the saved transcript and metadata. If the transcript is incomplete or contains Whisper errors, the analysis should be checked against the original video.",
    ]

    main_ideas = [
        f"{index}. **{idea.title}** - {idea.sentence}"
        for index, idea in enumerate(ideas, start=1)
    ]

    deep_sections: list[str] = []
    for index, idea in enumerate(ideas, start=1):
        keyword_text = ", ".join(idea.keywords[:5]) or "the core topic"
        deep_sections.append(
            "\n".join([
                f"### {index}. {idea.title}",
                "",
                f"**Explanation:** The transcript highlights this idea through the statement: \"{idea.sentence}\". In practical terms, the idea centers on {keyword_text}.",
                "",
                "**Why It Matters:** This matters because it points to a concrete problem, decision, or learning objective that the speaker wants the viewer to notice. It helps convert a passing video moment into reusable knowledge.",
                "",
                "**Practical Applications:** Use this idea as a checklist item when reviewing a project, lesson, product decision, or personal workflow. For example, a software team could turn it into an acceptance criterion; a learner could turn it into a study note; a founder could turn it into a customer or product hypothesis.",
                "",
                "**Key Lessons:**",
                f"- Preserve the idea in your own words: {idea.sentence}",
                "- Separate what the speaker claims from what the transcript proves.",
                "- Look for a next action, not only an interesting observation.",
                "",
                "**Advantages:** The idea is easy to reuse because it appears as a clear theme in the transcript and can be connected to practical decisions.",
                "",
                "**Possible Limitations:** The transcript may not include enough detail, examples, counterarguments, or data to prove the idea in every context.",
                "",
                "**Real-World Examples:** In product development, this could become a design principle. In education, it could become a lesson objective. In business, it could become a decision rule or a customer interview question.",
                "",
                "**Critical Analysis:** The idea is logically useful if the surrounding transcript supports it with reasons or examples. If the transcript only states it briefly, it should be treated as a hypothesis that needs more evidence.",
                "",
                "**Professional Opinion:** I agree with using this idea as a working insight when it is tied to observable evidence or practical testing. I would not treat it as a universal rule unless the original video or outside sources provide stronger support.",
            ])
        )

    hidden_insights = [
        "- The video is useful not only for its explicit statements, but for the decisions and habits it suggests.",
        "- The strongest value comes from converting short-form content into durable notes, action items, and questions.",
        "- If the speaker gives advice without evidence, the viewer should preserve the idea but verify it before acting on it.",
    ]

    immediate = [
        "- Save the main ideas as notes attached to this video.",
        "- Copy the strongest quote or claim into your study/work journal.",
        "- Mark any unsupported claim that needs checking against the original video or external sources.",
    ]
    short_term = [
        "- Turn the top ideas into a small checklist or learning plan.",
        "- Ask follow-up questions in transcript chat to locate supporting passages.",
        "- Compare this video with another saved video on the same topic.",
    ]
    long_term = [
        "- Build a personal library of recurring ideas across creators and platforms.",
        "- Review saved videos monthly and convert repeated themes into projects or decisions.",
        "- Add external evidence before using a video claim for important technical, business, or educational choices.",
    ]

    quotes = [
        f"- \"{quote}\" - This matters because it captures a high-signal statement from the transcript."
        for quote in _quote_candidates(sentences, frequencies)
    ] or ["- No short memorable quote was detected. Review the original transcript for quotable language."]

    mistakes = [
        "- Treating a transcript summary as proof rather than as a starting point for understanding.",
        "- Ignoring transcription errors, missing context, or unclear speaker intent.",
        "- Applying advice universally when the transcript only supports it in a narrow context.",
    ]

    connections = [
        f"**{domain}:** The transcript connects to this category through recurring language and practical implications."
        for domain in domains
    ]

    conclusion = [
        "**Three most important lessons:**",
        *(f"{index}. {idea.title}: {idea.sentence}" for index, idea in enumerate(ideas[:3], start=1)),
        "",
        f"**Single biggest takeaway:** The video is most valuable as a reusable knowledge object about {ideas[0].title.lower() if ideas else 'the topic'}, not just as something to watch once.",
        f"**Who benefits most:** {audience}.",
        "**Worth watching:** Yes, if the viewer wants the speaker's original delivery, examples, and nuance; the review is best used as a study companion.",
        "**Final professional assessment:** The transcript contains useful themes, but unsupported claims should be verified before they guide high-stakes decisions.",
    ]

    return "\n\n".join([
        f"# Professional Transcript Review: {label}",
        _section("1. Read and Understand", context),
        _section("2. Executive Summary", [executive_summary]),
        _section("3. Main Ideas", main_ideas),
        _section("4. Deep Analysis of Each Main Idea", deep_sections),
        _section("5. Hidden Insights", hidden_insights),
        _section("6. Actionable Takeaways", [
            "### Immediate Actions\n" + "\n".join(immediate),
            "### Short-Term Actions\n" + "\n".join(short_term),
            "### Long-Term Strategies\n" + "\n".join(long_term),
        ]),
        _section("7. Quotes Worth Remembering", quotes),
        _section("8. Mistakes and Misconceptions", mistakes),
        _section("9. Connections", connections),
        _section("10. Final Conclusion", conclusion),
    ]).strip()
