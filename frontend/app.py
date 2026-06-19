import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📘",
    layout="wide"
)

# ==================================================
# HEADER
# ==================================================

st.title("📘 AI Study Assistant")

st.caption("LangGraph + FastAPI + Gemini + SQLite")

st.markdown(
"""
### Welcome

This platform provides:

✅ AI Topic Explanations  
✅ Adaptive Quiz Generation  
✅ Automatic Evaluation  
✅ Quiz Recall  
✅ Learning Analytics Dashboard  
✅ Personalized Difficulty Recommendation  
"""
)

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.title("📘 Study Assistant")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "Explain Topic",
        "Generate Quiz",
        "Recall Quiz",
        "Progress Dashboard"
    ]
)

st.sidebar.markdown("---")

st.sidebar.caption("AI-Powered Learning Platform")

try:
    adaptive = requests.get(f"{API_URL}/adaptive").json()

    st.sidebar.metric(
        "Recommended Difficulty",
        adaptive.get("recommended_difficulty", "medium")
    )

except:
    pass


# ==================================================
# EXPLAIN PAGE
# ==================================================

if page == "Explain Topic":

    st.header("📖 Explain a Topic")

    topic = st.text_input(
        "Topic",
        placeholder="Machine Learning"
    )

    if st.button("Explain"):

        if not topic.strip():
            st.warning("Please enter a topic.")

        else:
            try:
                response = requests.post(
                    f"{API_URL}/process/",
                    json={
                        "user_input": f"explain {topic}"
                    }
                )

                data = response.json()

                explanation = (
                    data.get("result", {})
                    .get("explanation", "")
                )

                st.success("Explanation Generated")

                st.markdown("## 📖 Explanation")
                st.info(explanation)

                # SAVE TOPIC
                st.session_state.last_topic = topic

            except Exception as e:
                st.error(f"Error: {e}")


# ==================================================
# QUIZ PAGE
# ==================================================

elif page == "Generate Quiz":

    st.header("📝 Generate Quiz")

    col1, col2 = st.columns(2)

    with col1:
        topic = st.text_input("Topic", placeholder="Python")

    with col2:
        difficulty = st.selectbox(
            "Difficulty",
            ["easy", "medium", "hard"]
        )

    num_questions = st.slider(
        "Number of Questions",
        1,
        10,
        5
    )

    if st.button("Generate Quiz"):

        if not topic.strip():
            st.warning("Please enter a topic.")

        else:
            try:
                response = requests.post(
                    f"{API_URL}/process/",
                    json={
                        "user_input": f"quiz {topic} {difficulty}",
                        "num_questions": num_questions
                    }
                )

                data = response.json()

                st.session_state.quiz = (
                    data.get("result", {})
                    .get("quiz", [])
                )

                # SAVE TOPIC
                st.session_state.last_topic = topic

                st.success("Quiz Generated Successfully")

            except Exception as e:
                st.error(f"Quiz Error: {e}")

    if "quiz" in st.session_state and st.session_state.quiz:

        quiz = st.session_state.quiz

        st.subheader("Answer the Questions")

        answers = []

        for i, q in enumerate(quiz):

            st.markdown(f"### Question {i+1}")

            st.write(q.get("question", "No question"))

            answer = st.text_input(
                "Your Answer",
                key=f"answer_{i}"
            )

            answers.append(answer)

        if st.button("Submit Quiz"):

            try:
                response = requests.post(
                    f"{API_URL}/process/",
                    json={
                        "user_input": "evaluate",
                        "quiz": quiz,
                        "student_answers": answers
                    }
                )

                result = response.json()

                evaluation = result.get("result", {}).get("evaluation", {})

                score = evaluation.get("score", 0)
                total = evaluation.get("total", 0)

                percentage = (
                    round(score * 100 / total, 2)
                    if total > 0 else 0
                )

                st.success(f"Score: {score}/{total}")
                st.metric("Percentage", f"{percentage}%")

                # PERFORMANCE STATUS CARD
                if percentage >= 80:
                    st.success("Excellent Performance 🚀")
                elif percentage >= 50:
                    st.warning("Good Progress 📈")
                else:
                    st.error("Needs Improvement 📚")

                st.info(evaluation.get("recommendation", ""))

                st.subheader("Detailed Feedback")

                for item in evaluation.get("feedback", []):

                    with st.expander(item.get("question", "Question")):

                        st.write(
                            f"**Your Answer:** {item.get('student_answer','')}"
                        )

                        st.write(
                            f"**Result:** {item.get('result','')}"
                        )

                        st.write(
                            f"**Comment:** {item.get('comment','')}"
                        )

            except Exception as e:
                st.error(f"Evaluation Error: {e}")


# ==================================================
# RECALL PAGE
# ==================================================

elif page == "Recall Quiz":

    st.header("📚 Recall Last Quiz")

    try:

        response = requests.post(
            f"{API_URL}/process/",
            json={"user_input": "recall"}
        )

        data = response.json()

        quiz = data.get("result", {}).get("quiz", [])

        if not quiz:
            st.warning("No previous quiz found.")

        else:
            st.success(f"Retrieved {len(quiz)} questions")

            for i, q in enumerate(quiz, start=1):

                st.markdown(f"### Question {i}")
                st.write(q.get("question", ""))

                if q.get("answer"):

                    with st.expander("Show Answer"):
                        st.write(q["answer"])

    except Exception as e:
        st.error(f"Recall Error: {e}")


# ==================================================
# DASHBOARD PAGE
# ==================================================

elif page == "Progress Dashboard":

    st.header("📊 Progress Dashboard")

    try:

        dashboard = requests.get(f"{API_URL}/dashboard").json()

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Quizzes",
            dashboard.get("total_quizzes", 0)
        )

        col2.metric(
            "Average Score %",
            dashboard.get("average_score", 0)
        )

        col3.metric(
            "Recommended Difficulty",
            dashboard.get("recommended_difficulty", "medium")
        )

        st.caption(
            "Difficulty is automatically adjusted using recent quiz performance."
        )

        # PERFORMANCE STATUS
        avg = dashboard.get("average_score", 0)

        if avg >= 80:
            st.success("Excellent Performance 🚀")
        elif avg >= 50:
            st.warning("Good Progress 📈")
        else:
            st.error("Needs Improvement 📚")

        st.subheader("Performance Trend")

        scores = dashboard.get("scores", [])

        if scores:

            df = pd.DataFrame({
                "Attempt": list(range(1, len(scores) + 1)),
                "Score": list(reversed(scores))
            })

            chart_df = df.set_index("Attempt")

            st.line_chart(
                chart_df,
                use_container_width=True
            )

        else:
            st.info("No quiz history available.")

    except Exception as e:
        st.error(f"Dashboard Error: {e}")