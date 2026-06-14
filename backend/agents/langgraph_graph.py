from backend.database import (
    save_quiz,
    get_latest_quiz,
    save_evaluation,
    get_latest_evaluation,
    get_recommended_difficulty
)

import os
import json
import re
import time
from types import SimpleNamespace
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("🚨 GEMINI_API_KEY not found in .env")


# ---------------- MEMORY ----------------

class SimpleMemory:
    def __init__(self):
        self.chat_history = []

    def save_context(self, inputs, outputs):
        self.chat_history.append(
            SimpleNamespace(
                content=list(outputs.values())[0]
            )
        )

    def load_memory_variables(self, _):
        return {
            "chat_history": self.chat_history
        }


memory = SimpleMemory()


# ---------------- HELPERS ----------------

def _extract_json_from_text(text: str):
    if not text:
        return None

    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        text.strip(),
        flags=re.I
    )

    match = re.search(
        r"(\[.*\]|\{.*\})",
        cleaned,
        re.DOTALL
    )

    data = match.group(1) if match else cleaned

    try:
        return json.loads(data)
    except Exception:
        return None


# ---------------- EXPLAIN NODE ----------------

def explain_node(state, *_):

    topic = getattr(
        state,
        "topic",
        "general knowledge"
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.5,
        google_api_key=GEMINI_API_KEY
    )

    prompt = (
        f"Explain {topic} clearly for a student "
        f"in 3-4 short points with one example."
    )

    try:
        response = llm.invoke(prompt)

        explanation = getattr(
            response,
            "content",
            str(response)
        )

    except Exception as e:
        explanation = (
            f"⚠️ Error generating explanation: {e}"
        )

    memory.save_context(
        {"user": f"explain:{topic}"},
        {"assistant": explanation}
    )

    return {
        "explanation": explanation
    }


# ---------------- QUIZ NODE ----------------

def quiz_node(state, *_):

    topic = getattr(
        state,
        "topic",
        "general knowledge"
    )

    num_questions = getattr(
        state,
        "num_questions",
        4
    )

    difficulty = getattr(
        state,
        "difficulty",
        None
    )

    if not difficulty:
        difficulty = get_recommended_difficulty()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.6,
        google_api_key=GEMINI_API_KEY
    )

    def generate():

        prompt = f"""
Generate EXACTLY {num_questions} {difficulty.upper()} level quiz questions about "{topic}".

Rules:
- Easy = basic definitions and simple concepts
- Medium = understanding and application
- Hard = analytical and problem-solving

Return ONLY valid JSON array.

Example:
[
  {{
    "question": "What is AI?",
    "answer": "Artificial Intelligence"
  }}
]
"""

        result = llm.invoke(prompt)

        return _extract_json_from_text(
            getattr(result, "content", str(result))
        )

    quiz = None

    for _ in range(3):

        quiz = generate()

        if (
            isinstance(quiz, list)
            and len(quiz) == num_questions
        ):
            break

        time.sleep(0.3)

    if not quiz:
         raise ValueError(
        f"Failed to generate quiz for topic: {topic}"
    )
    
    memory.save_context(
        {"user": f"quiz:{topic}:{difficulty}"},
        {"assistant": json.dumps(quiz)}
    )

    save_quiz(
        topic=topic,
        difficulty=difficulty,
        quiz=quiz
    )

    return {
        "quiz": quiz
    }


# ---------------- EVALUATION NODE ----------------

def eval_node(state, *_):

    topic = getattr(
        state,
        "topic",
        "general knowledge"
    )

    student_answers = getattr(
        state,
        "student_answers",
        []
    )

    quiz = getattr(
        state,
        "quiz",
        None
    )

    if not quiz:

        latest_quiz = get_latest_quiz()

        if latest_quiz:

            quiz = latest_quiz

        else:

            return {
                "evaluation": {
                    "score": 0,
                    "total": 0,
                    "feedback": [
                        "No quiz found."
                    ]
                }
            }

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        google_api_key=GEMINI_API_KEY
    )

    prompt = f"""
Grade the student's answers.

Return ONLY valid JSON:

{{
  "score": integer,
  "total": integer,
  "feedback": [
    {{
      "question": "...",
      "student_answer": "...",
      "result": "✅ Correct",
      "comment": "short feedback"
    }}
  ]
}}

QUIZ:
{json.dumps(quiz)}

ANSWERS:
{json.dumps(student_answers)}
"""

    try:

        response = llm.invoke(prompt)

        evaluation = _extract_json_from_text(
            getattr(response, "content", str(response))
        )

    except Exception:

        evaluation = None

    if not evaluation:

        evaluation = {
            "score": 0,
            "total": len(quiz),
            "feedback": []
        }

    score = evaluation.get("score", 0)
    total = max(evaluation.get("total", 1), 1)

    percentage = (score / total) * 100

    if percentage < 40:

        difficulty = "easy"
        recommendation = "Try EASY questions next."

    elif percentage < 80:

        difficulty = "medium"
        recommendation = "Continue with MEDIUM questions."

    else:

        difficulty = "hard"
        recommendation = "Try HARD questions next."

    evaluation["percentage"] = round(
        percentage,
        2
    )

    evaluation["recommended_difficulty"] = difficulty

    evaluation["recommendation"] = recommendation

    memory.save_context(
        {"user": "evaluation"},
        {"assistant": json.dumps(evaluation)}
    )

    save_evaluation(
        topic=topic,
        score=score,
        total=total,
        evaluation=evaluation
    )

    return {
        "evaluation": evaluation
    }

# ---------------- RECALL NODE ----------------

def recall_node(state, *_):

    quiz = get_latest_quiz()

    if quiz:
        return {
            "quiz": quiz
        }

    return {
        "quiz": [
            {
                "question":
                "⚠️ No previous quiz found.",
                "answer": ""
            }
        ]
    }


# ---------------- BUILD GRAPHS ----------------

def build_graphs():

    class StudyState(BaseModel):
        topic: str
        difficulty: Optional[str] = None
        num_questions: Optional[int] = 4
        student_answers: Optional[list] = None
        quiz: Optional[list] = None
        explanation: Optional[str] = None
        evaluation: Optional[dict] = None

    # Explain
    explain_graph = StateGraph(StudyState)
    explain_graph.add_node("explain", explain_node)
    explain_graph.add_edge(START, "explain")
    explain_graph.add_edge("explain", END)
    explain_graph = explain_graph.compile()

    # Quiz
    quiz_graph = StateGraph(StudyState)
    quiz_graph.add_node("quiz", quiz_node)
    quiz_graph.add_edge(START, "quiz")
    quiz_graph.add_edge("quiz", END)
    quiz_graph = quiz_graph.compile()

    # Evaluation
    eval_graph = StateGraph(StudyState)
    eval_graph.add_node("evaluate", eval_node)
    eval_graph.add_edge(START, "evaluate")
    eval_graph.add_edge("evaluate", END)
    eval_graph = eval_graph.compile()

    # Recall
    recall_graph = StateGraph(StudyState)
    recall_graph.add_node("recall", recall_node)
    recall_graph.add_edge(START, "recall")
    recall_graph.add_edge("recall", END)
    recall_graph = recall_graph.compile()

       # Full workflow
    full_graph = StateGraph(StudyState)

    full_graph.add_node("explain", explain_node)
    full_graph.add_node("quiz", quiz_node)
    full_graph.add_node("evaluate", eval_node)

    full_graph.add_edge(START, "explain")
    full_graph.add_edge("explain", "quiz")
    full_graph.add_edge("quiz", "evaluate")
    full_graph.add_edge("evaluate", END)

    full_graph = full_graph.compile()

    return {
        "explain": explain_graph,
        "quiz": quiz_graph,
        "evaluate": eval_graph,
        "recall": recall_graph,
        "full": full_graph
    }