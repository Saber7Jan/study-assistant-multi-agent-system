import sqlite3
import json

DB_NAME = "study_assistant.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        difficulty TEXT,
        quiz_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        score INTEGER,
        total INTEGER,
        evaluation_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_quiz(topic, difficulty, quiz):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO quizzes(topic, difficulty, quiz_data)
    VALUES (?, ?, ?)
    """, (
        topic,
        difficulty,
        json.dumps(quiz)
    ))

    conn.commit()
    conn.close()


def get_latest_quiz():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT quiz_data
    FROM quizzes
    ORDER BY id DESC
    LIMIT 1
    """)

    row = cursor.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])

    return None


def save_evaluation(topic, score, total, evaluation):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO evaluations(topic, score, total, evaluation_data)
    VALUES (?, ?, ?, ?)
    """, (
        topic,
        score,
        total,
        json.dumps(evaluation)
    ))

    conn.commit()
    conn.close()


def get_latest_evaluation():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT evaluation_data
    FROM evaluations
    ORDER BY id DESC
    LIMIT 1
    """)

    row = cursor.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])

    return None


def get_recent_scores(limit=5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT score, total
    FROM evaluations
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

    scores = []

    for score, total in rows:
        if total > 0:
            percentage = (score / total) * 100
            scores.append(round(percentage, 2))

    return scores


def get_recommended_difficulty():
    scores = get_recent_scores()

    if not scores:
        return "medium"

    avg_score = sum(scores) / len(scores)

    if avg_score < 40:
        return "easy"
    elif avg_score < 80:
        return "medium"
    else:
        return "hard"