# ================================================================
# RABIA'S BACKEND — Prompt Enhancement & Refinement Engine
# Run: python app.py
# Port: 5003
# ================================================================

from __future__ import annotations

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps
from datetime import datetime
import json
import os
import re
import sqlite3
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from grok_failover import create_chat_completion, has_grok_api_keys

load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

DB_PATH = os.getenv("RABIA_DB_PATH", os.path.join(BASE_DIR, "rabia_enhancer.db"))
AREEBA_API = os.getenv("AREEBA_API", "http://127.0.0.1:5001")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

app = Flask(__name__)

# Explicit CORS — allows all origins, all methods, including preflight OPTIONS.
# This fixes "Unable to load enhancement history" when the frontend is on a
# different port (e.g. Vite dev server on 5173 calling Flask on 5003).
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    supports_credentials=False,
)

USE_GROQ = os.getenv("RABIA_USE_GROQ", "false").strip().lower() in {"1", "true", "yes"}


# ── DATABASE ─────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS enhancement_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            original_prompt TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS enhancement_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            iteration INTEGER DEFAULT 0,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES enhancement_sessions(id) ON DELETE CASCADE
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS enhancement_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            input_prompt TEXT NOT NULL,
            enhanced_prompt TEXT NOT NULL,
            clarity_score INTEGER DEFAULT 0,
            specificity_score INTEGER DEFAULT 0,
            structure_score INTEGER DEFAULT 0,
            completeness_score INTEGER DEFAULT 0,
            intent_score INTEGER DEFAULT 0,
            overall_score INTEGER DEFAULT 0,
            weaknesses TEXT,
            improvements TEXT,
            recommendations TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES enhancement_sessions(id) ON DELETE CASCADE
        )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_enhancement_sessions_user ON enhancement_sessions(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_enhancement_messages_session ON enhancement_messages(session_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_enhancement_versions_session ON enhancement_versions(session_id)")

    db.commit()
    db.close()


# ── AUTH INTEGRATION ──────────────────────────────────────────
def get_current_user_from_areeba(token: str):
    if not token:
        return None
    try:
        response = requests.get(
            f"{AREEBA_API}/api/areeba/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        user = data.get("user") or data
        return {
            "id": int(user["id"]),
            "name": user.get("name") or user.get("username") or "User",
            "email": user.get("email", ""),
        }
    except Exception:
        return None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()

        user = get_current_user_from_areeba(token)
        if not user:
            return jsonify({"error": "Unauthorized. Please sign in again."}), 401

        request.current_user = user
        request.auth_token = token
        return fn(*args, **kwargs)

    return wrapper


# ── HELPERS ───────────────────────────────────────────────────
def row_to_dict(row):
    return dict(row) if row else None


def safe_json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def clean_text(text: str | None, max_len: int = 6000) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def make_title(prompt: str) -> str:
    words = clean_text(prompt, 80)
    if len(words) <= 45:
        return words or "New enhancement"
    return words[:45].rstrip() + "..."


def blank_scores() -> dict:
    return {
        "clarity": 0,
        "specificity": 0,
        "structure": 0,
        "completeness": 0,
        "intent": 0,
        "overall": 0,
    }


# ── CORE FIX: extract_topic ───────────────────────────────────
# Old version left full phrases like "how to make biryani" as the topic.
# New version strips leading action verbs AND how-to patterns so the topic
# becomes the actual subject: "biryani", "a college essay", etc.

_STRIP_PATTERNS = [
    r"^(please\s+)?how\s+(do\s+i|to|can\s+i|should\s+i)\s+",
    r"^(please\s+)?(explain|describe|tell me about|tell me something about|what is|what are|define|give me information about)\s+",
    r"^(please\s+)?(write|create|make|generate|draft|prepare|build|design|help me write|help me create|help me make)\s+",
    r"^(can you|could you|i want you to|help me)\s+(write|create|make|generate|draft|prepare|build|design)?\s*",
    r"^(i need|i want)\s+(a\s+|an\s+|to\s+)?",
]


def extract_topic(prompt: str) -> str:
    """Strip leading action phrases; return the core subject of the prompt."""
    text = clean_text(prompt, 500).strip().strip('"').strip("'")
    cleaned = text

    # Apply patterns until none match anymore (handles stacked phrases)
    changed = True
    while changed:
        changed = False
        for pattern in _STRIP_PATTERNS:
            new = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            if new != cleaned:
                cleaned = new
                changed = True

    cleaned = cleaned.rstrip("?.!")
    return cleaned if cleaned else text


def sentence_case(text: str) -> str:
    text = clean_text(text, 800)
    return text[:1].upper() + text[1:] if text else text


def detect_prompt_type(prompt: str) -> str:
    lower = clean_text(prompt, 2000).lower()

    if any(w in lower for w in ["email", "letter", "leave application", "application for", "application to", "request letter", "formal application"]):
        return "formal_writing"
    if any(w in lower for w in ["college essay", "personal statement", "application essay", "admission essay"]):
        return "college_essay"
    if any(w in lower for w in ["recipe", "how to cook", "how to make", "how to bake", "biryani", "pasta", "cake", "curry", "food", "dish", "meal"]):
        return "recipe"
    if any(w in lower for w in ["explain", "tell me about", "tell me something about", "what is", "what are", "define", "describe"]):
        return "explanation"
    if any(w in lower for w in ["website", "web app", "web application", "mobile app", "mobile application", "software application", "portfolio", "landing page", "dashboard", "management system"]):
        return "product_build"
    if any(w in lower for w in ["essay", "article", "blog", "report", "paragraph", "summary", "assignment"]):
        return "long_writing"
    if any(w in lower for w in ["compare", "difference", "differentiate", "versus", "vs", "pros and cons", "advantages and disadvantages"]):
        return "comparison"
    if any(w in lower for w in ["code", "program", "python", "javascript", "react", "api", "database", "algorithm", "debug"]):
        return "technical"
    if any(w in lower for w in ["presentation", "slides", "ppt", "speech"]):
        return "presentation"
    if any(w in lower for w in ["lesson", "study plan", "schedule", "roadmap", "learn"]):
        return "learning_plan"
    if any(w in lower for w in ["how to", "steps to", "guide to", "tutorial"]):
        return "how_to"
    return "general"


ANSWER_LIKE_PATTERNS = [
    r"\bis\s+(a|an|the)\b",
    r"\bare\s+(a|an|the|used|known)\b",
    r"\brefers to\b",
    r"\bis defined as\b",
    r"\bcommonly used\b",
    r"\bplays a crucial role\b",
    r"\bfor example\b",
    r"\bin conclusion\b",
    r"\boverall\b",
]


def looks_like_answer(original: str, result: str) -> bool:
    """Return True when Groq answered the prompt instead of improving it."""
    text = clean_text(result, 8000)
    if not text:
        return True

    lower = text.lower()
    original_lower = clean_text(original, 1000).lower()
    prompt_instruction_starts = (
        "explain ",
        "write ",
        "create ",
        "draft ",
        "generate ",
        "provide ",
        "describe ",
        "compare ",
        "design ",
        "prepare ",
        "produce ",
        "develop ",
        "summarize ",
        "analyze ",
        "help me ",
    )

    starts_like_prompt = lower.startswith(prompt_instruction_starts)
    has_answer_markers = any(re.search(pattern, lower) for pattern in ANSWER_LIKE_PATTERNS)

    if starts_like_prompt and not has_answer_markers:
        return False

    if len(text.split()) > 90 and has_answer_markers:
        return True

    if original_lower.startswith(("what is ", "what are ", "define ", "tell me about ", "explain ")):
        return not starts_like_prompt

    return has_answer_markers and not starts_like_prompt


# ── CORE FIX: build_enhanced_prompt ──────────────────────────
# Root cause of both bugs:
# 1. The "general" branch wrapped the raw prompt inside "Write a well-structured {prompt}"
#    which caused Version 2 to wrap that wrapped text again.
# 2. make_second_version / make_third_version received `base_prompt` (already enhanced v1 text)
#    and appended to it — producing the doubled content seen in Version 2.
#
# Fix:
# - All branches build from `topic` (clean extracted subject), never from the raw prompt.
# - make_second_version / make_third_version also rebuild from `topic`, not from base_prompt.
# - The iteration parameter selects the version BEFORE returning — no separate v2/v3 functions
#   that could re-wrap existing output.

ENHANCEMENT_SYSTEM_PROMPT = """You are a Prompt Enhancer, not an answering assistant.
Your only task is to polish the raw user prompt and return a stronger prompt that another AI can answer later.

Core Behavior:
- Understand the user intent deeply.
- Rewrite the user's vague or rough prompt in a more professional, optimized, and explicit way.
- Improve clarity, specificity, and usability for AI models.
- Preserve the user's original intent.
- Do NOT copy or preserve original wording.
- Do NOT answer the user's prompt.
- Do NOT provide factual information about the prompt topic.
- Do NOT solve, explain, define, calculate, recommend, or generate the requested final content.
- Do NOT use templates, predefined formats, or fixed wrappers.
- Do NOT add explanations, comments, or meta text.
- Do NOT ask questions.
- Do NOT return multiple options.

Strict Output Rules:
- Output ONLY the enhanced prompt text that should be sent to another AI.
- No headings, no labels, no prefixes like "Improved Prompt".
- No extra formatting or markdown unless necessary for meaning.
- Keep it natural and human-like but optimized for AI understanding.

Transformation Goals:
- Make vague instructions precise.
- Expand missing context logically (without hallucinating facts).
- Remove redundancy.
- Improve instruction clarity for best model execution.

Example:
Raw user input: what is retinol
Correct output: Explain retinol in clear beginner-friendly language. Include what it is, how it is commonly used in skincare, key benefits, possible side effects or precautions, and practical examples. Use organized sections and a concise summary.
Incorrect output: Retinol is a derivative of vitamin A...
"""


def call_groq(prompt: str, iteration: int) -> str | None:
    """Call Groq API with the system prompt. Returns enhanced text or None on failure."""
    if not USE_GROQ or not has_grok_api_keys():
        return None
    try:
        iteration_note = ""
        if iteration == 2:
            iteration_note = " Make it more detailed and comprehensive than a basic enhancement."
        elif iteration >= 3:
            iteration_note = " Make it highly polished, precise, and production-ready. This is the final refined version."

        completion = create_chat_completion(
            action="rabia prompt enhancement",
            model=GROQ_MODEL,
            max_tokens=1000,
            temperature=0.4,
            messages=[
                {"role": "system", "content": ENHANCEMENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Enhance this raw user prompt. Return only the improved prompt, "
                        "not the answer to it.\n\n"
                        f"Raw prompt: {prompt}{iteration_note}"
                    ),
                },
            ],
        )
        result = completion.choices[0].message.content or ""
        result = result.strip()
        if looks_like_answer(prompt, result):
            print("[Groq] Ignored answer-like response; using fallback templates.")
            return None
        return result or None
    except Exception as e:
        print(f"[Groq] Error: {e}")
        return None


def build_enhanced_prompt(prompt: str, iteration: int = 1) -> str:
    """
    Try Groq first. Fall back to rule-based engine if Groq is unavailable.
    Each iteration is independent — no chaining of prior output.
    """
    original = clean_text(prompt, 2200)

    # ── Groq path ──
    groq_result = call_groq(original, iteration)
    if groq_result:
        return clean_text(groq_result, 8000)

    # ── Rule-based fallback ──
    lower = original.lower()
    topic = sentence_case(extract_topic(original))
    prompt_type = detect_prompt_type(original)

    if prompt_type == "college_essay":
        versions = [
            f"Help me write a compelling college essay about {topic}. Include a strong hook, personal story or experience, clear theme, specific details that show character, reflection on what was learned, and a memorable conclusion. Keep the tone authentic and personal.",
            f"Write a standout college application essay about {topic}. Open with a vivid hook that grabs attention, develop a focused personal narrative with specific moments and sensory details, reveal character and values through the story, reflect meaningfully on growth or lessons learned, and close with a forward-looking statement that ties back to the opening. Keep the voice genuine and the length appropriate for a college application.",
            f"Craft a polished, authentic college essay about {topic}. Begin with an engaging scene or moment that draws the reader in immediately. Develop a clear central theme woven throughout the narrative. Use concrete details, dialogue if appropriate, and personal reflection to show — not just tell — who you are and what matters to you. End with a resonant conclusion that connects your experience to your future goals. Aim for a natural, confident voice that feels uniquely yours.",
        ]
    elif prompt_type == "recipe":
        versions = [
            f"Provide a complete recipe for {topic}. Include all ingredients with exact quantities, step-by-step cooking instructions, cooking times and temperatures, helpful tips for beginners, and serving suggestions.",
            f"Write a detailed, easy-to-follow recipe for {topic}. List all ingredients with precise measurements, preparation steps before cooking, numbered cooking instructions with timing, heat settings, visual cues for doneness, common mistakes to avoid, and suggestions for variations or serving.",
            f"Create a thorough, beginner-friendly recipe guide for {topic}. Cover ingredient list with exact amounts, pre-preparation notes, detailed step-by-step cooking method with times and temperatures, tips for getting the best results, common pitfalls and how to avoid them, plating or serving ideas, and storage instructions if relevant.",
        ]
    elif prompt_type == "how_to":
        versions = [
            f"Explain how to {topic} clearly and step by step. Cover the purpose, required materials or prerequisites, numbered steps in order, important tips, and what the final result should look like.",
            f"Write a clear, practical guide on how to {topic}. Include an overview of the goal, list of tools or prerequisites, detailed numbered steps with explanations, helpful tips at key stages, common mistakes to avoid, and a brief summary of the expected outcome.",
            f"Create a complete, beginner-friendly tutorial on how to {topic}. Start with what you will achieve and why it matters. List all materials or prerequisites. Provide detailed numbered steps with explanations and tips at each stage. Include common errors and how to fix them. End with troubleshooting advice and the expected final result.",
        ]
    elif prompt_type == "explanation":
        versions = [
            f"Provide a clear, beginner-friendly explanation of {topic}. Cover what it means, why it matters, its key concepts, main features, practical uses, advantages, limitations, and simple real-world examples. Use clear headings and simple language.",
            f"Explain {topic} in a comprehensive, beginner-friendly way. Start with a simple definition, then describe its purpose, core concepts, major features, real-world applications, benefits, limitations, and common misconceptions. Include easy examples and a short recap.",
            f"Prepare a polished educational explanation of {topic} for beginners. Include a concise definition, why it is important, key ideas, practical examples, real-world use cases, advantages, limitations, common mistakes or misconceptions, and a final summary. Use clear headings and organized teaching style.",
        ]
    elif prompt_type == "product_build":
        if "portfolio" in lower:
            versions = [
                "Design a professional personal portfolio website. Include homepage, about, skills, projects, and contact sections. Use a modern responsive layout, clean visual style, and clear navigation.",
                "Design and develop a professional personal portfolio website. Define the objective, target audience, homepage structure, about section, skills showcase, projects gallery with descriptions, contact form, responsive layout, modern visual style, accessibility requirements, and deployment-ready deliverables.",
                "Create a complete specification for a polished personal portfolio website. Cover project goal, target audience, brand identity, page-by-page content plan, navigation flow, interactive features, responsive design behavior, accessibility standards, performance expectations, technology stack recommendations, and final deliverables for development.",
            ]
        elif "dashboard" in lower:
            versions = [
                "Design a clear, responsive dashboard interface. Include the purpose, key metrics, navigation, data sections, filters, charts or tables, and user actions.",
                "Design and develop a responsive dashboard interface. Define the dashboard purpose, target users, key metrics to display, navigation structure, data sections, filter controls, chart or table types, user actions, responsive behavior, and final UI/UX deliverables.",
                "Prepare a complete development brief for a responsive dashboard. Specify the objective, target users, brand direction, sitemap, metric definitions, component library, data visualization types, filter logic, user permissions, accessibility requirements, performance goals, and final deliverables.",
            ]
        else:
            versions = [
                f"Design and plan a complete {topic}. Define its purpose, target users, core features, user flow, interface structure, data requirements, technology considerations, and final deliverables.",
                f"Create a detailed specification for {topic}. Cover the project goal, target audience, feature list, user journeys, interface structure, data requirements, technology stack considerations, accessibility needs, performance expectations, and implementation-ready deliverables.",
                f"Prepare a comprehensive development-ready brief for {topic}. Specify the objective, target users, brand direction, sitemap, page-by-page requirements, feature list, UI/UX guidelines, data model, accessibility standards, performance goals, technology recommendations, testing checklist, and final deliverables.",
            ]
    elif prompt_type == "formal_writing":
        if "leave" in lower and "application" in lower:
            versions = [
                "Write a polite and professional leave application. Include a clear subject line, respectful greeting, reason for leave, requested dates or duration, assurance of responsibility, a courteous closing, and the sender's name.",
                "Draft a complete, respectful leave application ready for submission. Include a suitable subject, formal greeting, clear leave reason, exact dates or duration, request for approval, assurance about pending responsibilities, polite closing, and sender details.",
                "Write a polished, formal leave application ready for submission. Include a precise subject line, respectful salutation, brief reason for leave, exact leave dates, request for approval, note about managing responsibilities, courteous closing, and sender name.",
            ]
        elif "email" in lower:
            versions = [
                f"Write a clear and professional email about {topic}. Include an appropriate subject line, polite greeting, concise purpose, necessary details, a clear request or message, and professional closing.",
                f"Draft a professional, ready-to-send email about {topic}. Include a specific subject line, polite salutation, concise opening stating the purpose, all necessary details organized clearly, a direct call to action or request, and a professional sign-off.",
                f"Write a polished professional email about {topic}. Cover a compelling subject line, warm but formal greeting, concise context-setting opening, well-organized body with all relevant details, clear next step or request, professional closing, and sender signature.",
            ]
        else:
            versions = [
                f"Write a clear, polite, and professional document about {topic}. Include the purpose, necessary details, formal tone, organized structure, and a suitable closing.",
                f"Draft a formal, well-structured document about {topic}. Define the purpose clearly, organize the content logically, include all necessary details, maintain a professional tone throughout, and end with an appropriate closing statement.",
                f"Prepare a polished, submission-ready formal document about {topic}. Include a clear heading or subject, organized sections covering all necessary points, professional and respectful tone, specific details required for the context, and a formal closing with sender information.",
            ]
    elif prompt_type == "long_writing":
        versions = [
            f"Write a complete and well-organized piece about {topic}. Include a strong introduction, relevant background, clear main points, supporting details, practical examples, smooth transitions, and a concise conclusion.",
            f"Write a thorough, engaging piece about {topic}. Open with a strong hook, provide necessary background, develop main ideas with supporting evidence and examples, use smooth transitions between sections, maintain a consistent tone, and end with a meaningful conclusion.",
            f"Produce a polished, publication-ready piece about {topic}. Begin with a compelling introduction that establishes context and thesis. Develop each main point with evidence, examples, and analysis. Use clear transitions, varied sentence structure, and appropriate tone. Conclude with a strong summary and lasting impression.",
        ]
    elif prompt_type == "comparison":
        versions = [
            f"Compare {topic} in a clear and structured way. Define each item, explain key similarities and differences, discuss advantages and disadvantages, include practical examples, and end with a concise conclusion.",
            f"Provide a detailed, structured comparison of {topic}. Define each option, cover key similarities and differences across relevant criteria, weigh advantages and disadvantages, give practical examples, include a comparison table, and conclude with guidance on when each option is most suitable.",
            f"Write a comprehensive, balanced comparison of {topic}. Analyze across multiple criteria using a structured format or table. Discuss advantages, disadvantages, use cases, and trade-offs. Provide real-world examples and end with a clear recommendation based on different user needs.",
        ]
    elif prompt_type == "technical":
        versions = [
            f"Provide a clear technical guide for {topic}. Explain the objective, required concepts or tools, step-by-step process, example code or commands where useful, expected output, and common mistakes to avoid.",
            f"Write a detailed technical guide for {topic}. Cover prerequisites, core concepts, a step-by-step implementation process with annotated code examples, expected outputs at each stage, error handling tips, and a concise summary.",
            f"Create a comprehensive developer guide for {topic}. Include an overview of the goal, prerequisite knowledge and tools, detailed step-by-step implementation with well-commented code, expected outputs, edge cases, common errors and fixes, performance considerations, and a summary with next steps.",
        ]
    elif prompt_type == "presentation":
        versions = [
            f"Create a clear presentation outline about {topic}. Include a strong title, slide-by-slide structure, key talking points, simple explanations, relevant examples, visual suggestions, and a short conclusion.",
            f"Design a well-structured presentation on {topic}. Provide a title slide, agenda, background slide, main content slides with key points and visuals, a data or example slide, a summary slide, and a closing call to action.",
            f"Produce a complete, audience-ready presentation plan for {topic}. Include title and agenda slides, section-by-section content with key messages, supporting data and visuals for each slide, speaker note guidance, a strong conclusion slide, and a Q&A preparation guide.",
        ]
    elif prompt_type == "learning_plan":
        versions = [
            f"Create a practical learning plan for {topic}. Include the learning goal, required background, ordered topics to study, practice activities, estimated timeline, checkpoints, and measurable outcomes.",
            f"Design a structured learning plan for {topic}. Define the end goal, list prerequisites, break the subject into ordered modules, include resources for each module, suggest practice exercises, set a realistic timeline with milestones, and define clear success criteria.",
            f"Build a comprehensive, self-paced learning roadmap for {topic}. Structure content into ordered phases with specific topics, recommended resources, hands-on projects, and time estimates. Include checkpoints for self-assessment and measurable final outcomes.",
        ]
    else:
        versions = [
            f"Produce a clear, focused, and well-structured response on {topic}. Cover the main objective, essential background, key details, and practical examples. Use simple language, organized sections, and a professional tone.",
            f"Write a comprehensive, well-organized response about {topic}. Include necessary context, clearly structured main points with supporting details, relevant examples, and a concise conclusion. Tailor the depth and tone to be genuinely useful for the intended audience.",
            f"Create a polished, complete response about {topic}. Start with context and purpose, develop the core ideas with organized sections and supporting evidence, include practical examples, and conclude with a clear summary. Use professional language and a structure that makes the content immediately usable.",
        ]

    idx = min(iteration - 1, len(versions) - 1)
    return clean_text(versions[idx], 8000)

# ── ROUTES ────────────────────────────────────────────────────

@app.route("/api/rabia/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "rabia-enhancer", "timestamp": now()})



# Handle preflight OPTIONS for all /api/rabia/* routes
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        from flask import Response
        res = Response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return res, 200


# ── /history alias ────────────────────────────────────────────
# Frontends calling /api/rabia/history get a combined session+version summary.
@app.route("/api/rabia/enhancer/history", methods=["GET"])
@require_auth
def get_history():
    user_id = request.current_user["id"]
    db = get_db()
    rows = db.execute(
        """SELECT
               s.id AS session_id,
               s.title,
               s.original_prompt,
               s.status,
               s.created_at,
               s.updated_at,
               COUNT(v.id) AS version_count,
               MAX(v.enhanced_prompt) AS latest_enhanced_prompt
           FROM enhancement_sessions s
           LEFT JOIN enhancement_versions v
               ON v.session_id = s.id AND v.user_id = s.user_id
           WHERE s.user_id = ?
           GROUP BY s.id
           ORDER BY s.updated_at DESC""",
        (user_id,)
    ).fetchall()
    db.close()
    return jsonify({"history": [row_to_dict(r) for r in rows]})


# ── Session management ────────────────────────────────────────

@app.route("/api/rabia/enhancer/sessions", methods=["GET"])
@require_auth
def get_sessions():
    user_id = request.current_user["id"]
    db = get_db()
    rows = db.execute(
        "SELECT * FROM enhancement_sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    ).fetchall()
    db.close()
    return jsonify({"sessions": [row_to_dict(r) for r in rows]})


@app.route("/api/rabia/enhancer/sessions", methods=["POST"])
@require_auth
def create_session():
    user_id = request.current_user["id"]
    data = request.get_json() or {}
    original_prompt = clean_text(data.get("prompt", ""), 2200)
    title = make_title(original_prompt) if original_prompt else "New enhancement"

    db = get_db()
    cur = db.execute(
        "INSERT INTO enhancement_sessions (user_id, title, original_prompt) VALUES (?, ?, ?)",
        (user_id, title, original_prompt)
    )
    db.commit()
    session_id = cur.lastrowid
    row = db.execute("SELECT * FROM enhancement_sessions WHERE id = ?", (session_id,)).fetchone()
    db.close()
    return jsonify({"session": row_to_dict(row)}), 201


@app.route("/api/rabia/enhancer/sessions/<int:session_id>", methods=["GET"])
@require_auth
def get_session(session_id):
    user_id = request.current_user["id"]
    db = get_db()
    session = _get_session_with_messages(db, session_id, user_id)
    db.close()
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"session": session})


@app.route("/api/rabia/enhancer/sessions/<int:session_id>", methods=["DELETE"])
@require_auth
def delete_session(session_id):
    user_id = request.current_user["id"]
    db = get_db()
    db.execute(
        "DELETE FROM enhancement_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    db.commit()
    db.close()
    return jsonify({"message": "Session deleted"})


# ── Enhancement ───────────────────────────────────────────────

@app.route("/api/rabia/enhancer/enhance", methods=["POST"])
@require_auth
def enhance_prompt():
    """
    Enhance a prompt.

    Body (JSON):
        prompt      : str  – the user's raw prompt (required)
        session_id  : int  – existing session to attach to (optional)
        iteration   : int  – which version to produce, 1/2/3 (default 1)
    """
    user_id = request.current_user["id"]
    data = request.get_json() or {}

    raw_prompt = clean_text(data.get("prompt", ""), 2200)
    if not raw_prompt:
        return jsonify({"error": "prompt is required"}), 400

    # iteration must come from the request, not be inferred from DB count,
    # so the frontend controls exactly which version is produced.
    iteration = max(1, min(int(data.get("iteration", 1)), 3))

    # ── Session ──
    session_id = data.get("session_id")
    db = get_db()

    if session_id:
        row = db.execute(
            "SELECT * FROM enhancement_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        ).fetchone()
        if not row:
            db.close()
            return jsonify({"error": "Session not found"}), 404
    else:
        title = make_title(raw_prompt)
        cur = db.execute(
            "INSERT INTO enhancement_sessions (user_id, title, original_prompt) VALUES (?, ?, ?)",
            (user_id, title, raw_prompt)
        )
        db.commit()
        session_id = cur.lastrowid

    # ── Build the enhanced prompt (pure local logic, no LLM needed) ──
    enhanced = build_enhanced_prompt(raw_prompt, iteration)

    scores = blank_scores()

    # ── Persist version ──
    db.execute(
        """INSERT INTO enhancement_versions
               (session_id, user_id, version_number, input_prompt, enhanced_prompt,
                clarity_score, specificity_score, structure_score,
                completeness_score, intent_score, overall_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, user_id, iteration, raw_prompt, enhanced,
            scores["clarity"], scores["specificity"], scores["structure"],
            scores["completeness"], scores["intent"], scores["overall"],
        )
    )

    # ── Persist messages ──
    db.execute(
        "INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration) VALUES (?, ?, 'user', ?, ?)",
        (session_id, user_id, raw_prompt, iteration)
    )
    db.execute(
        "INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration) VALUES (?, ?, 'assistant', ?, ?)",
        (session_id, user_id, enhanced, iteration)
    )

    db.execute(
        "UPDATE enhancement_sessions SET updated_at = ? WHERE id = ?",
        (now(), session_id)
    )
    db.commit()

    # Frontend calls syncSessionFromResponse(data.session) so return full session
    session = _get_session_with_messages(db, session_id, user_id)
    db.close()
    return jsonify({"session": session})


# ── Enhance Again ────────────────────────────────────────────
# Frontend calls POST /api/rabia/enhancer/sessions/{id}/enhance-again

@app.route("/api/rabia/enhancer/sessions/<int:session_id>/enhance-again", methods=["POST"])
@require_auth
def enhance_again(session_id):
    user_id = request.current_user["id"]
    db = get_db()

    session_row = db.execute(
        "SELECT * FROM enhancement_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()

    if not session_row:
        db.close()
        return jsonify({"error": "Session not found"}), 404

    # Find what version we're on so next one is +1
    last_version = db.execute(
        "SELECT MAX(version_number) as max_v FROM enhancement_versions WHERE session_id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()
    next_iteration = min((last_version["max_v"] or 0) + 1, 3)

    original_prompt = session_row["original_prompt"] or ""
    enhanced = build_enhanced_prompt(original_prompt, next_iteration)
    scores = blank_scores()

    db.execute(
        """INSERT INTO enhancement_versions
               (session_id, user_id, version_number, input_prompt, enhanced_prompt,
                clarity_score, specificity_score, structure_score,
                completeness_score, intent_score, overall_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, next_iteration, original_prompt, enhanced,
         scores["clarity"], scores["specificity"], scores["structure"],
         scores["completeness"], scores["intent"], scores["overall"])
    )
    db.execute(
        "INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration) VALUES (?, ?, 'user', ?, ?)",
        (session_id, user_id, "enhance again", next_iteration)
    )
    db.execute(
        "INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration) VALUES (?, ?, 'assistant', ?, ?)",
        (session_id, user_id, enhanced, next_iteration)
    )
    db.execute("UPDATE enhancement_sessions SET updated_at = ? WHERE id = ?", (now(), session_id))
    db.commit()

    # Return full session with messages so frontend can sync
    session = _get_session_with_messages(db, session_id, user_id)
    db.close()
    return jsonify({"session": session})


def _get_session_with_messages(db, session_id: int, user_id: int) -> dict:
    """Return session dict with messages and latest_version attached."""
    row = db.execute(
        "SELECT * FROM enhancement_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()
    if not row:
        return {}
    session = row_to_dict(row)

    msgs = db.execute(
        "SELECT * FROM enhancement_messages WHERE session_id = ? AND user_id = ? ORDER BY created_at ASC",
        (session_id, user_id)
    ).fetchall()
    session["messages"] = [row_to_dict(m) for m in msgs]

    latest = db.execute(
        "SELECT * FROM enhancement_versions WHERE session_id = ? AND user_id = ? ORDER BY version_number DESC LIMIT 1",
        (session_id, user_id)
    ).fetchone()
    session["latest_version"] = row_to_dict(latest)

    return session


# ── Version history ───────────────────────────────────────────

@app.route("/api/rabia/enhancer/sessions/<int:session_id>/versions", methods=["GET"])
@require_auth
def get_versions(session_id):
    user_id = request.current_user["id"]
    db = get_db()
    rows = db.execute(
        """SELECT * FROM enhancement_versions
           WHERE session_id = ? AND user_id = ?
           ORDER BY version_number ASC""",
        (session_id, user_id)
    ).fetchall()
    db.close()
    return jsonify({"versions": [row_to_dict(r) for r in rows]})


# ── Message history ───────────────────────────────────────────

@app.route("/api/rabia/enhancer/sessions/<int:session_id>/messages", methods=["GET"])
@require_auth
def get_messages(session_id):
    user_id = request.current_user["id"]
    db = get_db()
    rows = db.execute(
        """SELECT * FROM enhancement_messages
           WHERE session_id = ? AND user_id = ?
           ORDER BY created_at ASC""",
        (session_id, user_id)
    ).fetchall()
    db.close()
    return jsonify({"messages": [row_to_dict(r) for r in rows]})


# ── Startup ───────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("RABIA_PORT", 5003))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    print(f"[Rabia] Starting on port {port} | debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)
