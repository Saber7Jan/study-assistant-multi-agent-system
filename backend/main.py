from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from backend.agents.langgraph_graph import build_graphs, memory
from backend.nlu import parse_user_input

app = FastAPI(title="Study Assistant Multi-Agent System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graphs = build_graphs()

class StudyRequest(BaseModel):
    user_input: str
    student_answers: list[str] = []
    num_questions: Optional[int] = None
    quiz: Optional[list] = None

@app.post("/process/")
def process_user_input(request: StudyRequest):
    try:
        parsed = parse_user_input(request.user_input)
        intent = parsed["intent"]
        topic = parsed["topic"]
        num = request.num_questions or parsed["num_questions"] or 4

        if intent == "explain":
            graph, payload = graphs["explain"], {"topic": topic}

        elif intent == "quiz":
            graph, payload = graphs["quiz"], {"topic": topic, "num_questions": num}

        elif intent == "evaluate":
            graph, payload = graphs["evaluate"], {"topic": topic, "student_answers": request.student_answers, "quiz": request.quiz}

        elif intent == "recall":
            graph, payload = graphs["recall"], {"topic": topic}

        else:
            graph, payload = graphs["full"], {"topic": topic, "num_questions": num, "student_answers": request.student_answers}

        result = graph.invoke(payload)
        message = f"🧭 Intent: {intent} | 🧩 Topic: {topic}" + (f" | 🧮 Questions: {num}" if intent == 'quiz' else "")

        return {"intent": intent, "topic": topic, "num_questions": num, "result": result, "message": message}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")

@app.get("/")
def root():
    return {"message": "✅ Study Assistant Backend running with persistent memory."}

@app.get("/memory")
def show_memory():
    return {"chat_history": memory.load_memory_variables({})}
