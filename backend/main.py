from backend.database import init_db
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from backend.agents.langgraph_graph import (
    build_graphs,
    memory
)

from backend.nlu import parse_user_input

app = FastAPI(
    title="Study Assistant Multi-Agent System"
)

init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphs = build_graphs()

# ---------------- REQUEST MODEL ----------------

class StudyRequest(BaseModel):
    user_input: str

    student_answers: list[str] = []

    num_questions: Optional[int] = None

    quiz: Optional[list] = None


# ---------------- MAIN ENDPOINT ----------------

@app.post("/process/")
def process_user_input(request: StudyRequest):

    try:
        parsed = parse_user_input(
            request.user_input
        )

        intent = parsed["intent"]

        topic = parsed["topic"]

        difficulty = parsed.get(
            "difficulty",
            "medium"
        )

        num_questions = (
            request.num_questions
            or parsed["num_questions"]
            or 4
        )

        payload = {
            "topic": topic,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "student_answers": request.student_answers,
            "quiz": request.quiz,
        }

        # -------- ROUTING --------

        if intent == "explain":

            result = graphs["explain"].invoke(
                payload
            )

        elif intent == "quiz":

            result = graphs["quiz"].invoke(
                payload
            )

        elif intent == "evaluate":

            result = graphs["evaluate"].invoke(
                payload
            )

        elif intent == "recall":

            result = graphs["recall"].invoke(
                payload
            )

        else:

            result = graphs["full"].invoke(
                payload
            )

        return {
            "intent": intent,
            "topic": topic,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "result": result,
            "message":
                f"Intent={intent} | "
                f"Topic={topic} | "
                f"Difficulty={difficulty}"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Internal Error: {e}"
        )


# ---------------- HEALTH CHECK ----------------

@app.get("/")
def root():

    return {
        "message":
        "✅ Study Assistant Backend running."
    }


# ---------------- MEMORY VIEW ----------------

@app.get("/memory")
def show_memory():

    return {
        "chat_history":
        memory.load_memory_variables({})
    }