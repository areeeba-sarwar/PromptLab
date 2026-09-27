# ================================================================
#  Fatima Backend — Learning Module, Practice Evaluation, Progress
#  Scope: chapters, practice questions, practice sessions, practice
#  evaluation, chat history, progress tracking, learning analytics.
#
#  Run: python app.py
#  Port: 5002
# ================================================================

from __future__ import annotations

import html
import json
import os
import random
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from grok_failover import create_chat_completion, has_grok_api_keys

load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__)
CORS(app)

DB_PATH = os.getenv("FATIMA_DB_PATH", "fatima_learning.db")
AREEBA_API = os.getenv("AREEBA_API", "http://127.0.0.1:5001")
PASSING_SCORE = int(os.getenv("PRACTICE_PASSING_SCORE", "70"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ----------------------------------------------------------------
# Seed content. This is stored in DB on first startup and then served
# through APIs, so the frontend no longer depends on mock learning data.
# ----------------------------------------------------------------
# YouTube embed URLs — one per chapter (prompt-engineering related, CC-licensed / official)
CHAPTER_VIDEOS = {
    "1": "https://www.youtube.com/embed/T9aRN5JkmL8",   # Prompt Engineering Overview – Andrej Karpathy
    "2": "https://www.youtube.com/embed/1bUy-1hGZpI",   # How to write better prompts – LearnWithHasan
    "3": "https://www.youtube.com/embed/jC4v5AS4RIM",   # Context in prompting – AI Explained
    "4": "https://www.youtube.com/embed/wbGKfAPlZVA",   # Role prompting deep-dive – Matt Wolfe
    "5": "https://www.youtube.com/embed/_e5YKLv2zyI",   # Chain of Thought prompting – Prompt Engineering YT
    "6": "https://www.youtube.com/embed/dOxUroR57xs",   # Advanced prompting techniques – AI Jason
}

DEFAULT_CHAPTERS = [
    {
        "id": "1",
        "title": "Introduction to Prompt Engineering",
        "description": "Learn the fundamentals of crafting effective prompts for AI systems",
        "duration": "15 min",
        "lessons": 4,
        "video_url": CHAPTER_VIDEOS["1"],
        "content": """# Introduction to Prompt Engineering

Prompt engineering is the art and science of crafting effective instructions for AI systems. In this chapter, you'll learn the foundational concepts that help you communicate more effectively with AI models.

## What is a Prompt?

A prompt is any text input you provide to an AI model to generate a response. The quality of your prompt directly influences the quality of the output you receive.

## Why Does Prompt Engineering Matter?

- Precision: Well-crafted prompts lead to more accurate and relevant responses.
- Efficiency: Good prompts reduce the need for repeated follow-up questions.
- Consistency: Structured prompts produce more reliable outputs.
- Control: You can guide the AI's behavior, tone, scope, and format.

## Key Principles

1. Be specific about the task.
2. Provide useful context.
3. Define the expected output format.
4. Add constraints such as audience, tone, word count, or examples.
5. Improve iteratively based on feedback.""",
    },
    {
        "id": "2",
        "title": "Clarity and Specificity",
        "description": "Master the art of writing clear and specific prompts",
        "duration": "20 min",
        "lessons": 5,
        "video_url": CHAPTER_VIDEOS["2"],
        "content": """# Clarity and Specificity

The most common prompt engineering mistake is being too vague. Clear prompts reduce ambiguity and guide the AI toward useful responses.

## Techniques for Clarity

### Define the Audience
Example: Explain cloud computing for a beginner business student.

### Specify the Format
Example: Provide a 5-point checklist.

### Add Boundaries
Example: Focus only on social media marketing for B2B startups.

### Include Examples
Examples teach the AI the pattern you want it to follow.

## Practice Focus

Transform vague prompts into prompts with task, context, audience, constraints, and expected output.""",
    },
    {
        "id": "3",
        "title": "Context and Background",
        "description": "Learn how to provide effective context in your prompts",
        "duration": "18 min",
        "lessons": 4,
        "video_url": CHAPTER_VIDEOS["3"],
        "content": """# Context and Background

Context is the information that helps an AI understand your situation, goals, audience, and constraints.

## Types of Context

### Situational Context
Who you are, what you know, and what situation you are in.

### Goal Context
What outcome you want.

### Constraint Context
Any time, budget, format, tone, platform, or length limitations.

### Historical Context
Previous attempts, failed approaches, or background details.

## Context Framework

Use Who, What, Why, When, Where, and How to make your prompt complete.""",
    },
    {
        "id": "4",
        "title": "Role-Based Prompting",
        "description": "Assign roles to AI for more specialized responses",
        "duration": "22 min",
        "lessons": 6,
        "video_url": CHAPTER_VIDEOS["4"],
        "content": """# Role-Based Prompting

Assigning a role helps the AI answer from a specific perspective or expertise level.

## Examples

- You are a senior financial advisor.
- Act as a patient teacher.
- Respond as a skeptical product reviewer.

## Benefits

1. Better domain-specific language.
2. More relevant advice.
3. Consistent tone.
4. Useful perspective for analysis.

## Practice Focus

Use role, task, context, constraints, and output format together.""",
    },
    {
        "id": "5",
        "title": "Chain of Thought Prompting",
        "description": "Guide AI through complex reasoning step by step",
        "duration": "25 min",
        "lessons": 5,
        "video_url": CHAPTER_VIDEOS["5"],
        "content": """# Chain of Thought Prompting

For complex tasks, ask the AI to reason step by step or follow a structured process.

## When to Use It

- Planning
- Analysis
- Debugging
- Comparing options
- Multi-step decisions

## Useful Structures

Ask the AI to identify variables, list constraints, compare approaches, and then recommend an answer.

## Practice Focus

Create prompts that guide the AI through reasoning without leaving the task vague.""",
    },
    {
        "id": "6",
        "title": "Advanced Techniques",
        "description": "Explore few-shot learning, output formatting, and iterative refinement",
        "duration": "30 min",
        "lessons": 7,
        "video_url": CHAPTER_VIDEOS["6"],
        "content": """# Advanced Prompt Engineering Techniques

Advanced prompting combines examples, constraints, output schemas, and iterative refinement.

## Few-Shot Learning

Provide examples of input and output so the AI can follow the pattern.

## Negative Prompting

Specify what the AI should avoid.

## Output Formatting

Ask for JSON, tables, checklists, steps, headings, or another required structure.

## Iterative Refinement

Submit a prompt, review feedback, improve it, and submit again.""",
    },
]

DEFAULT_QUESTIONS = [
    # ── Chapter 1: Introduction to Prompt Engineering ──────────────────────
    {
        "chapter_id": "1",
        "title": "Marketing Email Prompt",
        "difficulty": "beginner",
        "scenario": "You need an AI to help create a marketing email for a new smart water bottle that tracks hydration levels.",
        "hints": ["Mention the target audience", "Define email tone", "Request a clear email structure"],
        "expected_elements": ["task", "target audience", "product details", "tone", "email format", "call to action"],
    },
    {
        "chapter_id": "1",
        "title": "Simple Explanation Prompt",
        "difficulty": "beginner",
        "scenario": "You want an AI to explain photosynthesis to a grade 8 student in simple language.",
        "hints": ["Mention the student level", "Ask for simple words", "Request examples or bullet points"],
        "expected_elements": ["audience", "topic", "simple language", "format", "examples"],
    },
    {
        "chapter_id": "1",
        "title": "Recipe Generation Prompt",
        "difficulty": "beginner",
        "scenario": "You want an AI to suggest a healthy dinner recipe for a family of four using chicken, broccoli, and rice.",
        "hints": ["Mention available ingredients", "State serving size", "Request step-by-step instructions"],
        "expected_elements": ["ingredients", "serving size", "dietary preference", "cooking steps", "time"],
    },
    {
        "chapter_id": "1",
        "title": "Social Media Caption Prompt",
        "difficulty": "beginner",
        "scenario": "You need an AI to write three Instagram captions for a new café that specializes in plant-based coffee drinks.",
        "hints": ["Describe the café's brand voice", "Mention the number of captions", "Ask for relevant hashtags"],
        "expected_elements": ["brand", "product", "tone", "number of captions", "hashtags", "platform"],
    },
    {
        "chapter_id": "1",
        "title": "Study Plan Prompt",
        "difficulty": "beginner",
        "scenario": "You want AI to create a two-week study plan for a university student preparing for final exams in three subjects.",
        "hints": ["List the subjects", "State available daily hours", "Ask for a structured schedule"],
        "expected_elements": ["subjects", "duration", "daily hours", "study methods", "schedule format"],
    },
    # ── Chapter 2: Clarity & Specificity ──────────────────────────────────
    {
        "chapter_id": "2",
        "title": "Resume Review Prompt",
        "difficulty": "beginner",
        "scenario": "You need an AI to review a software engineering resume for a junior developer role.",
        "hints": ["Specify what should be reviewed", "Mention the job role", "Ask for actionable suggestions"],
        "expected_elements": ["role", "review criteria", "specific improvements", "format", "constraints"],
    },
    {
        "chapter_id": "2",
        "title": "Code Review Prompt",
        "difficulty": "intermediate",
        "scenario": "Create a prompt that asks an AI to review a Python function that calculates the average of a list of numbers.",
        "hints": ["Ask for edge cases", "Request readability feedback", "Ask for corrected code"],
        "expected_elements": ["language", "code purpose", "review criteria", "edge cases", "explanation"],
    },
    {
        "chapter_id": "2",
        "title": "Meeting Summary Prompt",
        "difficulty": "beginner",
        "scenario": "You want an AI to summarize a 30-minute team meeting about launching a new mobile app feature next month.",
        "hints": ["State the meeting topic", "Specify output format", "Ask for action items"],
        "expected_elements": ["meeting topic", "duration", "output format", "action items", "key decisions"],
    },
    {
        "chapter_id": "2",
        "title": "Product Description Prompt",
        "difficulty": "intermediate",
        "scenario": "Ask AI to write a product description for a noise-cancelling headphone targeting remote workers and students.",
        "hints": ["Specify the target buyer", "List key features", "Set word limit and tone"],
        "expected_elements": ["product", "features", "target audience", "tone", "word limit", "benefits"],
    },
    {
        "chapter_id": "2",
        "title": "Travel Itinerary Prompt",
        "difficulty": "beginner",
        "scenario": "You want AI to plan a 5-day budget travel itinerary for a solo traveller visiting Tokyo for the first time.",
        "hints": ["Mention budget range", "State solo travel preference", "Ask for daily structure"],
        "expected_elements": ["destination", "duration", "budget", "traveller type", "daily schedule", "tips"],
    },
    # ── Chapter 3: Context & Background ───────────────────────────────────
    {
        "chapter_id": "3",
        "title": "Interview Preparation Prompt",
        "difficulty": "intermediate",
        "scenario": "You want AI help to prepare for a Senior Software Engineer interview at a fintech company.",
        "hints": ["Add background", "Mention company domain", "Request mock questions and feedback"],
        "expected_elements": ["candidate background", "job role", "industry", "question format", "feedback"],
    },
    {
        "chapter_id": "3",
        "title": "Business Plan Prompt",
        "difficulty": "intermediate",
        "scenario": "You need an AI to help create a small business plan for an online handmade jewelry store.",
        "hints": ["Explain business context", "Mention budget limits", "Request sections"],
        "expected_elements": ["business type", "goal", "constraints", "sections", "audience"],
    },
    {
        "chapter_id": "3",
        "title": "Customer Support Script Prompt",
        "difficulty": "intermediate",
        "scenario": "You work at an e-commerce company and need AI to write a customer support email template for delayed shipment complaints.",
        "hints": ["Describe company context", "State the customer complaint type", "Ask for empathetic and professional tone"],
        "expected_elements": ["company context", "complaint type", "tone", "resolution steps", "template format"],
    },
    {
        "chapter_id": "3",
        "title": "Health Advice Prompt",
        "difficulty": "beginner",
        "scenario": "You are a nurse practitioner needing AI to draft simple healthy lifestyle tips for elderly patients managing Type 2 diabetes.",
        "hints": ["Provide healthcare context", "Specify patient group", "Request simple and safe language"],
        "expected_elements": ["healthcare context", "patient group", "condition", "safety constraints", "simple language", "tips format"],
    },
    {
        "chapter_id": "3",
        "title": "Academic Research Prompt",
        "difficulty": "advanced",
        "scenario": "You are a postgraduate student writing a literature review on the impact of social media on teenage mental health.",
        "hints": ["State your academic level", "Define the research scope", "Ask for structured sections"],
        "expected_elements": ["academic context", "topic", "scope", "research sources", "structure", "audience"],
    },
    # ── Chapter 4: Role-Based Prompting ───────────────────────────────────
    {
        "chapter_id": "4",
        "title": "Financial Advisor Role Prompt",
        "difficulty": "intermediate",
        "scenario": "Ask AI to act as a financial advisor and explain basic budgeting to a university student.",
        "hints": ["Assign a role", "Mention user situation", "Set tone and format"],
        "expected_elements": ["role", "audience", "goal", "tone", "practical steps"],
    },
    {
        "chapter_id": "4",
        "title": "Teacher Role Prompt",
        "difficulty": "beginner",
        "scenario": "Ask AI to act as a patient programming teacher explaining loops in Python to a beginner.",
        "hints": ["Define the teaching role", "Mention beginner level", "Ask for examples"],
        "expected_elements": ["role", "topic", "audience level", "examples", "step-by-step explanation"],
    },
    {
        "chapter_id": "4",
        "title": "Career Coach Role Prompt",
        "difficulty": "intermediate",
        "scenario": "Ask AI to act as a career coach helping a recent computer science graduate decide between a startup and a corporate job offer.",
        "hints": ["Assign the coaching role", "Describe the graduate's situation", "Ask for pros and cons"],
        "expected_elements": ["role", "situation", "options", "decision criteria", "personalised advice"],
    },
    {
        "chapter_id": "4",
        "title": "Legal Advisor Role Prompt",
        "difficulty": "intermediate",
        "scenario": "Ask AI to act as a business lawyer and explain the basic steps to register a sole proprietorship in simple terms.",
        "hints": ["Assign a legal expert role", "State the business type", "Request plain language explanation"],
        "expected_elements": ["role", "business type", "jurisdiction context", "plain language", "numbered steps"],
    },
    {
        "chapter_id": "4",
        "title": "Nutritionist Role Prompt",
        "difficulty": "beginner",
        "scenario": "Ask AI to act as a certified nutritionist and create a one-week meal plan for a vegetarian athlete trying to build muscle.",
        "hints": ["Define the nutrition expert role", "State dietary restriction", "Specify fitness goal"],
        "expected_elements": ["role", "dietary restriction", "goal", "meal structure", "daily calories", "weekly plan"],
    },
    # ── Chapter 5: Chain of Thought Prompting ─────────────────────────────
    {
        "chapter_id": "5",
        "title": "Decision Analysis Prompt",
        "difficulty": "advanced",
        "scenario": "Create a prompt that guides AI to compare whether a student should buy a laptop or tablet for university work.",
        "hints": ["Ask for step-by-step comparison", "Mention constraints", "Request final recommendation"],
        "expected_elements": ["options", "criteria", "constraints", "step-by-step reasoning", "recommendation"],
    },
    {
        "chapter_id": "5",
        "title": "Debugging Reasoning Prompt",
        "difficulty": "advanced",
        "scenario": "Ask AI to debug why a Python program is returning the wrong total price in a shopping cart.",
        "hints": ["Ask for systematic checks", "Mention expected vs actual output", "Request explanation"],
        "expected_elements": ["debugging role", "symptoms", "steps", "expected output", "fix explanation"],
    },
    {
        "chapter_id": "5",
        "title": "Business Risk Assessment Prompt",
        "difficulty": "advanced",
        "scenario": "Create a prompt that asks AI to analyse risks of opening a food truck business in a competitive city market, step by step.",
        "hints": ["Ask for structured risk analysis", "Mention market context", "Request mitigation strategies"],
        "expected_elements": ["business context", "step-by-step analysis", "risk categories", "market factors", "mitigation"],
    },
    {
        "chapter_id": "5",
        "title": "Math Word Problem Prompt",
        "difficulty": "intermediate",
        "scenario": "Create a prompt asking AI to solve a compound interest word problem step by step, showing every calculation clearly.",
        "hints": ["Provide problem details", "Ask for visible calculation steps", "Request final answer with explanation"],
        "expected_elements": ["problem details", "step-by-step calculation", "formula used", "intermediate results", "final answer"],
    },
    {
        "chapter_id": "5",
        "title": "Hiring Decision Prompt",
        "difficulty": "advanced",
        "scenario": "You are an HR manager choosing between two candidates for a data analyst role. Create a prompt guiding AI to reason through the decision.",
        "hints": ["Describe each candidate briefly", "List evaluation criteria", "Ask AI to reason before concluding"],
        "expected_elements": ["candidate profiles", "criteria", "reasoning steps", "weighting", "final recommendation"],
    },
    # ── Chapter 6: Advanced Techniques ────────────────────────────────────
    {
        "chapter_id": "6",
        "title": "JSON Output Prompt",
        "difficulty": "advanced",
        "scenario": "Create a prompt that asks AI to summarize customer feedback and return the result in JSON format.",
        "hints": ["Define JSON fields", "Mention categories", "Ask for concise output"],
        "expected_elements": ["task", "data context", "JSON schema", "constraints", "categories"],
    },
    {
        "chapter_id": "6",
        "title": "Few-Shot Prompt",
        "difficulty": "advanced",
        "scenario": "Write a prompt that teaches AI to convert casual messages into professional emails using examples.",
        "hints": ["Provide example pairs", "Define style", "Ask for same pattern"],
        "expected_elements": ["examples", "input-output pattern", "tone", "task", "format"],
    },
    {
        "chapter_id": "6",
        "title": "Iterative Refinement Prompt",
        "difficulty": "advanced",
        "scenario": "Write a prompt asking AI to first generate a draft blog post introduction, then critique it, then rewrite an improved version.",
        "hints": ["Ask for draft → critique → rewrite flow", "Specify the blog topic", "Define quality criteria"],
        "expected_elements": ["topic", "multi-step instruction", "self-critique", "improvement criteria", "final output"],
    },
    {
        "chapter_id": "6",
        "title": "Negative Prompting Prompt",
        "difficulty": "intermediate",
        "scenario": "Create a prompt for an AI content writer that explicitly lists what to AVOID: no clichés, no passive voice, no filler phrases.",
        "hints": ["List banned phrases or patterns", "Set a positive task goal", "Ask for explanation of choices"],
        "expected_elements": ["task", "negative constraints", "style rules", "examples of what to avoid", "output format"],
    },
    {
        "chapter_id": "6",
        "title": "Structured Report Prompt",
        "difficulty": "advanced",
        "scenario": "Ask AI to generate a competitor analysis report for a mobile banking app, using headings, bullet points, and a summary table.",
        "hints": ["Define report sections", "Ask for a comparison table", "Specify industry and competitors"],
        "expected_elements": ["report topic", "sections", "competitors", "table format", "summary", "industry context"],
    },
]


# ----------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def sanitize_prompt(text: str) -> str:
    """Strip HTML tags and unescape entities; collapse excessive whitespace."""
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"[ \t]{3,}", "  ", cleaned)
    return cleaned.strip()


def init_db() -> None:
    db = get_db()
    cur = db.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chapters (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            duration TEXT NOT NULL,
            lessons INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL,
            video_url TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT NOT NULL,
            title TEXT NOT NULL,
            scenario TEXT NOT NULL,
            hints TEXT NOT NULL,
            expected_elements TEXT NOT NULL,
            difficulty TEXT NOT NULL DEFAULT 'beginner',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chapter_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            session_title TEXT,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id),
            FOREIGN KEY (question_id) REFERENCES practice_questions(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            chapter_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            attempt_number INTEGER NOT NULL,
            prompt_text TEXT NOT NULL,
            score INTEGER NOT NULL,
            clarity INTEGER NOT NULL,
            structure INTEGER NOT NULL,
            specificity INTEGER NOT NULL,
            strengths TEXT NOT NULL,
            weaknesses TEXT NOT NULL,
            suggestions TEXT NOT NULL,
            detailed_feedback TEXT NOT NULL,
            prompt_quality_analysis TEXT NOT NULL,
            improvement_recommendations TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES practice_questions(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            attempt_id INTEGER,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (attempt_id) REFERENCES practice_attempts(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chapter_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chapter_id TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_questions INTEGER NOT NULL DEFAULT 0,
            total_questions INTEGER NOT NULL DEFAULT 0,
            best_score INTEGER NOT NULL DEFAULT 0,
            average_score REAL NOT NULL DEFAULT 0,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            UNIQUE(user_id, chapter_id),
            FOREIGN KEY (chapter_id) REFERENCES chapters(id)
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_practice_sessions_user ON practice_sessions(user_id, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attempts_user_chapter ON practice_attempts(user_id, chapter_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON practice_messages(session_id, created_at)")

    seed_chapters_and_questions(db)
    init_final_test_tables(db)
    db.commit()
    db.close()


def seed_chapters_and_questions(db: sqlite3.Connection) -> None:
    chapter_count = db.execute("SELECT COUNT(*) AS c FROM chapters").fetchone()["c"]
    if chapter_count == 0:
        for index, chapter in enumerate(DEFAULT_CHAPTERS, start=1):
            db.execute(
                """
                INSERT INTO chapters (id, title, description, duration, lessons, content, video_url, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter["id"],
                    chapter["title"],
                    chapter["description"],
                    chapter["duration"],
                    chapter["lessons"],
                    chapter["content"],
                    chapter.get("video_url"),
                    index,
                ),
            )
    else:
        # Migrate: backfill video_url on already-seeded chapters that don't have one
        for chapter in DEFAULT_CHAPTERS:
            if chapter.get("video_url"):
                db.execute(
                    "UPDATE chapters SET video_url=? WHERE id=? AND (video_url IS NULL OR video_url='')",
                    (chapter["video_url"], chapter["id"]),
                )

    # Upsert questions: insert any that don't exist yet (keyed by chapter_id + title).
    # This runs on every startup so newly-added questions reach existing databases.
    for q in DEFAULT_QUESTIONS:
        existing = db.execute(
            "SELECT id FROM practice_questions WHERE chapter_id=? AND title=?",
            (q["chapter_id"], q["title"]),
        ).fetchone()
        if not existing:
            db.execute(
                """
                INSERT INTO practice_questions (chapter_id, title, scenario, hints, expected_elements, difficulty)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    q["chapter_id"],
                    q["title"],
                    q["scenario"],
                    json_dumps(q["hints"]),
                    json_dumps(q["expected_elements"]),
                    q["difficulty"],
                ),
            )


# ----------------------------------------------------------------
# Auth: Fatima backend uses Areeba's existing auth token without
# changing auth/signup/login code.
# ----------------------------------------------------------------
def get_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    return auth_header.replace("Bearer ", "").strip()


def get_current_user_from_areeba() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    token = get_token()
    if not token:
        return None, (jsonify({"error": "Missing Authorization token"}), 401)

    try:
        response = requests.get(
            f"{AREEBA_API}/api/areeba/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=4,
        )
    except requests.RequestException:
        return None, (jsonify({"error": "Could not verify login. Make sure Areeba backend is running on port 5001."}), 503)

    if response.status_code != 200:
        return None, (jsonify({"error": "Invalid or expired login token"}), 401)

    user = response.json().get("user")
    if not user:
        return None, (jsonify({"error": "Invalid user response from auth service"}), 401)
    return user, None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user, error = get_current_user_from_areeba()
        if error:
            return error
        request.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def current_user_id() -> int:
    return int(request.current_user["id"])


# ----------------------------------------------------------------
# Serialization helpers
# ----------------------------------------------------------------
def serialize_chapter(row: sqlite3.Row, progress: Optional[sqlite3.Row] = None, question_count: Optional[int] = None) -> Dict[str, Any]:
    total_questions = question_count if question_count is not None else 0
    completed_questions = int(progress["completed_questions"]) if progress else 0
    completed = bool(progress["completed"]) if progress else False
    percent = round((completed_questions / total_questions) * 100) if total_questions else 0
    if completed:
        percent = 100

    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "duration": row["duration"],
        "lessons": row["lessons"],
        "content": row["content"],
        "videoUrl": row["video_url"],
        "progress": percent,
        "completed": completed,
        "completed_questions": completed_questions,
        "total_questions": total_questions,
        "best_score": int(progress["best_score"]) if progress else 0,
        "average_score": float(progress["average_score"]) if progress else 0,
        "attempt_count": int(progress["attempt_count"]) if progress else 0,
    }


def serialize_question(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "chapter_id": row["chapter_id"],
        "title": row["title"],
        "scenario": row["scenario"],
        "statement": row["scenario"],
        "hints": json_loads(row["hints"], []),
        "expected_elements": json_loads(row["expected_elements"], []),
        "difficulty": row["difficulty"],
    }


def serialize_attempt(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "question_id": row["question_id"],
        "chapter_id": row["chapter_id"],
        "attempt_number": row["attempt_number"],
        "prompt_text": row["prompt_text"],
        "score": row["score"],
        "clarity": row["clarity"],
        "structure": row["structure"],
        "specificity": row["specificity"],
        "strengths": json_loads(row["strengths"], []),
        "weaknesses": json_loads(row["weaknesses"], []),
        "suggestions": json_loads(row["suggestions"], []),
        "detailed_feedback": row["detailed_feedback"],
        "prompt_quality_analysis": row["prompt_quality_analysis"],
        "improvement_recommendations": json_loads(row["improvement_recommendations"], []),
        "created_at": row["created_at"],
    }


def serialize_message(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "session_id": row["session_id"],
        "attempt_id": row["attempt_id"],
        "role": row["role"],
        "content": row["content"],
        "timestamp": row["created_at"],
        "created_at": row["created_at"],
    }


def serialize_session(db: sqlite3.Connection, row: sqlite3.Row, include_details: bool = False) -> Dict[str, Any]:
    question = db.execute("SELECT * FROM practice_questions WHERE id=?", (row["question_id"],)).fetchone()
    chapter = db.execute("SELECT id, title FROM chapters WHERE id=?", (row["chapter_id"],)).fetchone()
    latest_attempt = db.execute(
        "SELECT * FROM practice_attempts WHERE session_id=? ORDER BY attempt_number DESC LIMIT 1",
        (row["id"],),
    ).fetchone()

    data = {
        "id": row["id"],
        "user_id": row["user_id"],
        "chapter_id": row["chapter_id"],
        "chapter_title": chapter["title"] if chapter else None,
        "question_id": row["question_id"],
        "question": serialize_question(question) if question else None,
        "status": row["status"],
        "session_title": row["session_title"],
        "metadata": json_loads(row["metadata"], {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row["completed_at"],
        "latest_score": latest_attempt["score"] if latest_attempt else None,
    }

    if include_details:
        attempts = db.execute(
            "SELECT * FROM practice_attempts WHERE session_id=? ORDER BY attempt_number ASC",
            (row["id"],),
        ).fetchall()
        messages = db.execute(
            "SELECT * FROM practice_messages WHERE session_id=? ORDER BY created_at ASC, id ASC",
            (row["id"],),
        ).fetchall()
        data["attempts"] = [serialize_attempt(a) for a in attempts]
        data["messages"] = [serialize_message(m) for m in messages]

    return data


# ----------------------------------------------------------------
# Practice evaluation logic — deterministic and functional without
# requiring paid AI keys. It evaluates prompt quality according to
# prompt-engineering criteria.
# ----------------------------------------------------------------
def clamp(value: int, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, value))


def contains_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


def evaluate_prompt_rules(prompt_text: str, question: sqlite3.Row) -> Dict[str, Any]:
    text = prompt_text.strip()
    lower = text.lower()
    words = re.findall(r"\b\w+\b", lower)
    word_count = len(words)
    expected_elements = json_loads(question["expected_elements"], [])

    # Clarity checks
    clarity = 30
    if word_count >= 20:
        clarity += 15
    if word_count >= 45:
        clarity += 10
    if contains_any(lower, ["create", "write", "generate", "explain", "review", "analyze", "act as", "help"]):
        clarity += 15
    if "?" in text or contains_any(lower, ["please", "i need", "your task"]):
        clarity += 5
    if not contains_any(lower, ["something", "anything", "stuff", "good", "nice"]):
        clarity += 10
    if len(text) < 25:
        clarity -= 20

    # Structure checks
    structure = 25
    if contains_any(lower, ["act as", "you are", "role"]):
        structure += 15
    if contains_any(lower, ["context", "background", "scenario", "i am", "for a", "audience"]):
        structure += 15
    if contains_any(lower, ["format", "bullet", "list", "table", "json", "sections", "step-by-step", "steps"]):
        structure += 20
    if contains_any(lower, ["tone", "style", "professional", "friendly", "simple", "concise"]):
        structure += 10
    if "\n" in text or re.search(r"(^|\s)(1\.|- |\*)", text):
        structure += 10

    # Specificity checks
    specificity = 25
    matched_expected = 0
    for element in expected_elements:
        normalized = str(element).lower().replace("_", " ")
        element_words = [w for w in normalized.split() if len(w) > 2]
        if any(w in lower for w in element_words):
            matched_expected += 1
    if expected_elements:
        specificity += round((matched_expected / len(expected_elements)) * 35)
    if contains_any(lower, ["target", "audience", "student", "customer", "developer", "business", "user"]):
        specificity += 10
    if contains_any(lower, ["word", "limit", "within", "must", "do not", "avoid", "include", "focus"]):
        specificity += 10
    if contains_any(lower, ["example", "examples", "sample"]):
        specificity += 10

    clarity = clamp(clarity)
    structure = clamp(structure)
    specificity = clamp(specificity)
    score = clamp(round((clarity * 0.34) + (structure * 0.33) + (specificity * 0.33)))

    strengths: List[str] = []
    weaknesses: List[str] = []
    suggestions: List[str] = []
    recommendations: List[str] = []

    if clarity >= 75:
        strengths.append("The task is clear and easy to understand.")
    else:
        weaknesses.append("The prompt needs a clearer main task.")
        suggestions.append("Start with a direct instruction such as 'Create', 'Analyze', 'Review', or 'Explain'.")

    if structure >= 75:
        strengths.append("The prompt includes useful structure such as role, format, or steps.")
    else:
        weaknesses.append("The prompt structure can be improved.")
        suggestions.append("Add a role, context, output format, and constraints in separate sentences or bullets.")

    if specificity >= 75:
        strengths.append("The prompt includes specific details related to the scenario.")
    else:
        weaknesses.append("The prompt is not specific enough for the given scenario.")
        suggestions.append("Mention the audience, goal, constraints, and expected output details.")

    missing_elements = []
    for element in expected_elements:
        normalized = str(element).lower().replace("_", " ")
        element_words = [w for w in normalized.split() if len(w) > 2]
        if not any(w in lower for w in element_words):
            missing_elements.append(element)

    if missing_elements:
        readable = ", ".join(missing_elements[:4])
        suggestions.append(f"Include these missing scenario elements: {readable}.")
        recommendations.append(f"Add details about {readable} to make the prompt more complete.")

    if word_count < 30:
        recommendations.append("Expand the prompt with context and output requirements; very short prompts often produce generic answers.")
    if not contains_any(lower, ["format", "bullet", "list", "table", "json", "sections"]):
        recommendations.append("Specify the response format, for example bullet points, email structure, checklist, or JSON.")
    if not contains_any(lower, ["tone", "style", "professional", "friendly", "simple", "concise"]):
        recommendations.append("Define the tone or style expected from the AI response.")

    if not strengths:
        strengths.append("The prompt provides a starting point that can be improved through iteration.")
    if not recommendations:
        recommendations.append("Submit another version with stronger context and constraints to improve the score further.")

    detailed_feedback = (
        f"Your prompt scored {score}/100. "
        f"Clarity is {clarity}%, structure is {structure}%, and specificity is {specificity}%. "
        "A strong prompt should clearly state the task, provide relevant context, define the desired output format, "
        "and include constraints or examples where useful."
    )

    prompt_quality_analysis = (
        "High-quality prompts normally include: role/persona, task, background context, audience, constraints, "
        "output format, and success criteria. This evaluation compares your answer against those elements and the current practice scenario."
    )

    return {
        "score": score,
        "clarity": clarity,
        "structure": structure,
        "specificity": specificity,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "detailed_feedback": detailed_feedback,
        "prompt_quality_analysis": prompt_quality_analysis,
        "improvement_recommendations": recommendations,
        "passing_score": PASSING_SCORE,
        "passed": score >= PASSING_SCORE,
    }


def extract_json_object(raw: str) -> Dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?|```", "", raw or "", flags=re.IGNORECASE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_feedback_list(value: Any, fallback: List[str]) -> List[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def evaluate_prompt_with_groq(prompt_text: str, question: sqlite3.Row, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not has_grok_api_keys():
        raise RuntimeError("Groq API keys are unavailable")

    question_data = serialize_question(question)
    system_prompt = """You are a prompt engineering practice evaluator.
Return ONLY valid JSON. Do not include markdown or extra text.
Evaluate the student's prompt for the given practice scenario.
Use these fields exactly:
{
  "score": 0,
  "clarity": 0,
  "structure": 0,
  "specificity": 0,
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["..."],
  "detailed_feedback": "...",
  "prompt_quality_analysis": "...",
  "improvement_recommendations": ["..."]
}
Scores must be integers from 0 to 100. Feedback must be practical, specific, and aligned with the scenario."""

    user_prompt = f"""Practice scenario:
Title: {question_data.get("title")}
Difficulty: {question_data.get("difficulty")}
Scenario: {question_data.get("scenario")}
Expected elements: {", ".join(question_data.get("expected_elements") or [])}

Student prompt:
{prompt_text}"""

    response = create_chat_completion(
        action="fatima practice evaluation",
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    raw = response.choices[0].message.content
    data = extract_json_object(raw)

    score = clamp(int(data.get("score", fallback["score"])))
    clarity = clamp(int(data.get("clarity", fallback["clarity"])))
    structure = clamp(int(data.get("structure", fallback["structure"])))
    specificity = clamp(int(data.get("specificity", fallback["specificity"])))

    detailed_feedback = str(data.get("detailed_feedback") or "").strip() or fallback["detailed_feedback"]
    prompt_quality_analysis = str(data.get("prompt_quality_analysis") or "").strip() or fallback["prompt_quality_analysis"]

    return {
        "score": score,
        "clarity": clarity,
        "structure": structure,
        "specificity": specificity,
        "strengths": normalize_feedback_list(data.get("strengths"), fallback["strengths"]),
        "weaknesses": normalize_feedback_list(data.get("weaknesses"), fallback["weaknesses"]),
        "suggestions": normalize_feedback_list(data.get("suggestions"), fallback["suggestions"]),
        "detailed_feedback": detailed_feedback,
        "prompt_quality_analysis": prompt_quality_analysis,
        "improvement_recommendations": normalize_feedback_list(
            data.get("improvement_recommendations"),
            fallback["improvement_recommendations"],
        ),
        "passing_score": PASSING_SCORE,
        "passed": score >= PASSING_SCORE,
        "feedback_source": "groq",
    }


def evaluate_prompt(prompt_text: str, question: sqlite3.Row) -> Dict[str, Any]:
    fallback = evaluate_prompt_rules(prompt_text, question)
    fallback["feedback_source"] = "rules"
    try:
        return evaluate_prompt_with_groq(prompt_text, question, fallback)
    except Exception as exc:
        print(f"[FATIMA][practice-eval] Groq unavailable, using built-in rules: {exc}", flush=True)
        return fallback


def build_feedback_message(evaluation: Dict[str, Any]) -> str:
    return f"""I've evaluated your practice prompt.

Overall Score: {evaluation['score']}/100
Clarity: {evaluation['clarity']}%
Structure: {evaluation['structure']}%
Specificity: {evaluation['specificity']}%

Strengths:
{chr(10).join('- ' + item for item in evaluation['strengths'])}

Weaknesses:
{chr(10).join('- ' + item for item in evaluation['weaknesses'])}

Suggestions:
{chr(10).join('- ' + item for item in evaluation['suggestions'])}

Detailed Feedback:
{evaluation['detailed_feedback']}

You can improve this prompt and submit again. Every attempt will be saved in this session."""


def refresh_chapter_progress(db: sqlite3.Connection, user_id: int, chapter_id: str) -> Dict[str, Any]:
    total_questions = db.execute(
        "SELECT COUNT(*) AS c FROM practice_questions WHERE chapter_id=? AND is_active=1",
        (chapter_id,),
    ).fetchone()["c"]

    completed_questions = db.execute(
        """
        SELECT COUNT(*) AS c
        FROM (
            SELECT question_id, MAX(score) AS best_score
            FROM practice_attempts
            WHERE user_id=? AND chapter_id=?
            GROUP BY question_id
            HAVING best_score >= ?
        )
        """,
        (user_id, chapter_id, PASSING_SCORE),
    ).fetchone()["c"]

    score_row = db.execute(
        """
        SELECT COALESCE(MAX(score), 0) AS best_score,
               COALESCE(AVG(score), 0) AS average_score,
               COUNT(*) AS attempt_count
        FROM practice_attempts
        WHERE user_id=? AND chapter_id=?
        """,
        (user_id, chapter_id),
    ).fetchone()

    completed = total_questions > 0 and completed_questions >= total_questions
    existing = db.execute(
        "SELECT id, completed_at FROM chapter_progress WHERE user_id=? AND chapter_id=?",
        (user_id, chapter_id),
    ).fetchone()

    completed_at = None
    if completed:
        completed_at = existing["completed_at"] if existing and existing["completed_at"] else now()

    if existing:
        db.execute(
            """
            UPDATE chapter_progress
            SET completed=?, completed_questions=?, total_questions=?, best_score=?, average_score=?,
                attempt_count=?, updated_at=?, completed_at=?
            WHERE user_id=? AND chapter_id=?
            """,
            (
                1 if completed else 0,
                completed_questions,
                total_questions,
                int(score_row["best_score"]),
                float(score_row["average_score"]),
                int(score_row["attempt_count"]),
                now(),
                completed_at,
                user_id,
                chapter_id,
            ),
        )
    else:
        db.execute(
            """
            INSERT INTO chapter_progress
            (user_id, chapter_id, completed, completed_questions, total_questions, best_score, average_score, attempt_count, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                chapter_id,
                1 if completed else 0,
                completed_questions,
                total_questions,
                int(score_row["best_score"]),
                float(score_row["average_score"]),
                int(score_row["attempt_count"]),
                now(),
                completed_at,
            ),
        )

    return {
        "chapter_id": chapter_id,
        "completed": completed,
        "completed_questions": completed_questions,
        "total_questions": total_questions,
        "best_score": int(score_row["best_score"]),
        "average_score": round(float(score_row["average_score"]), 1),
        "attempt_count": int(score_row["attempt_count"]),
        "completion_percentage": round((completed_questions / total_questions) * 100) if total_questions else 0,
    }


def choose_question(
    db: sqlite3.Connection,
    chapter_id: str,
    user_id: Optional[int] = None,
    exclude_question_id: Optional[int] = None,
) -> Tuple[Optional[sqlite3.Row], bool]:
    """Return (question, all_completed).

    all_completed is True only when user_id is given and every question in the
    chapter has been attempted at least once — the caller should surface a
    completion message instead of starting another session.
    """
    all_questions = db.execute(
        "SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1",
        (chapter_id,),
    ).fetchall()

    if not all_questions:
        return None, False

    candidates = list(all_questions)

    if user_id is not None:
        attempted_ids = {
            row["question_id"]
            for row in db.execute(
                "SELECT DISTINCT question_id FROM practice_attempts WHERE user_id=? AND chapter_id=?",
                (user_id, chapter_id),
            ).fetchall()
        }
        unattempted = [q for q in candidates if q["id"] not in attempted_ids]

        # DEBUG: helps verify pool sizes are correct (remove after testing)
        print(
            f"[FATIMA][choose_question] chapter={chapter_id} user={user_id} "
            f"total={len(all_questions)} attempted={sorted(attempted_ids)} "
            f"unattempted={len(unattempted)}",
            flush=True,
        )

        if not unattempted:
            return None, True  # all questions exhausted
        candidates = unattempted

    if exclude_question_id:
        filtered = [q for q in candidates if q["id"] != exclude_question_id]
        if filtered:
            candidates = filtered  # only exclude if there is an alternative

    return random.choice(candidates), False


# ----------------------------------------------------------------
# APIs
# ----------------------------------------------------------------
@app.route("/api/fatima/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "module": "learning", "database": DB_PATH})


@app.route("/api/fatima/chapters", methods=["GET"])
@require_auth
def get_chapters():
    user_id = current_user_id()
    db = get_db()
    chapters = db.execute("SELECT * FROM chapters ORDER BY sort_order ASC").fetchall()
    progress_rows = db.execute("SELECT * FROM chapter_progress WHERE user_id=?", (user_id,)).fetchall()
    progress_map = {row["chapter_id"]: row for row in progress_rows}
    counts = {
        row["chapter_id"]: row["c"]
        for row in db.execute(
            "SELECT chapter_id, COUNT(*) AS c FROM practice_questions WHERE is_active=1 GROUP BY chapter_id"
        ).fetchall()
    }
    result = [serialize_chapter(c, progress_map.get(c["id"]), counts.get(c["id"], 0)) for c in chapters]
    db.close()
    return jsonify({"chapters": result})


@app.route("/api/fatima/chapters/<chapter_id>", methods=["GET"])
@require_auth
def get_chapter(chapter_id: str):
    user_id = current_user_id()
    db = get_db()
    chapter = db.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if not chapter:
        db.close()
        return jsonify({"error": "Chapter not found"}), 404

    progress = db.execute("SELECT * FROM chapter_progress WHERE user_id=? AND chapter_id=?", (user_id, chapter_id)).fetchone()
    question_count = db.execute(
        "SELECT COUNT(*) AS c FROM practice_questions WHERE chapter_id=? AND is_active=1",
        (chapter_id,),
    ).fetchone()["c"]
    questions = db.execute(
        "SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1 ORDER BY id ASC",
        (chapter_id,),
    ).fetchall()
    result = serialize_chapter(chapter, progress, question_count)
    db.close()
    return jsonify({"chapter": result, "questions": [serialize_question(q) for q in questions]})


@app.route("/api/fatima/chapters/<chapter_id>/questions", methods=["GET"])
@require_auth
def get_questions(chapter_id: str):
    db = get_db()
    questions = db.execute(
        "SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1 ORDER BY id ASC",
        (chapter_id,),
    ).fetchall()
    db.close()
    return jsonify({"questions": [serialize_question(q) for q in questions]})


@app.route("/api/fatima/practice/start", methods=["POST"])
@require_auth
def start_practice():
    user_id = current_user_id()
    data = request.get_json() or {}
    chapter_id = str(data.get("chapter_id") or "").strip()
    question_id = data.get("question_id")

    if not chapter_id:
        return jsonify({"error": "chapter_id is required"}), 400

    db = get_db()
    chapter = db.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if not chapter:
        db.close()
        return jsonify({"error": "Chapter not found"}), 404

    if question_id:
        question = db.execute(
            "SELECT * FROM practice_questions WHERE id=? AND chapter_id=? AND is_active=1",
            (question_id, chapter_id),
        ).fetchone()
        if not question:
            db.close()
            return jsonify({"error": "No practice questions available for this chapter"}), 404
    else:
        question, all_completed = choose_question(db, chapter_id, user_id=user_id)
        if all_completed:
            db.close()
            return jsonify({
                "all_completed": True,
                "message": "You have attempted all practice questions for this chapter. Great work!",
            }), 200
        if not question:
            db.close()
            return jsonify({"error": "No practice questions available for this chapter"}), 404

    session_title = f"{chapter['title']} - {question['title']}"
    cur = db.execute(
        """
        INSERT INTO practice_sessions (user_id, chapter_id, question_id, session_title, metadata, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, chapter_id, question["id"], session_title, json_dumps({"source": "start_practice"}), now(), now()),
    )
    session_id = cur.lastrowid
    db.commit()
    session = db.execute("SELECT * FROM practice_sessions WHERE id=?", (session_id,)).fetchone()
    result = serialize_session(db, session, include_details=True)
    db.close()
    return jsonify({"session": result}), 201


@app.route("/api/fatima/practice/<int:session_id>/submit", methods=["POST"])
@require_auth
def submit_practice(session_id: int):
    user_id = current_user_id()
    data = request.get_json() or {}
    prompt_text = sanitize_prompt((data.get("prompt_text") or ""))

    if len(prompt_text) < 10:
        return jsonify({"error": "Prompt must be at least 10 characters long"}), 400
    if len(prompt_text) > 5000:
        return jsonify({"error": "Prompt must be under 5000 characters"}), 400

    db = get_db()
    session = db.execute("SELECT * FROM practice_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone()
    if not session:
        db.close()
        return jsonify({"error": "Practice session not found"}), 404

    question = db.execute("SELECT * FROM practice_questions WHERE id=?", (session["question_id"],)).fetchone()
    if not question:
        db.close()
        return jsonify({"error": "Practice question not found"}), 404

    latest = db.execute(
        "SELECT COALESCE(MAX(attempt_number), 0) AS n FROM practice_attempts WHERE session_id=?",
        (session_id,),
    ).fetchone()
    attempt_number = int(latest["n"]) + 1
    evaluation = evaluate_prompt(prompt_text, question)

    cur = db.execute(
        """
        INSERT INTO practice_attempts
        (session_id, user_id, chapter_id, question_id, attempt_number, prompt_text, score, clarity, structure, specificity,
         strengths, weaknesses, suggestions, detailed_feedback, prompt_quality_analysis, improvement_recommendations, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            user_id,
            session["chapter_id"],
            session["question_id"],
            attempt_number,
            prompt_text,
            evaluation["score"],
            evaluation["clarity"],
            evaluation["structure"],
            evaluation["specificity"],
            json_dumps(evaluation["strengths"]),
            json_dumps(evaluation["weaknesses"]),
            json_dumps(evaluation["suggestions"]),
            evaluation["detailed_feedback"],
            evaluation["prompt_quality_analysis"],
            json_dumps(evaluation["improvement_recommendations"]),
            now(),
        ),
    )
    attempt_id = cur.lastrowid

    feedback_message = build_feedback_message(evaluation)
    db.execute(
        "INSERT INTO practice_messages (session_id, user_id, attempt_id, role, content, created_at) VALUES (?, ?, ?, 'user', ?, ?)",
        (session_id, user_id, attempt_id, prompt_text, now()),
    )
    db.execute(
        "INSERT INTO practice_messages (session_id, user_id, attempt_id, role, content, created_at) VALUES (?, ?, ?, 'assistant', ?, ?)",
        (session_id, user_id, attempt_id, feedback_message, now()),
    )

    status = "completed" if evaluation["score"] >= PASSING_SCORE else "active"
    db.execute(
        "UPDATE practice_sessions SET status=?, updated_at=?, completed_at=COALESCE(completed_at, ?) WHERE id=?",
        (status, now(), now() if status == "completed" else None, session_id),
    )

    progress = refresh_chapter_progress(db, user_id, session["chapter_id"])
    db.commit()

    attempt_row = db.execute("SELECT * FROM practice_attempts WHERE id=?", (attempt_id,)).fetchone()
    session_row = db.execute("SELECT * FROM practice_sessions WHERE id=?", (session_id,)).fetchone()
    result = serialize_session(db, session_row, include_details=True)
    db.close()

    return jsonify({"evaluation": evaluation, "attempt": serialize_attempt(attempt_row), "session": result, "progress": progress})


@app.route("/api/fatima/practice/<int:session_id>/change-question", methods=["POST"])
@require_auth
def change_question(session_id: int):
    user_id = current_user_id()
    db = get_db()
    old_session = db.execute("SELECT * FROM practice_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone()
    if not old_session:
        db.close()
        return jsonify({"error": "Practice session not found"}), 404

    question, all_completed = choose_question(
        db, old_session["chapter_id"], user_id=user_id, exclude_question_id=old_session["question_id"]
    )
    if all_completed:
        db.close()
        return jsonify({
            "all_completed": True,
            "message": "You have attempted all practice questions for this chapter. Great work!",
        }), 200
    if not question:
        db.close()
        return jsonify({"error": "No alternate question available"}), 404

    chapter = db.execute("SELECT * FROM chapters WHERE id=?", (old_session["chapter_id"],)).fetchone()
    existing_attempts = db.execute(
        "SELECT COUNT(*) AS c FROM practice_attempts WHERE session_id=?",
        (session_id,),
    ).fetchone()["c"]

    if int(existing_attempts) > 0:
        db.execute("UPDATE practice_sessions SET status='saved', updated_at=? WHERE id=?", (now(), session_id))
    else:
        db.execute("DELETE FROM practice_sessions WHERE id=?", (session_id,))

    cur = db.execute(
        """
        INSERT INTO practice_sessions (user_id, chapter_id, question_id, status, session_title, metadata, created_at, updated_at)
        VALUES (?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (
            user_id,
            old_session["chapter_id"],
            question["id"],
            f"{chapter['title']} - {question['title']}",
            json_dumps({"source": "change_question", "previous_session_id": session_id}),
            now(),
            now(),
        ),
    )
    new_session_id = cur.lastrowid
    db.commit()
    session = db.execute("SELECT * FROM practice_sessions WHERE id=?", (new_session_id,)).fetchone()
    result = serialize_session(db, session, include_details=True)
    db.close()
    return jsonify({"session": result}), 201


@app.route("/api/fatima/practice/sessions", methods=["GET"])
@require_auth
def list_sessions():
    user_id = current_user_id()
    db = get_db()
    rows = db.execute(
        """
        SELECT s.*
        FROM practice_sessions s
        WHERE s.user_id=?
          AND EXISTS (
              SELECT 1 FROM practice_attempts a WHERE a.session_id=s.id
          )
        ORDER BY s.updated_at DESC, s.created_at DESC
        LIMIT 50
        """,
        (user_id,),
    ).fetchall()
    result = [serialize_session(db, row, include_details=False) for row in rows]
    db.close()
    return jsonify({"sessions": result})


@app.route("/api/fatima/practice/sessions/<int:session_id>", methods=["GET"])
@require_auth
def get_session(session_id: int):
    user_id = current_user_id()
    db = get_db()
    row = db.execute("SELECT * FROM practice_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Practice session not found"}), 404
    result = serialize_session(db, row, include_details=True)
    db.close()
    return jsonify({"session": result})


@app.route("/api/fatima/progress/me", methods=["GET"])
@require_auth
def progress_me():
    user_id = current_user_id()
    db = get_db()
    # Refresh all chapters to keep dashboard accurate even after seed changes.
    chapter_ids = [r["id"] for r in db.execute("SELECT id FROM chapters ORDER BY sort_order ASC").fetchall()]
    refreshed = [refresh_chapter_progress(db, user_id, chapter_id) for chapter_id in chapter_ids]
    db.commit()
    db.close()
    return jsonify({"progress": refreshed})


@app.route("/api/fatima/dashboard/me", methods=["GET"])
@require_auth
def learning_dashboard_me():
    user_id = current_user_id()
    db = get_db()
    chapter_ids = [r["id"] for r in db.execute("SELECT id FROM chapters ORDER BY sort_order ASC").fetchall()]
    for chapter_id in chapter_ids:
        refresh_chapter_progress(db, user_id, chapter_id)
    db.commit()

    total_chapters = len(chapter_ids)
    completed_chapters = db.execute(
        "SELECT COUNT(*) AS c FROM chapter_progress WHERE user_id=? AND completed=1",
        (user_id,),
    ).fetchone()["c"]
    attempts = db.execute(
        "SELECT COUNT(*) AS c, COALESCE(AVG(score), 0) AS avg_score, COALESCE(MAX(score), 0) AS best_score FROM practice_attempts WHERE user_id=?",
        (user_id,),
    ).fetchone()
    sessions = db.execute(
        "SELECT COUNT(DISTINCT session_id) AS c FROM practice_attempts WHERE user_id=?",
        (user_id,),
    ).fetchone()["c"]
    messages = db.execute(
        "SELECT COUNT(*) AS c FROM practice_messages WHERE user_id=? AND role IN ('user', 'assistant')",
        (user_id,),
    ).fetchone()["c"]
    recent_sessions = db.execute(
        """
        SELECT s.*
        FROM practice_sessions s
        WHERE s.user_id=?
          AND EXISTS (
              SELECT 1 FROM practice_attempts a WHERE a.session_id=s.id
          )
        ORDER BY s.updated_at DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    stats = {
        "total_chapters": total_chapters,
        "chapters_completed": completed_chapters,
        "chapters_remaining": max(total_chapters - completed_chapters, 0),
        "completion_percentage": round((completed_chapters / total_chapters) * 100) if total_chapters else 0,
        "practice_sessions": sessions,
        "practice_submissions": int(attempts["c"]),
        "average_score": round(float(attempts["avg_score"]), 1),
        "best_score": int(attempts["best_score"]),
        "chat_messages": messages,
        "passing_score": PASSING_SCORE,
    }
    result_sessions = [serialize_session(db, row, include_details=False) for row in recent_sessions]
    db.close()
    return jsonify({"stats": stats, "recent_sessions": result_sessions})


# ----------------------------------------------------------------
# Backward-compatible endpoints from old Fatima file. They now use
# the new session/evaluation system.
# ----------------------------------------------------------------
@app.route("/api/fatima/practice-feedback", methods=["POST"])
@require_auth
def practice_feedback_legacy():
    data = request.get_json() or {}
    chapter_id = str(data.get("chapter_id") or "1")
    prompt_text = data.get("prompt_text") or ""

    # Start a temporary legacy session and evaluate using the new scoring engine.
    db = get_db()
    question, _ = choose_question(db, chapter_id)
    if not question:
        db.close()
        return jsonify({"error": "No question found"}), 404
    cur = db.execute(
        "INSERT INTO practice_sessions (user_id, chapter_id, question_id, session_title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (current_user_id(), chapter_id, question["id"], f"Legacy feedback - {question['title']}", now(), now()),
    )
    session_id = cur.lastrowid
    db.commit()
    db.close()

    # Reuse core submission logic by directly creating evaluation.
    db = get_db()
    question = db.execute("SELECT * FROM practice_questions WHERE id=?", (question["id"],)).fetchone()
    evaluation = evaluate_prompt(prompt_text, question)
    db.close()
    return jsonify(evaluation)


@app.route("/api/fatima/progress/<int:user_id>", methods=["GET"])
def progress_by_user_legacy(user_id: int):
    db = get_db()
    rows = db.execute("SELECT * FROM chapter_progress WHERE user_id=? ORDER BY chapter_id ASC", (user_id,)).fetchall()
    db.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/fatima/update-progress", methods=["POST"])
def update_progress_legacy():
    # Kept to avoid breaking old gateway/main routes; new progress is automatic.
    data = request.get_json() or {}
    chapter_id = str(data.get("chapter_id") or "").strip()
    user_id = int(data.get("user_id") or 1)
    if not chapter_id:
        return jsonify({"error": "chapter_id is required"}), 400
    db = get_db()
    progress = refresh_chapter_progress(db, user_id, chapter_id)
    db.commit()
    db.close()
    return jsonify({"message": "Progress refreshed", "progress": progress})


# ----------------------------------------------------------------
# Final Certification Test — tables, seed questions, endpoints
# ----------------------------------------------------------------

FINAL_TEST_QUESTIONS = [
    {
        "question": "Which of the following best describes the purpose of a 'role' in a prompt?",
        "options": [
            "To limit the response length",
            "To give the AI a persona or perspective to respond from",
            "To specify the programming language",
            "To list the topics to avoid"
        ],
        "answer": 1,
        "explanation": "Assigning a role (e.g., 'You are a senior financial advisor') anchors the AI's expertise and tone."
    },
    {
        "question": "A vague prompt like 'Tell me about climate' is most likely to produce:",
        "options": [
            "A highly specific, actionable answer",
            "A generic, broad response with little practical value",
            "A concise one-sentence answer",
            "A structured JSON output"
        ],
        "answer": 1,
        "explanation": "Without context, audience, or format constraints, the AI defaults to a broad generic overview."
    },
    {
        "question": "Which prompt technique asks the AI to reason step-by-step before giving a final answer?",
        "options": [
            "Few-shot prompting",
            "Role-based prompting",
            "Chain of Thought prompting",
            "Negative prompting"
        ],
        "answer": 2,
        "explanation": "Chain of Thought prompting explicitly asks the model to reason through the problem step by step."
    },
    {
        "question": "What is the key benefit of providing examples in a prompt (few-shot prompting)?",
        "options": [
            "It reduces API cost",
            "It teaches the AI the pattern or format you want it to follow",
            "It prevents jailbreak attacks",
            "It makes the prompt shorter"
        ],
        "answer": 1,
        "explanation": "Examples demonstrate the input-output pattern so the AI can replicate the same structure."
    },
    {
        "question": "Which element is missing from this prompt: 'Write a summary of the report'?",
        "options": [
            "A task verb",
            "Context, audience, format, and constraints",
            "A programming language",
            "A greeting"
        ],
        "answer": 1,
        "explanation": "The prompt has only a bare task with no context about the report, target audience, length, or format."
    },
    {
        "question": "Negative prompting means:",
        "options": [
            "Writing prompts in a negative tone",
            "Telling the AI what NOT to do or include",
            "Criticizing the AI's previous output",
            "Reducing the prompt's word count"
        ],
        "answer": 1,
        "explanation": "Negative prompting adds constraints like 'Do not use jargon' or 'Avoid bullet points'."
    },
    {
        "question": "Which of the following prompts is most specific?",
        "options": [
            "Explain AI",
            "Explain machine learning to a business executive in 3 bullet points, avoiding technical jargon",
            "What is deep learning?",
            "Tell me about neural networks"
        ],
        "answer": 1,
        "explanation": "Specifying the audience, format (bullet points), word count, and tone constraint makes this prompt the most precise."
    },
    {
        "question": "What does 'context' in a prompt refer to?",
        "options": [
            "The programming framework being used",
            "The background information that helps the AI understand the situation, goal, and constraints",
            "The number of tokens in the prompt",
            "The temperature setting of the model"
        ],
        "answer": 1,
        "explanation": "Context includes who you are, what you want, your constraints, and any relevant background."
    },
    {
        "question": "Iterative refinement in prompt engineering means:",
        "options": [
            "Sending the same prompt multiple times until the server responds",
            "Reviewing AI output, identifying weaknesses, and improving the prompt based on feedback",
            "Splitting a long prompt into multiple shorter ones",
            "Translating the prompt into another language"
        ],
        "answer": 1,
        "explanation": "Iteration involves evaluate → identify gap → improve the prompt → resubmit, in a continuous loop."
    },
    {
        "question": "Which of the following is the BEST way to request a structured output from an AI?",
        "options": [
            "Just ask the question and hope for the best",
            "Add 'please' to the end of the prompt",
            "Explicitly specify the format, e.g., 'Return your answer as a JSON object with fields: name, date, summary'",
            "Use all capital letters"
        ],
        "answer": 2,
        "explanation": "Explicitly defining the output schema (JSON, table, bullet points, etc.) directs the AI to format its response accordingly."
    },
    {
        "question": "Which domain-specific prompt would most benefit from adding compliance constraints?",
        "options": [
            "A creative writing prompt",
            "A legal or medical advice prompt",
            "A prompt asking for a poem",
            "A prompt for a casual conversation"
        ],
        "answer": 1,
        "explanation": "Legal and medical domains carry liability risk; adding constraints like 'This is for educational purposes only' is important."
    },
    {
        "question": "What is 'prompt injection'?",
        "options": [
            "Adding more words to improve a prompt",
            "An attack where malicious text in user input hijacks the AI's instructions",
            "A technique to shorten prompts",
            "A method of translating prompts"
        ],
        "answer": 1,
        "explanation": "Prompt injection is when adversarial input overrides or hijacks the system instructions, a key security concern."
    },
    {
        "question": "In a prompt, specifying 'audience: grade 8 student' primarily affects:",
        "options": [
            "The number of words in the response",
            "The vocabulary, complexity, and explanation style of the AI's answer",
            "The AI's creativity",
            "The response speed"
        ],
        "answer": 1,
        "explanation": "Audience definition steers the AI to adjust language complexity, analogies, and depth to suit that reader."
    },
    {
        "question": "Which of the following best demonstrates 'clarity' in a prompt?",
        "options": [
            "'Do something useful with this data'",
            "'Summarize the key trends in this sales data as 5 bullet points for a non-technical manager'",
            "'Help me'",
            "'Make it better'"
        ],
        "answer": 1,
        "explanation": "A clear prompt names the task (summarize), the medium (bullet points), the count (5), the audience, and the data."
    },
    {
        "question": "What does a 'Difficulty: Expert' classification mean for a prompt?",
        "options": [
            "The prompt is very long",
            "The prompt uses optimized role, context, constraints, format, and examples in a fully structured way",
            "The prompt is written in a foreign language",
            "The prompt contains mathematical equations"
        ],
        "answer": 1,
        "explanation": "Expert-level prompts combine all elements: persona, task, context, constraints, output format, and examples into one coherent instruction."
    },
    {
        "question": "Which format constraint would you add when you need an AI to return data that will be parsed by code?",
        "options": [
            "Bullet points",
            "A numbered list",
            "JSON or a defined schema",
            "Plain prose paragraphs"
        ],
        "answer": 2,
        "explanation": "JSON provides a machine-readable, structured format that code can reliably parse and validate."
    },
    {
        "question": "A prompt that says 'Act as a skeptical product reviewer and critique this feature list' is an example of:",
        "options": [
            "Few-shot prompting",
            "Chain of Thought prompting",
            "Role-based prompting",
            "Negative prompting"
        ],
        "answer": 2,
        "explanation": "Assigning a specific persona ('skeptical product reviewer') is the defining feature of role-based prompting."
    },
    {
        "question": "Why should you avoid vague words like 'good', 'nice', or 'something' in a prompt?",
        "options": [
            "They increase token count unnecessarily",
            "They are grammatically incorrect",
            "They give the AI no actionable guidance and lead to generic outputs",
            "They trigger content filters"
        ],
        "answer": 2,
        "explanation": "Vague qualifiers give the AI no specific target, resulting in shallow, generic, and potentially useless responses."
    },
    {
        "question": "Which prompt would produce the most reliable, comparable outputs if run multiple times?",
        "options": [
            "A prompt with no constraints",
            "A prompt with a clearly defined role, task, context, format, and constraints",
            "A one-word prompt",
            "A prompt written in question form only"
        ],
        "answer": 1,
        "explanation": "Fully constrained prompts reduce ambiguity, leading to more consistent outputs across runs."
    },
    {
        "question": "What is the primary goal of prompt engineering?",
        "options": [
            "To make prompts as short as possible",
            "To make the AI respond faster",
            "To craft instructions that guide an AI model to produce accurate, relevant, and useful outputs",
            "To teach the AI new information it was not trained on"
        ],
        "answer": 2,
        "explanation": "Prompt engineering is the art of crafting the right input to maximally guide model behaviour toward the desired output."
    },
]

FINAL_TEST_DURATION_SECONDS = 30 * 60   # 30 minutes
FINAL_TEST_PASS_SCORE       = 75         # 75% to pass
FINAL_TEST_COOLDOWN_DAYS    = 7          # 1 attempt per 7 days


def init_final_test_tables(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS final_test_questions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT NOT NULL,
            options     TEXT NOT NULL,
            answer      INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            sort_order  INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS final_test_attempts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            started_at   DATETIME NOT NULL,
            submitted_at DATETIME,
            answers      TEXT,
            score        INTEGER,
            passed       INTEGER NOT NULL DEFAULT 0,
            timed_out    INTEGER NOT NULL DEFAULT 0,
            status       TEXT NOT NULL DEFAULT 'active'
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS certificates (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL UNIQUE,
            attempt_id   INTEGER NOT NULL,
            score        INTEGER NOT NULL,
            issued_at    DATETIME NOT NULL,
            FOREIGN KEY (attempt_id) REFERENCES final_test_attempts(id)
        )
        """
    )

    count = db.execute("SELECT COUNT(*) AS c FROM final_test_questions").fetchone()["c"]
    if count == 0:
        for idx, q in enumerate(FINAL_TEST_QUESTIONS, start=1):
            db.execute(
                "INSERT INTO final_test_questions (question, options, answer, explanation, sort_order) VALUES (?,?,?,?,?)",
                (q["question"], json_dumps(q["options"]), q["answer"], q["explanation"], idx),
            )


def _all_chapters_completed(db: sqlite3.Connection, user_id: int) -> bool:
    total = db.execute("SELECT COUNT(*) AS c FROM chapters").fetchone()["c"]
    done  = db.execute(
        "SELECT COUNT(*) AS c FROM chapter_progress WHERE user_id=? AND completed=1",
        (user_id,),
    ).fetchone()["c"]
    return total > 0 and done >= total


def _active_attempt(db: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    cutoff = (datetime.utcnow() - timedelta(seconds=FINAL_TEST_DURATION_SECONDS)).strftime("%Y-%m-%d %H:%M:%S")
    return db.execute(
        "SELECT * FROM final_test_attempts WHERE user_id=? AND status='active' AND started_at >= ? ORDER BY id DESC LIMIT 1",
        (user_id, cutoff),
    ).fetchone()


def _serialize_attempt(row: sqlite3.Row) -> Dict[str, Any]:
    started = datetime.strptime(row["started_at"], "%Y-%m-%d %H:%M:%S")
    elapsed = (datetime.utcnow() - started).total_seconds()
    remaining = max(0, FINAL_TEST_DURATION_SECONDS - int(elapsed))
    return {
        "id":           row["id"],
        "status":       row["status"],
        "started_at":   row["started_at"],
        "submitted_at": row["submitted_at"],
        "score":        row["score"],
        "passed":       bool(row["passed"]),
        "timed_out":    bool(row["timed_out"]),
        "remaining_seconds": remaining,
    }


@app.route("/api/fatima/final-test/status", methods=["GET"])
@require_auth
def final_test_status():
    user_id = current_user_id()
    db = get_db()

    completed = _all_chapters_completed(db, user_id)
    certificate = db.execute("SELECT * FROM certificates WHERE user_id=?", (user_id,)).fetchone()

    # Find most recent attempt (any status) for cooldown display
    last = db.execute(
        "SELECT * FROM final_test_attempts WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    cooldown_remaining = 0
    if last and last["status"] != "active":
        submitted = last["submitted_at"] or last["started_at"]
        if submitted:
            dt = datetime.strptime(submitted, "%Y-%m-%d %H:%M:%S")
            elapsed_days = (datetime.utcnow() - dt).total_seconds() / 86400
            cooldown_remaining = max(0, FINAL_TEST_COOLDOWN_DAYS - elapsed_days)

    active = _active_attempt(db, user_id)
    db.close()

    return jsonify({
        "all_chapters_completed": completed,
        "has_certificate": certificate is not None,
        "certificate": dict(certificate) if certificate else None,
        "cooldown_remaining_hours": round(cooldown_remaining * 24, 1),
        "can_attempt": completed and not certificate and cooldown_remaining == 0,
        "active_attempt": _serialize_attempt(active) if active else None,
        "pass_score": FINAL_TEST_PASS_SCORE,
        "duration_seconds": FINAL_TEST_DURATION_SECONDS,
        "total_questions": len(FINAL_TEST_QUESTIONS),
    })


@app.route("/api/fatima/final-test/start", methods=["POST"])
@require_auth
def final_test_start():
    user_id = current_user_id()
    db = get_db()

    if not _all_chapters_completed(db, user_id):
        db.close()
        return jsonify({"error": "Complete all chapters before taking the final test"}), 403

    if db.execute("SELECT id FROM certificates WHERE user_id=?", (user_id,)).fetchone():
        db.close()
        return jsonify({"error": "You have already passed and received a certificate"}), 409

    # Expire any timed-out active attempts
    cutoff = (datetime.utcnow() - timedelta(seconds=FINAL_TEST_DURATION_SECONDS)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE final_test_attempts SET status='expired', timed_out=1 WHERE user_id=? AND status='active' AND started_at < ?",
        (user_id, cutoff),
    )
    db.commit()

    # 7-day cooldown check
    last = db.execute(
        "SELECT * FROM final_test_attempts WHERE user_id=? AND status != 'active' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if last:
        submitted = last["submitted_at"] or last["started_at"]
        if submitted:
            dt = datetime.strptime(submitted, "%Y-%m-%d %H:%M:%S")
            elapsed_days = (datetime.utcnow() - dt).total_seconds() / 86400
            if elapsed_days < FINAL_TEST_COOLDOWN_DAYS:
                remaining_h = round((FINAL_TEST_COOLDOWN_DAYS - elapsed_days) * 24, 1)
                db.close()
                return jsonify({"error": f"Please wait {remaining_h} more hours before retaking the test"}), 429

    # Resume existing active attempt
    active = _active_attempt(db, user_id)
    if active:
        questions = db.execute("SELECT * FROM final_test_questions ORDER BY sort_order ASC").fetchall()
        db.close()
        return jsonify({
            "attempt": _serialize_attempt(active),
            "questions": [
                {"id": q["id"], "question": q["question"], "options": json_loads(q["options"], [])}
                for q in questions
            ]
        })

    # Create new attempt
    started = now()
    cur = db.execute(
        "INSERT INTO final_test_attempts (user_id, started_at, status) VALUES (?, ?, 'active')",
        (user_id, started),
    )
    attempt_id = cur.lastrowid
    db.commit()
    questions = db.execute("SELECT * FROM final_test_questions ORDER BY sort_order ASC").fetchall()
    attempt = db.execute("SELECT * FROM final_test_attempts WHERE id=?", (attempt_id,)).fetchone()
    db.close()

    return jsonify({
        "attempt": _serialize_attempt(attempt),
        "questions": [
            {"id": q["id"], "question": q["question"], "options": json_loads(q["options"], [])}
            for q in questions
        ]
    }), 201


@app.route("/api/fatima/final-test/submit", methods=["POST"])
@require_auth
def final_test_submit():
    user_id = current_user_id()
    data    = request.get_json() or {}
    raw_answers = data.get("answers", {})
    # Only accept integer option indices 0–3; discard anything else
    answers: Dict[str, int] = {
        str(k): int(v)
        for k, v in raw_answers.items()
        if isinstance(v, int) and 0 <= v <= 3
    }

    db = get_db()
    active = _active_attempt(db, user_id)
    if not active:
        db.close()
        return jsonify({"error": "No active test session. Time may have expired."}), 404

    # Check timer
    started  = datetime.strptime(active["started_at"], "%Y-%m-%d %H:%M:%S")
    elapsed  = (datetime.utcnow() - started).total_seconds()
    timed_out = elapsed > FINAL_TEST_DURATION_SECONDS

    questions = db.execute("SELECT * FROM final_test_questions ORDER BY sort_order ASC").fetchall()
    correct = 0
    result_details = []
    for q in questions:
        qid        = str(q["id"])
        if qid not in answers:
            continue
        selected   = answers.get(qid)
        is_correct = selected == q["answer"]
        if is_correct:
            correct += 1
        result_details.append({
            "id":          q["id"],
            "question":    q["question"],
            "options":     json_loads(q["options"], []),
            "your_answer": selected,
            "correct_answer": q["answer"],
            "is_correct":  is_correct,
            "explanation": q["explanation"],
        })

    total  = len(questions)
    attempted = len(result_details)
    score  = round((correct / total) * 100) if total else 0
    passed = score >= FINAL_TEST_PASS_SCORE
    submitted_at = now()

    db.execute(
        """
        UPDATE final_test_attempts
        SET submitted_at=?, answers=?, score=?, passed=?, timed_out=?, status='submitted'
        WHERE id=?
        """,
        (submitted_at, json_dumps(answers), score, 1 if passed else 0, 1 if timed_out else 0, active["id"]),
    )

    if passed:
        existing_cert = db.execute("SELECT id FROM certificates WHERE user_id=?", (user_id,)).fetchone()
        if not existing_cert:
            db.execute(
                "INSERT INTO certificates (user_id, attempt_id, score, issued_at) VALUES (?,?,?,?)",
                (user_id, active["id"], score, submitted_at),
            )

    db.commit()
    certificate = db.execute("SELECT * FROM certificates WHERE user_id=?", (user_id,)).fetchone()
    db.close()

    return jsonify({
        "score":       score,
        "passed":      passed,
        "correct":     correct,
        "total":       total,
        "attempted":   attempted,
        "timed_out":   timed_out,
        "details":     result_details,
        "certificate": dict(certificate) if certificate else None,
    })


@app.route("/api/fatima/certificate/me", methods=["GET"])
@require_auth
def get_certificate():
    user_id = current_user_id()
    db = get_db()
    cert = db.execute("SELECT * FROM certificates WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    if not cert:
        return jsonify({"has_certificate": False})
    return jsonify({"has_certificate": True, "certificate": dict(cert)})


# ----------------------------------------------------------------
# Run
# ----------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("\nFatima Learning Backend Running at http://localhost:5002")
    print("GET  /api/fatima/chapters")
    print("GET  /api/fatima/chapters/<chapter_id>")
    print("POST /api/fatima/practice/start")
    print("POST /api/fatima/practice/<session_id>/submit")
    print("POST /api/fatima/practice/<session_id>/change-question")
    print("GET  /api/fatima/practice/sessions")
    print("GET  /api/fatima/dashboard/me")
    print("GET  /api/fatima/final-test/status")
    print("POST /api/fatima/final-test/start")
    print("POST /api/fatima/final-test/submit")
    print("GET  /api/fatima/certificate/me\n")
    app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5002)),
    debug=False,
    )
