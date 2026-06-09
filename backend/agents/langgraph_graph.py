import os, json, re, time
from types import SimpleNamespace
from typing import Optional
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("🚨 GEMINI_API_KEY not found in .env")

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
        return {"chat_history": self.chat_history}

memory = SimpleMemory()

# -------------------- helpers --------------------
def _extract_json_from_text(text: str):
    if not text or not isinstance(text, str): return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    data = match.group(1) if match else cleaned
    try:
        return json.loads(data)
    except:
        return None

# -------------------- NODES --------------------
def explain_node(state, *_):
    topic = getattr(state, "topic", "general knowledge")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.5, google_api_key=GEMINI_API_KEY)
    prompt = f"Explain {topic} clearly for a student in 3-4 short points with one example."
    try:
        response = llm.invoke(prompt)
        explanation = getattr(response, "content", str(response))
    except Exception as e:
        explanation = f"⚠️ Error generating explanation: {e}"

    memory.save_context({"user": f"explain:{topic}"}, {"assistant": explanation})
    return {"explanation": explanation}


def quiz_node(state, *_):
    topic = getattr(state, "topic", "general knowledge")
    num_questions = getattr(state, "num_questions", 4)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.6, google_api_key=GEMINI_API_KEY)

    def generate():
        prompt = (
            f"Generate EXACTLY {num_questions} quiz questions about '{topic}'. "
            "Return ONLY JSON array of {'question': ..., 'explanation': ...}."
        )
        res = llm.invoke(prompt)
        return _extract_json_from_text(getattr(res, "content", str(res)))

    quiz = None
    for _ in range(3):
        quiz = generate()
        if isinstance(quiz, list) and len(quiz) == num_questions:
            break
        time.sleep(0.3)

    if not quiz or not isinstance(quiz, list):
        quiz = [{"question": f"Describe {topic}", "explanation": "General topic overview"}]

    memory.save_context({"user": f"quiz:{topic}"}, {"assistant": json.dumps(quiz)})
    return {"quiz": quiz}


def eval_node(state, *_):
    student_answers = getattr(state, "student_answers", [])
    quiz = getattr(state, "quiz", None)

    # fetch from memory if missing
    if not quiz:
        mem = memory.load_memory_variables({})
        hist = mem.get("chat_history", [])
        for msg in reversed(hist):
            content = getattr(msg, "content", str(msg))
            data = _extract_json_from_text(content)
            if isinstance(data, list):
                quiz = data
                break

    if not quiz:
        return {"evaluation": {"score": 0, "total": 0, "feedback": ["No quiz found."]}}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, google_api_key=GEMINI_API_KEY)
    prompt = (
        f"Grade these answers. Return JSON: "
        f"{{'score': int, 'total': int, 'feedback': [{{'question': str, 'student_answer': str, 'result': '✅/❌', 'comment': str}}]}}.\n"
        f"QUIZ: {json.dumps(quiz)}\nANSWERS: {json.dumps(student_answers)}"
    )
    try:
        resp = llm.invoke(prompt)
        evaluation = _extract_json_from_text(getattr(resp, "content", str(resp)))
    except:
        evaluation = None

    if not evaluation:
        evaluation = {
            "score": 0,
            "total": len(quiz),
            "feedback": [
                {"question": q.get("question"), "student_answer": student_answers[i] if i < len(student_answers) else "",
                 "result": "❌", "comment": q.get("explanation", "")}
                for i, q in enumerate(quiz)
            ],
        }

    memory.save_context({"user": "evaluation"}, {"assistant": json.dumps(evaluation)})
    return {"evaluation": evaluation}


def recall_node(state, *_):
    """Fetch last quiz from memory."""
    mem = memory.load_memory_variables({})
    hist = mem.get("chat_history", [])
    for msg in reversed(hist):
        text = getattr(msg, "content", str(msg))
        quiz = _extract_json_from_text(text)
        if isinstance(quiz, list):
            return {"quiz": quiz}
    return {"quiz": [{"question": "⚠️ No previous quiz found.", "explanation": ""}]}

# -------------------- BUILD --------------------
def build_graphs():
    class StudyState(BaseModel):
        topic: str
        num_questions: Optional[int] = 4
        student_answers: Optional[list] = None
        quiz: Optional[list] = None
        explanation: Optional[str] = None
        evaluation: Optional[dict] = None

    # --- Individual Graphs ---
    explain_graph = StateGraph(StudyState)
    explain_graph.add_node("explain", explain_node)
    explain_graph.add_edge(START, "explain")
    explain_graph.add_edge("explain", END)
    explain_graph = explain_graph.compile()

    quiz_graph = StateGraph(StudyState)
    quiz_graph.add_node("quiz", quiz_node)
    quiz_graph.add_edge(START, "quiz")
    quiz_graph.add_edge("quiz", END)
    quiz_graph = quiz_graph.compile()

    eval_graph = StateGraph(StudyState)
    eval_graph.add_node("evaluate", eval_node)
    eval_graph.add_edge(START, "evaluate")
    eval_graph.add_edge("evaluate", END)
    eval_graph = eval_graph.compile()

    recall_graph = StateGraph(StudyState)
    recall_graph.add_node("recall", recall_node)
    recall_graph.add_edge(START, "recall")
    recall_graph.add_edge("recall", END)
    recall_graph = recall_graph.compile()

    # --- Full Workflow Graph ---
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
        "full": full_graph,
    }
