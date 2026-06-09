import re

def parse_user_input(user_input: str):
    """
    Smarter NLU parser to detect:
    - intent: explain | quiz | evaluate | recall
    - topic: main subject
    - num_questions: integer count if present
    """

    text = user_input.lower().strip()

    # ----------- INTENT DETECTION -----------
    if any(w in text for w in ["explain", "tell me about", "what is", "define", "describe"]):
        intent = "explain"
    elif any(w in text for w in ["quiz", "test", "question", "questions", "mcq"]):
        intent = "quiz"
    elif any(w in text for w in ["evaluate", "check", "grade", "score"]):
        intent = "evaluate"
    elif any(w in text for w in ["last quiz", "previous quiz", "my quiz"]):
        intent = "recall"
    else:
        intent = "explain"

    # ----------- NUMBER DETECTION -----------
    num_match = re.search(r"(\d+)\s*(?:question|questions|mcq)", text)
    num_questions = int(num_match.group(1)) if num_match else 3

    # ----------- TOPIC EXTRACTION -----------
    topic = text

    intent_words = [
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
    ]

    for word in intent_words:
        topic = topic.replace(word, "")

    topic = re.sub(r"\d+", "", topic)
    topic = " ".join(topic.split())

    # Handle fallback
    if not topic:
        topic = "general knowledge"

    return {
        "intent": intent,
        "topic": topic,
        "num_questions": num_questions,
    }