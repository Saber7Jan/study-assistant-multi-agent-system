import re


def parse_user_input(user_input: str):
    """
    Detect:
    - intent
    - topic
    - num_questions
    - difficulty
    """

    text = user_input.lower().strip()

    # ---------------- INTENT DETECTION ----------------

    if any(w in text for w in [
    "recall",
    "last quiz",
    "previous quiz",
    "my quiz",
    "show quiz",
    "recall quiz"
]):
     intent = "recall"

    elif any(w in text for w in [
        "evaluate",
        "check",
        "grade",
        "score"
    ]):
        intent = "evaluate"

    elif any(w in text for w in [
        "adaptive",
        "progress",
        "recommendation",
        "recommend",
        "performance"
    ]):
        intent = "adaptive"

    elif any(w in text for w in [
        "quiz",
        "test",
        "question",
        "questions",
        "mcq"
    ]):
        intent = "quiz"

    elif any(w in text for w in [
        "explain",
        "tell me about",
        "what is",
        "define",
        "describe"
    ]):
        intent = "explain"

    else:
        intent = "explain"

    # ---------------- NUMBER DETECTION ----------------

    num_match = re.search(
        r"(\d+)\s*(?:question|questions|mcq)",
        text
    )

    num_questions = (
        int(num_match.group(1))
        if num_match
        else 3
    )

    # ---------------- DIFFICULTY DETECTION ----------------

    if any(word in text for word in [
        "easy",
        "beginner",
        "simple"
    ]):
        difficulty = "easy"

    elif any(word in text for word in [
        "hard",
        "advanced",
        "difficult"
    ]):
        difficulty = "hard"

    else:
        difficulty = "medium"

    # ---------------- TOPIC EXTRACTION ----------------

    topic = text

    removable_words = [
        "explain",
        "tell me about",
        "what is",
        "define",
        "describe",

        "quiz",
        "test",
        "question",
        "questions",
        "mcq",

        "evaluate",
        "check",
        "grade",
        "score",

        "adaptive",
        "progress",
        "recommendation",
        "recommend",
        "performance",

        "easy",
        "hard",
        "medium",
        "beginner",
        "simple",
        "advanced",
        "difficult",

        "last quiz",
        "previous quiz",
        "my quiz",
        "show quiz",
        "recall quiz",

        "show",
        "last",
        "previous",
        "my",
        "recall"
    ]

    removable_words.sort(key=len, reverse=True)

    for word in removable_words:
        topic = re.sub(
            rf"\b{re.escape(word)}\b",
            "",
            topic
        )

    topic = re.sub(r"\d+", "", topic)

    filler_words = [
        "on",
        "about",
        "with",
        "for",
        "of",
        "the",
        "a",
        "an"
    ]

    for word in filler_words:
        topic = re.sub(
            rf"\b{re.escape(word)}\b",
            "",
            topic
        )

    topic = " ".join(topic.split())

    if not topic:
        topic = "general knowledge"

    return {
        "intent": intent,
        "topic": topic,
        "num_questions": num_questions,
        "difficulty": difficulty,
    }