"""
roadmap.py — EduPilot AI · Roadmap Module

Syllabus parsing and study roadmap generation logic.
Processes exam syllabi, breaks them into topics, and generates
personalised day-wise study plans.
"""

import math
from datetime import datetime, date


def parse_syllabus(syllabus_text: str) -> list:
    """
    Split syllabus text by 'Unit' boundaries, then extract
    comma-separated topics from each unit.

    Returns a flat list of trimmed, non-empty topic strings.
    """
    # Split on the word "Unit" (case-insensitive boundary)
    units = syllabus_text.split("Unit")

    topics = []
    for unit in units:
        # Each unit block may contain comma-separated topics
        for topic in unit.split(","):
            cleaned = topic.strip().strip("-:;0123456789. ")
            if cleaned:
                topics.append(cleaned)

    return topics


def calculate_days_until_exam(exam_date: str) -> int:
    """
    Calculate the number of days from today until the exam date.

    Args:
        exam_date: Date string in YYYY-MM-DD format.

    Returns:
        Number of days remaining (minimum 1).
    """
    exam_dt = datetime.strptime(exam_date, "%Y-%m-%d").date()
    delta = (exam_dt - date.today()).days
    return max(delta, 1)


# Keywords that signal a harder / more time-intensive topic
HARD_KEYWORDS = ["Deadlock", "Normalization", "Scheduling", "Concurrency"]


def _topic_weight(topic: str) -> int:
    """
    Assign an importance weight to a topic.
      • base weight = 1
      • +1 if the topic contains a known hard keyword
      • +1 if the topic has more than 2 words (indicates breadth)
    """
    weight = 1
    for kw in HARD_KEYWORDS:
        if kw.lower() in topic.lower():
            weight += 1
            break                       # count keyword bonus only once
    if len(topic.split()) > 2:
        weight += 1
    return weight


def generate_strategy_insight(total_days: int, total_topics: int, hours_per_day: int) -> str:
    """
    Produce a short, confident strategy insight based on
    the relationship between available days, topics, and
    daily study hours.
    """
    parts: list[str] = []

    effective_days = max(total_days - 2, 1)
    parts.append(f"You have {effective_days} effective study days to cover {total_topics} topics.")

    # Pacing strategy
    if total_days < total_topics:
        parts.append(
            "With limited time, adopt an intensive multi-topic approach — "
            "cover 2–3 related topics per session and prioritise high-weight areas."
        )
    elif total_days > total_topics * 2:
        parts.append(
            "You have ample runway — leverage spaced repetition with alternating "
            "study and practice cycles to maximise long-term retention."
        )
    else:
        parts.append(
            "Your schedule is well-balanced — maintain a steady one-topic-per-day pace "
            "and use buffer days for catch-up or deeper practice."
        )

    # Hours-based advice
    if hours_per_day >= 5:
        parts.append(
            "With extended daily hours, structure sessions into 90-minute deep-work blocks "
            "separated by short breaks to sustain focus and avoid burnout."
        )
    elif hours_per_day <= 2:
        parts.append(
            "Given limited daily hours, use focused priority scheduling — tackle your "
            "weakest topics first when energy is highest."
        )

    return " ".join(parts)


def assess_burnout_risk(total_days: int, total_topics: int, study_plan: list[dict]) -> str:
    """
    Evaluate burnout risk based on schedule density.

    Returns "Low", "Medium", or "High".
    """
    effective_days = max(total_days - 2, 1)
    topics_per_day = total_topics / effective_days

    heavy_day = any(len(day["tasks"]) > 3 for day in study_plan)

    revision_exists = any(
        any("Revision" in t or "Mock" in t for t in day["tasks"])
        for day in study_plan
    )

    if topics_per_day > 3 or heavy_day:
        return "High"
    if not revision_exists:
        return "Medium"
    if 2 <= topics_per_day <= 3:
        return "Medium"
    return "Low"


def generate_mentor_advice(burnout_risk: str) -> str:
    """
    Return dynamic mentor advice based on the burnout risk level.
    """
    advice = {
        "High": (
            "Your schedule is highly compressed and may lead to fatigue. "
            "Consider increasing daily study hours or extending your timeline "
            "to maintain retention and avoid burnout."
        ),
        "Medium": (
            "Your plan is achievable but moderately intensive. Stay consistent, "
            "protect revision time, and monitor your energy levels."
        ),
        "Low": (
            "Your plan is well balanced with healthy spacing and revision blocks. "
            "Maintain consistency and focus on reinforcing weak topics."
        ),
    }
    return advice.get(burnout_risk, advice["Medium"])


def generate_study_plan(
    syllabus_text: str,
    exam_date: str,
    hours_per_day: int,
) -> dict:
    """
    Advanced adaptive study-plan generator.

    • Weights topics by complexity keywords and word count.
    • Distributes topics proportionally across available study days.
    • Reserves the last 2 days for revision:
        – Day N-1  →  Weak Topic Revision
        – Day N    →  Full Revision + Mock Test
    • Falls back to simple even distribution when total_days ≤ 3.
    """
    # ── Step 1: parse & calculate ──────────────────────
    topics = parse_syllabus(syllabus_text)
    total_days = calculate_days_until_exam(exam_date)
    total_topics = len(topics)

    study_plan: list[dict] = []

    # ── Step 2: short-exam fast path (≤ 3 days) ───────
    if total_days <= 3:
        study_days = max(total_days - 1, 1)
        topics_per_day = math.ceil(total_topics / study_days) if total_topics else 1

        day_number = 1
        for i in range(0, total_topics, topics_per_day):
            study_plan.append({
                "day": day_number,
                "tasks": topics[i : i + topics_per_day],
            })
            day_number += 1

        # Last day → revision
        study_plan.append({
            "day": total_days,
            "tasks": ["Full Revision"],
        })

        burnout = assess_burnout_risk(total_days, total_topics, study_plan)
        return {
            "total_days": total_days,
            "total_topics": total_topics,
            "study_plan": study_plan,
            "strategy_insight": generate_strategy_insight(total_days, total_topics, hours_per_day),
            "burnout_risk": burnout,
            "mentor_advice": generate_mentor_advice(burnout),
        }

    # ── Step 3: reserve last 2 days ────────────────────
    study_days = total_days - 2

    # ── Step 4: intelligent compression ────────────────
    #   If there are far more days than topics, compress
    #   topic teaching into fewer "active" days so the
    #   remaining days can be used for practice.
    if study_days > total_topics * 2:
        active_topic_days = math.ceil(total_topics / 2)
    else:
        active_topic_days = min(study_days, total_topics)

    # ── Step 5: topics per active day ──────────────────
    topics_per_day = math.ceil(total_topics / active_topic_days) if active_topic_days else 1

    # ── Step 6: assign topics day by day ───────────────
    day_number = 1
    for i in range(0, total_topics, topics_per_day):
        study_plan.append({
            "day": day_number,
            "tasks": topics[i : i + topics_per_day],
        })
        day_number += 1

    # ── Step 7: fill leftover days with practice ───────
    filler_tasks = [
        "Practice Problems",
        "Reinforce Weak Topics",
        "Timed Quiz Session",
    ]
    leftover_days = study_days - active_topic_days
    for j in range(leftover_days):
        study_plan.append({
            "day": day_number,
            "tasks": [filler_tasks[j % len(filler_tasks)]],
        })
        day_number += 1

    # ── Step 8: revision tail (last 2 days) ────────────
    study_plan.append({
        "day": total_days - 1,
        "tasks": ["Weak Topic Revision"],
    })
    study_plan.append({
        "day": total_days,
        "tasks": ["Full Revision", "Mock Test"],
    })

    burnout = assess_burnout_risk(total_days, total_topics, study_plan)
    return {
        "total_days": total_days,
        "total_topics": total_topics,
        "study_plan": study_plan,
        "strategy_insight": generate_strategy_insight(total_days, total_topics, hours_per_day),
        "burnout_risk": burnout,
        "mentor_advice": generate_mentor_advice(burnout),
    }
