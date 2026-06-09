import streamlit as st
import requests
import json
import time

API_URL = "http://127.0.0.1:8000/process/"

# -------------------- SESSION STATE INIT --------------------
if "quiz" not in st.session_state:
    st.session_state.quiz = []
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "mode" not in st.session_state:
    st.session_state.mode = None
if "intent" not in st.session_state:
    st.session_state.intent = ""
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "evaluation" not in st.session_state:
    st.session_state.evaluation = {}

st.title("📘 Study Assistant (LangGraph + FastAPI)")

# -------------------- MAIN INPUT --------------------
user_input = st.text_input("Enter your request:", key="user_prompt")

# Handle request safely
if st.button("Run Assistant"):
    with st.spinner("🤖 Thinking..."):
        try:
            res = requests.post(API_URL, json={"user_input": user_input, "student_answers": []})
            if res.status_code != 200:
                st.error(f"❌ Server Error: {res.status_code}")
                st.stop()
            data = res.json()
        except Exception as e:
            st.error(f"❌ Connection Error: {e}")
            st.stop()

    # Extract safely
    intent = data.get("intent", "")
    topic = data.get("topic", "")
    st.session_state.intent = intent
    st.session_state.topic = topic

    result = data.get("result", data)
    st.session_state.result = result

    # Display intent/topic info
    if intent:
        st.markdown(f"🧠 **Intent:** {intent.capitalize()}  |  🏷️ **Topic:** {topic}")

    # Handle explanation
    if intent == "explain" and "explanation" in result:
        st.session_state.mode = "explain"
        st.write(result.get("explanation", "No explanation found."))

    # Handle quiz
    elif intent == "quiz" and "quiz" in result:
        quiz_list = result.get("quiz", [])
        if not isinstance(quiz_list, list):
            try:
                quiz_list = json.loads(quiz_list)
            except Exception:
                quiz_list = [{"question": str(quiz_list)}]

        st.session_state.quiz = quiz_list
        st.session_state.mode = "quiz"
        st.session_state.current_q = 0
        st.session_state.answers = []

        st.success(f"📝 Quiz created with {len(quiz_list)} questions!")
        time.sleep(0.5)
        st.rerun()

    # Handle recall intent
    elif intent == "recall" and "quiz" in result:
        st.session_state.quiz = result.get("quiz", [])
        st.session_state.mode = "quiz"
        st.info("📚 Retrieved your last quiz from memory.")
        st.rerun()

    # Handle evaluation
    elif intent == "evaluate" and "evaluation" in result:
        st.session_state.mode = "evaluation"
        st.session_state.evaluation = result.get("evaluation", {})
        st.rerun()

    else:
        st.warning("🤔 No valid output received from backend.")

# -------------------- QUIZ FLOW --------------------
if st.session_state.mode == "quiz" and st.session_state.quiz:
    quiz = st.session_state.quiz
    q_index = st.session_state.current_q
    total = len(quiz)

    st.markdown(f"🧠 **Intent:** Quiz  |  🏷️ **Topic:** {st.session_state.topic}")

    if q_index < total:
        question = quiz[q_index].get("question", f"Question {q_index+1}")
        st.markdown(f"**Question {q_index+1} of {total}:** {question}")

        answer = st.text_input("Your answer:", key=f"answer_{q_index}")
        if st.button("Submit Answer", key=f"submit_{q_index}"):
            if not answer.strip():
                st.warning("⚠️ Please enter an answer before submitting.")
            else:
                st.session_state.answers.append(answer)
                st.session_state.current_q += 1
                st.rerun()
    else:
        st.info("✅ All questions answered! Evaluating your responses...")
        with st.spinner("🧩 Evaluating..."):
            try:
                res = requests.post(API_URL, json={
                    "user_input": "evaluate",
                    "student_answers": st.session_state.answers
                })
                data = res.json()
                eval_result = data.get("result", {}).get("evaluation", {})
                if isinstance(eval_result, list):
                    eval_result = {"score": 0, "total": len(eval_result), "feedback": eval_result}
                st.session_state.evaluation = eval_result
                st.session_state.mode = "evaluation"
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Evaluation Error: {e}")

# -------------------- EVALUATION FLOW --------------------
if st.session_state.mode == "evaluation" and st.session_state.evaluation:
    ev = st.session_state.evaluation
    st.subheader("📊 Evaluation Results")
    st.markdown(f"🧠 **Intent:** Evaluate  |  🏷️ **Topic:** {st.session_state.topic}")

    if isinstance(ev, dict):
        st.success(f"Your Score: {ev.get('score', 0)}/{ev.get('total', 0)}")
        for f in ev.get("feedback", []):
            st.markdown(f"""
            **Q:** {f.get('question', '')}  
            🧍‍♂️ *Your answer:* {f.get('student_answer', '')}  
            **Result:** {f.get('result', '')}  
            💬 {f.get('comment', '')}
            """)
    else:
        st.warning("⚠️ Evaluation format not recognized.")
