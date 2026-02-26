"""
main.py — EduPilot AI · FastAPI Backend
Run with: uvicorn main:app --reload
"""

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
import roadmap  # noqa: F401  — EduPilot AI roadmap module (scaffold)

# ─────────────────────────────────────────────
# STARTUP: Load trained model
# ─────────────────────────────────────────────

MODEL_PATH = "model/model.pkl"

try:
    model = joblib.load(MODEL_PATH)
    print(f"✔ Model loaded successfully from '{MODEL_PATH}'")
except FileNotFoundError:
    raise RuntimeError(
        f"Model file not found at '{MODEL_PATH}'. "
        "Run train.py first to generate the model."
    )

# ─────────────────────────────────────────────
# APP INITIALISATION
# ─────────────────────────────────────────────

app = FastAPI(
    title="AI Skill Gap Analyser",
    description="Analyses student quiz performance and returns a personalised learning roadmap.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# PYDANTIC REQUEST MODEL
# ─────────────────────────────────────────────

class QuizInput(BaseModel):
    """Incoming quiz accuracy scores and timing data from the student."""
    ds_accuracy:   float = Field(..., ge=0, le=100, description="Data Structures accuracy (0–100)")
    algo_accuracy: float = Field(..., ge=0, le=100, description="Algorithms accuracy (0–100)")
    dbms_accuracy: float = Field(..., ge=0, le=100, description="DBMS accuracy (0–100)")
    os_accuracy:   float = Field(..., ge=0, le=100, description="OS accuracy (0–100)")
    avg_time:      float = Field(..., ge=0,          description="Average time per question (seconds)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ds_accuracy":   72.5,
                "algo_accuracy": 58.0,
                "dbms_accuracy": 85.0,
                "os_accuracy":   64.0,
                "avg_time":      45.3,
            }
        }
    }

# ─────────────────────────────────────────────
# HELPER: Label & Roadmap mappings
# ─────────────────────────────────────────────

MASTERY_LABELS = {
    0: "Beginner",
    1: "Developing",
    2: "Proficient",
}

TOPIC_NAMES = {
    "ds_accuracy":   "Data Structures",
    "algo_accuracy": "Algorithms",
    "dbms_accuracy": "DBMS",
    "os_accuracy":   "Operating Systems",
}

def build_roadmap(mastery_level: str, weakest_topic: str) -> str:
    """
    Rule-based roadmap generator.
    Returns a concise, actionable study recommendation.
    """
    roadmaps = {
        "Beginner": (
            f"Start with the fundamentals. Focus on core concepts in {weakest_topic} "
            "before moving on. Use beginner-friendly resources like GeeksforGeeks, "
            "Khan Academy, or introductory YouTube playlists. Aim to complete basic "
            "exercises daily and revisit theory until it feels comfortable."
        ),
        "Developing": (
            f"You have a solid base — now sharpen it. Your weakest area is {weakest_topic}. "
            "Work through intermediate problem sets on LeetCode or HackerRank. "
            "Review topic-specific notes, attempt timed quizzes, and focus on "
            "understanding 'why' solutions work, not just 'what' they are."
        ),
        "Proficient": (
            f"Great performance overall! To stay sharp, tackle advanced problems in "
            f"{weakest_topic} and explore system design or competitive programming. "
            "Contribute to open source, mentor peers, or attempt mock interviews to "
            "consolidate mastery and uncover any hidden gaps."
        ),
    }
    return roadmaps.get(mastery_level, "Keep practising consistently!")


# ─────────────────────────────────────────────
# ENDPOINT 1: Health Check
# ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Simple liveness probe — confirms the API is running."""
    return {"status": "running"}


# ─────────────────────────────────────────────
# ENDPOINT 2: Skill Gap Analysis
# ─────────────────────────────────────────────

@app.post("/analyze", tags=["Analysis"])
def analyze(quiz: QuizInput):
    """
    Accepts student quiz scores, runs ML inference, and returns:
    - Mastery level (Beginner / Developing / Proficient)
    - Weakest topic
    - Overall score
    - Personalised study roadmap
    """
    try:
        # ── 1. Derive computed features ───────────────
        topic_scores = {
            "ds_accuracy":   quiz.ds_accuracy,
            "algo_accuracy": quiz.algo_accuracy,
            "dbms_accuracy": quiz.dbms_accuracy,
            "os_accuracy":   quiz.os_accuracy,
        }

        overall_score       = round(
            0.30 * quiz.ds_accuracy +
            0.30 * quiz.algo_accuracy +
            0.20 * quiz.dbms_accuracy +
            0.20 * quiz.os_accuracy,
            2
        )
        weakest_topic_score = round(min(topic_scores.values()), 2)

        # ── 2. Build feature vector (must match training order) ──
        features = np.array([[
            quiz.ds_accuracy,
            quiz.algo_accuracy,
            quiz.dbms_accuracy,
            quiz.os_accuracy,
            quiz.avg_time,
            overall_score,
            weakest_topic_score,
        ]])

        # ── 3. Predict mastery label ───────────────────
        prediction    = model.predict(features)[0]          # int: 0, 1, or 2
        mastery_level = MASTERY_LABELS[int(prediction)]

        # ── 4. Identify weakest topic (human-readable) ─
        weakest_key   = min(topic_scores, key=topic_scores.get)
        weakest_topic = TOPIC_NAMES[weakest_key]

        # ── 5. Generate roadmap ────────────────────────
        roadmap = build_roadmap(mastery_level, weakest_topic)

        return {
            "mastery_level":  mastery_level,
            "weakest_topic":  weakest_topic,
            "overall_score":  overall_score,
            "roadmap":        roadmap,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# =============================
# EduPilot AI - Roadmap Module
# =============================

class RoadmapRequest(BaseModel):
    """Incoming data for exam roadmap generation."""
    syllabus_text: str = Field(..., description="Full syllabus text split by Units")
    exam_date:     str = Field(..., description="Exam date in YYYY-MM-DD format")
    hours_per_day: int = Field(..., ge=1, description="Hours available for study per day")

    model_config = {
        "json_schema_extra": {
            "example": {
                "syllabus_text": "Unit 1: Arrays, Linked Lists, Stacks Unit 2: Trees, Graphs",
                "exam_date": "2026-04-15",
                "hours_per_day": 4,
            }
        }
    }


@app.post("/generate-roadmap", tags=["Roadmap"])
def generate_roadmap(req: RoadmapRequest):
    """Generate a day-wise study plan from syllabus text and exam date."""
    try:
        plan = roadmap.generate_study_plan(
            syllabus_text=req.syllabus_text,
            exam_date=req.exam_date,
            hours_per_day=req.hours_per_day,
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roadmap generation failed: {str(e)}")