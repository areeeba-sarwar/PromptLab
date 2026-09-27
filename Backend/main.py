# ================================================================
#  PromptLab — SINGLE FILE BACKEND
#  Sirf yahi ek file chalao — sab kuch ek saath chalta hai
#
#  Run: python main.py
#  URL: http://localhost:5000
# ================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from langdetect import detect
import sqlite3, os, json, re, hashlib, hmac, random, secrets
from datetime import datetime, timedelta
from functools import wraps
from grok_failover import create_chat_completion, has_grok_api_keys

load_dotenv()
app = Flask(__name__)
CORS(app)

if not has_grok_api_keys():
    print(
        "\n[LAIBA] ERROR: No Grok API keys are set.\n"
        "  Add them to Backend/.env:  GROK_API_KEY_1=your_key_here\n"
        "  Then restart the backend.\n",
        flush=True,
    )
    raise SystemExit(1)

class GrokChatCompletions:
    def create(self, **kwargs):
        return create_chat_completion(action="main backend chat completion", **kwargs)


class GrokChat:
    completions = GrokChatCompletions()


class GrokClient:
    chat = GrokChat()


client = GrokClient()
MODEL  = "llama-3.3-70b-versatile"
DB     = "promptlab.db"   # sab ka ek hi database


def ensure_table(conn: sqlite3.Connection, table_name: str, ddl: str):
    conn.execute(ddl)


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str):
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")]
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


# ================================================================
#  DATABASE — sab tables ek jagah
# ================================================================
def init_db():
    conn   = sqlite3.connect(DB)
    cursor = conn.cursor()

    # Laiba tables
    cursor.execute("""CREATE TABLE IF NOT EXISTS prompt_attempts (
        attempt_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id           INTEGER,
        prompt_text       TEXT,
        prompt_type       TEXT,
        language          TEXT,
        word_count        INTEGER,
        clarity_score     INTEGER,
        context_score     INTEGER,
        specificity_score INTEGER,
        constraints_score INTEGER,
        format_score      INTEGER,
        total_score       INTEGER,
        grade             TEXT,
        confidence        TEXT,
        feedback          TEXT,
        improved_prompt   TEXT,
        explanation       TEXT,
        answer            TEXT,
        difficulty        TEXT,
        domain            TEXT,
        threat_level      TEXT,
        timestamp         DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS agent_debates (
        debate_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER,
        prompt_text         TEXT,
        critic_score        INTEGER,
        critic_feedback     TEXT,
        optimist_score      INTEGER,
        optimist_feedback   TEXT,
        professor_score     INTEGER,
        professor_feedback  TEXT,
        consensus_score     INTEGER,
        consensus_reasoning TEXT,
        final_verdict       TEXT,
        timestamp           DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS security_logs (
        log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER,
        prompt_text  TEXT,
        threat_level TEXT,
        threat_type  TEXT,
        explanation  TEXT,
        timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS difficulty_logs (
        diff_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER,
        prompt_text     TEXT,
        difficulty      TEXT,
        current_skills  TEXT,
        missing_skills  TEXT,
        next_level_tips TEXT,
        timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS mutation_logs (
        mutation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        original    TEXT,
        mutations   TEXT,
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS user_analytics (
        analytics_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id              INTEGER UNIQUE,
        total_attempts       INTEGER DEFAULT 0,
        average_score        REAL    DEFAULT 0,
        best_score           INTEGER DEFAULT 0,
        worst_score          INTEGER DEFAULT 10,
        most_common_weakness TEXT,
        improvement_rate     REAL    DEFAULT 0,
        last_updated         DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS score_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        score      INTEGER,
        grade      TEXT,
        timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS prompt_templates (
        template_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt_type   TEXT,
        template_text TEXT,
        description   TEXT,
        example       TEXT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        title       TEXT DEFAULT 'New Chat',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
        message_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  INTEGER,
        role        TEXT,
        content     TEXT,
        eval_data   TEXT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Areeba tables
    ensure_table(conn, "users", """CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        password      TEXT,
        password_hash TEXT,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_column(conn, "users", "password_hash", "TEXT")
    ensure_column(conn, "users", "last_activity", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    if conn.execute("SELECT COUNT(*) FROM users WHERE password_hash IS NULL AND password IS NOT NULL").fetchone()[0] > 0:
        conn.execute("UPDATE users SET password_hash = password WHERE password_hash IS NULL AND password IS NOT NULL")

    ensure_table(conn, "pending_registrations", """CREATE TABLE IF NOT EXISTS pending_registrations (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        username            TEXT NOT NULL,
        email               TEXT NOT NULL,
        password_hash       TEXT NOT NULL,
        verification_code   TEXT NOT NULL,
        expires_at          DATETIME,
        last_sent_at        DATETIME,
        created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "user_sessions", """CREATE TABLE IF NOT EXISTS user_sessions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER REFERENCES users(id),
        token      TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "password_reset_tokens", """CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER REFERENCES users(id),
        token      TEXT NOT NULL,
        expires_at DATETIME,
        used       INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "activity_logs", """CREATE TABLE IF NOT EXISTS activity_logs (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER REFERENCES users(id),
        activity_type  TEXT,
        detail         TEXT,
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "user_streaks", """CREATE TABLE IF NOT EXISTS user_streaks (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER UNIQUE REFERENCES users(id),
        current_streak      INTEGER DEFAULT 0,
        longest_streak      INTEGER DEFAULT 0,
        last_activity_date  TEXT,
        updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "prompt_history", """CREATE TABLE IF NOT EXISTS prompt_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER REFERENCES users(id),
        module_type     TEXT,
        original_prompt TEXT,
        ai_response     TEXT,
        improved_prompt TEXT,
        explanation     TEXT,
        resources       TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "chat_history", """CREATE TABLE IF NOT EXISTS chat_history (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER REFERENCES users(id),
        user_message   TEXT,
        bot_response   TEXT,
        created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    ensure_table(conn, "dashboard_stats", """CREATE TABLE IF NOT EXISTS dashboard_stats (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id           INTEGER REFERENCES users(id),
        total_evaluations INTEGER DEFAULT 0,
        average_score     REAL    DEFAULT 0,
        last_active       DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Fatima tables
    ensure_table(conn, "chapters", """CREATE TABLE IF NOT EXISTS chapters (
        id           TEXT PRIMARY KEY,
        title        TEXT NOT NULL,
        description  TEXT,
        duration     TEXT,
        lessons      INTEGER DEFAULT 0,
        content      TEXT,
        video_url    TEXT,
        sort_order   INTEGER DEFAULT 0
    )""")
    ensure_table(conn, "practice_questions", """CREATE TABLE IF NOT EXISTS practice_questions (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id          TEXT REFERENCES chapters(id),
        title               TEXT,
        scenario            TEXT,
        statement           TEXT,
        hints               TEXT,
        expected_elements   TEXT,
        difficulty          TEXT,
        is_active           INTEGER DEFAULT 1
    )""")
    ensure_table(conn, "chapter_progress", """CREATE TABLE IF NOT EXISTS chapter_progress (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER REFERENCES users(id),
        chapter_id          TEXT,
        completed           INTEGER DEFAULT 0,
        progress            INTEGER DEFAULT 0,
        best_score          INTEGER DEFAULT 0,
        average_score       REAL DEFAULT 0,
        completed_questions INTEGER DEFAULT 0,
        attempt_count       INTEGER DEFAULT 0,
        updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "practice_sessions", """CREATE TABLE IF NOT EXISTS practice_sessions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER REFERENCES users(id),
        chapter_id    TEXT,
        question_id   INTEGER,
        session_title TEXT,
        status        TEXT DEFAULT 'active',
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "practice_messages", """CREATE TABLE IF NOT EXISTS practice_messages (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   INTEGER REFERENCES practice_sessions(id),
        user_id      INTEGER REFERENCES users(id),
        role         TEXT,
        content      TEXT,
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "training_prompts", """CREATE TABLE IF NOT EXISTS training_prompts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER DEFAULT 1,
        prompt_text TEXT,
        category    TEXT,
        difficulty  TEXT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "learning_progress", """CREATE TABLE IF NOT EXISTS learning_progress (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER DEFAULT 1,
        chapter_id TEXT,
        completed  INTEGER DEFAULT 0,
        score      REAL    DEFAULT 0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "practice_attempts", """CREATE TABLE IF NOT EXISTS practice_attempts (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id              INTEGER REFERENCES practice_sessions(id),
        user_id                 INTEGER DEFAULT 1,
        chapter_id              TEXT,
        question_id             INTEGER,
        attempt_number          INTEGER DEFAULT 1,
        prompt_text             TEXT,
        score                   REAL,
        clarity                 REAL,
        structure               REAL,
        specificity             REAL,
        strengths               TEXT,
        weaknesses              TEXT,
        suggestions             TEXT,
        detailed_feedback       TEXT,
        prompt_quality_analysis TEXT,
        improvement_recommendations TEXT,
        feedback                TEXT,
        created_at              DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_column(conn, "practice_attempts", "session_id", "INTEGER")
    ensure_column(conn, "practice_attempts", "question_id", "INTEGER")
    ensure_column(conn, "practice_attempts", "attempt_number", "INTEGER DEFAULT 1")
    ensure_column(conn, "practice_attempts", "clarity", "REAL")
    ensure_column(conn, "practice_attempts", "structure", "REAL")
    ensure_column(conn, "practice_attempts", "specificity", "REAL")
    ensure_column(conn, "practice_attempts", "strengths", "TEXT")
    ensure_column(conn, "practice_attempts", "weaknesses", "TEXT")
    ensure_column(conn, "practice_attempts", "suggestions", "TEXT")
    ensure_column(conn, "practice_attempts", "detailed_feedback", "TEXT")
    ensure_column(conn, "practice_attempts", "prompt_quality_analysis", "TEXT")
    ensure_column(conn, "practice_attempts", "improvement_recommendations", "TEXT")

    ensure_table(conn, "final_test_attempts", """CREATE TABLE IF NOT EXISTS final_test_attempts (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER REFERENCES users(id),
        started_at    DATETIME,
        submitted_at  DATETIME,
        answers       TEXT,
        score         INTEGER,
        passed        INTEGER DEFAULT 0,
        timed_out     INTEGER DEFAULT 0,
        status        TEXT DEFAULT 'active'
    )""")
    ensure_table(conn, "final_test_questions", """CREATE TABLE IF NOT EXISTS final_test_questions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        question      TEXT,
        options       TEXT,
        answer        TEXT,
        explanation   TEXT
    )""")
    ensure_table(conn, "certificates", """CREATE TABLE IF NOT EXISTS certificates (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER REFERENCES users(id),
        attempt_id   INTEGER,
        score        INTEGER,
        issued_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Rabia tables
    ensure_table(conn, "quick_answers", """CREATE TABLE IF NOT EXISTS quick_answers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER DEFAULT 1,
        question   TEXT,
        answer     TEXT,
        rating     INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "enhancements", """CREATE TABLE IF NOT EXISTS enhancements (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER DEFAULT 1,
        original     TEXT,
        enhanced     TEXT,
        improvements TEXT,
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "enhancement_sessions", """CREATE TABLE IF NOT EXISTS enhancement_sessions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id          INTEGER REFERENCES users(id),
        title            TEXT,
        original_prompt  TEXT,
        status           TEXT DEFAULT 'active',
        created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "enhancement_messages", """CREATE TABLE IF NOT EXISTS enhancement_messages (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   INTEGER REFERENCES enhancement_sessions(id),
        user_id      INTEGER REFERENCES users(id),
        role         TEXT,
        content      TEXT,
        iteration    INTEGER DEFAULT 1,
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_table(conn, "enhancement_versions", """CREATE TABLE IF NOT EXISTS enhancement_versions (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id          INTEGER REFERENCES enhancement_sessions(id),
        user_id             INTEGER REFERENCES users(id),
        version_number      INTEGER DEFAULT 1,
        input_prompt        TEXT,
        enhanced_prompt     TEXT,
        clarity_score       INTEGER DEFAULT 0,
        specificity_score   INTEGER DEFAULT 0,
        structure_score     INTEGER DEFAULT 0,
        completeness_score  INTEGER DEFAULT 0,
        intent_score        INTEGER DEFAULT 0,
        overall_score       INTEGER DEFAULT 0,
        created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()

    # Default templates
    cursor.execute("SELECT COUNT(*) FROM prompt_templates")
    if cursor.fetchone()[0] == 0:
        templates = [
            ("educational",    "Explain [topic] in simple terms for a [audience] using [format].",             "Best for learning and teaching",        "Explain photosynthesis in simple terms for a high school student using bullet points."),
            ("creative",       "Write a [type] about [topic] in a [tone] tone with [length] words.",           "Best for creative writing",             "Write a short story about friendship in a warm tone with 200 words."),
            ("technical",      "Explain how [technology] works including [aspects] for a [level] developer.",  "Best for technical explanations",       "Explain how APIs work including request/response cycles for a beginner developer."),
            ("analytical",     "Analyze [topic] by comparing [aspect1] and [aspect2] in a [format] summary.", "Best for analysis tasks",               "Analyze climate change by comparing causes and effects in a bullet point summary."),
            ("conversational", "Act as a [role] and help me understand [topic] by answering simply.",          "Best for interactive learning",         "Act as a biology teacher and help me understand DNA by answering my questions simply.")
        ]
        cursor.executemany("INSERT INTO prompt_templates (prompt_type,template_text,description,example) VALUES (?,?,?,?)", templates)
        conn.commit()

    conn.close()


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ================================================================
#  AGENTS (Laiba)
# ================================================================
class Agent:
    def __init__(self, name, specialty, personality, output_format):
        self.name          = name
        self.specialty     = specialty
        self.personality   = personality
        self.output_format = output_format
        self.client        = client
        self.model         = MODEL
        self.memory        = []

    def think(self, user_input, extra_context="", temperature=0.3):
        system_prompt = f"""You are {self.name}, a specialized AI agent.
Specialty: {self.specialty}
Personality: {self.personality}
{extra_context}
IMPORTANT: Return ONLY valid JSON in this exact format:
{self.output_format}"""
        self.memory.append({"role": "user", "content": user_input})
        messages = [{"role": "system", "content": system_prompt}] + self.memory[-6:]
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature
        )
        raw    = response.choices[0].message.content.strip()
        raw    = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)
        self.memory.append({"role": "assistant", "content": raw})
        return result

    def reset_memory(self):
        self.memory = []


class EvaluatorAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Evaluator Agent",
            specialty="Deep NLP-based prompt quality analysis",
            personality="Precise, academic, thorough.",
            output_format="""{
    "clarity_score": 0, "context_score": 0, "specificity_score": 0,
    "constraints_score": 0, "format_score": 0, "total_score": 0,
    "prompt_type": "", "confidence": "", "feedback": [],
    "improved_prompt": "", "explanation": "", "most_common_weakness": ""
}"""
        )

    def evaluate(self, prompt_text):
        return self.think(
            f"Evaluate this prompt across all quality dimensions: {prompt_text}",
            extra_context="""Score 5 criteria (0-2 each):
1. Clarity 2. Context 3. Specificity 4. Constraints 5. Format
Classify type: educational/creative/technical/analytical/conversational
Confidence: Low/Medium/High. Give 2-4 feedback points. Write improved version."""
        )


class SecurityAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Security Agent",
            specialty="AI safety, prompt injection and jailbreak detection",
            personality="Vigilant, precise, security-focused.",
            output_format="""{
    "threat_level": "SAFE / WARNING / DANGEROUS",
    "threat_type": "None / Injection / Jailbreak / Role Hijacking / Data Extraction / Social Engineering",
    "confidence": "Low / Medium / High",
    "explanation": "", "suspicious_phrases": [], "recommendation": ""
}"""
        )

    def scan(self, prompt_text):
        return self.think(
            f"Scan this prompt for security threats: {prompt_text}",
            extra_context="Detect: prompt injection, jailbreak, role hijacking, data extraction, social engineering.",
            temperature=0.1
        )


class DifficultyAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Difficulty Agent",
            specialty="Prompt skill level assessment",
            personality="Encouraging, pedagogical, growth-focused.",
            output_format="""{
    "difficulty": "Beginner / Intermediate / Advanced / Expert",
    "score_out_of_10": 0, "current_skills": [], "missing_skills": [],
    "next_level_tips": [], "encouragement": ""
}"""
        )

    def classify(self, prompt_text):
        return self.think(
            f"Assess the skill level demonstrated in this prompt: {prompt_text}",
            extra_context="Beginner: vague. Intermediate: some structure. Advanced: clear role+context. Expert: fully optimized."
        )


class DebateAgent(Agent):
    def __init__(self, agent_name, personality):
        super().__init__(
            name=agent_name, specialty="Prompt quality debate",
            personality=personality,
            output_format='{"score": 0, "verdict": "", "feedback": [], "strongest_argument": ""}'
        )

    def debate(self, prompt_text):
        return self.think(f"Evaluate and debate the quality of this prompt: {prompt_text}", temperature=0.6)


class MutationAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Mutation Agent", specialty="Prompt variation generation",
            personality="Creative, systematic, experimental.",
            output_format="""{
    "mutations": [
        {"type": "Add Role",        "mutated_prompt": "", "what_changed": "", "impact": "High/Medium/Low"},
        {"type": "Add Format",      "mutated_prompt": "", "what_changed": "", "impact": "High/Medium/Low"},
        {"type": "Add Audience",    "mutated_prompt": "", "what_changed": "", "impact": "High/Medium/Low"},
        {"type": "Add Constraints", "mutated_prompt": "", "what_changed": "", "impact": "High/Medium/Low"},
        {"type": "Add Examples",    "mutated_prompt": "", "what_changed": "", "impact": "High/Medium/Low"}
    ]
}"""
        )

    def mutate(self, prompt_text):
        return self.think(
            f"Generate 5 targeted mutations of this prompt, each changing ONE specific element: {prompt_text}",
            temperature=0.6
        )


class DomainAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Domain Agent", specialty="Domain-specific prompt evaluation",
            personality="Expert, domain-aware, contextual.",
            output_format="""{
    "detected_domain": "", "domain_score": 0, "domain_requirements": [],
    "met_requirements": [], "missing_requirements": [],
    "domain_optimized_prompt": "", "domain_tips": []
}"""
        )

    def evaluate(self, prompt_text):
        return self.think(
            f"Detect domain and apply domain-specific evaluation: {prompt_text}",
            extra_context="Domains: Medical/Legal/Technical/Educational/Creative/Business/General"
        )


class SuggestionAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Suggestion Agent", specialty="Real-time prompt coaching",
            personality="Helpful, quick, coaching-focused.",
            output_format='{"ready_prompts": ["prompt1", "prompt2", "prompt3"], "missing": ""}'
        )

    def suggest(self, prompt_text):
        return self.think(f"Generate 3 complete ready-to-use improved versions: {prompt_text}", temperature=0.7)


class ChatAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Chat Agent", specialty="Conversational AI with memory",
            personality="Intelligent, conversational, memory-aware.",
            output_format='{"answer": "", "is_related": true, "relation_note": "", "chain_of_thought": ""}'
        )

    def chat(self, message, history):
        self.memory = history[-10:]
        return self.think(message,
            extra_context="Remember all previous conversation. Use chain-of-thought when building on context.",
            temperature=0.7
        )


class SynthesisAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Synthesis Agent", specialty="Multi-agent result synthesis",
            personality="Balanced, analytical, integrative.",
            output_format="""{
    "consensus_score": 0,
    "final_verdict": "Weak / Developing / Competent / Strong / Masterful",
    "reasoning": "", "strongest_point": "", "key_improvement": ""
}"""
        )

    def synthesize(self, prompt_text, agent_results):
        context = f"Prompt: {prompt_text}\nAgent results:\n{json.dumps(agent_results, indent=2)}"
        return self.think(context, temperature=0.3)


class Orchestrator:
    def __init__(self):
        self.evaluator  = EvaluatorAgent()
        self.security   = SecurityAgent()
        self.difficulty = DifficultyAgent()
        self.mutation   = MutationAgent()
        self.domain     = DomainAgent()
        self.suggestion = SuggestionAgent()
        self.chat       = ChatAgent()
        self.synthesis  = SynthesisAgent()
        self.critic     = DebateAgent("The Critic",    "Extremely strict, finds every flaw")
        self.optimist   = DebateAgent("The Optimist",  "Encouraging, focuses on strengths")
        self.professor  = DebateAgent("The Professor", "Academic NLP expert")

    def run_full_evaluation(self, prompt_text, user_id):
        results = {}
        results["security"]   = self.security.scan(prompt_text)
        results["evaluation"] = self.evaluator.evaluate(prompt_text)
        results["difficulty"] = self.difficulty.classify(prompt_text)
        results["domain"]     = self.domain.evaluate(prompt_text)
        answer_resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Answer clearly and in a well-structured format."},
                {"role": "user",   "content": prompt_text}
            ],
            temperature=0.7
        )
        results["answer"] = answer_resp.choices[0].message.content.strip()
        return results

    def run_debate(self, prompt_text):
        critic_result    = self.critic.debate(prompt_text)
        optimist_result  = self.optimist.debate(prompt_text)
        professor_result = self.professor.debate(prompt_text)
        consensus = self.synthesis.synthesize(prompt_text, {
            "critic": critic_result, "optimist": optimist_result, "professor": professor_result
        })
        return {
            "agents":    {"critic": critic_result, "optimist": optimist_result, "professor": professor_result},
            "consensus": consensus
        }


orchestrator = Orchestrator()


# ================================================================
#  HELPERS
# ================================================================
def calculate_grade(score):
    if score >= 9:   return "A+"
    elif score >= 8: return "A"
    elif score >= 7: return "B"
    elif score >= 6: return "C"
    elif score >= 4: return "D"
    else:            return "F"

def detect_language(text):
    try:
        lang = detect(text)
        m = {"en": "English", "fr": "French", "es": "Spanish", "de": "German",
             "ar": "Arabic",  "ur": "Urdu",   "zh": "Chinese", "hi": "Hindi"}
        return m.get(lang, f"Other ({lang})")
    except:
        return "English"

def update_analytics(user_id, new_score, weakness):
    conn   = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT total_attempts,average_score,best_score,worst_score FROM user_analytics WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        total = row[0] + 1
        avg   = round(((row[1] * row[0]) + new_score) / total, 2)
        cursor.execute("""UPDATE user_analytics
            SET total_attempts=?,average_score=?,best_score=?,worst_score=?,
                most_common_weakness=?,improvement_rate=?,last_updated=?
            WHERE user_id=?""",
            (total, avg, max(row[2], new_score), min(row[3], new_score),
             weakness, round(((new_score - row[1]) / max(row[1], 1)) * 100, 1),
             datetime.now(), user_id))
    else:
        cursor.execute("""INSERT INTO user_analytics
            (user_id,total_attempts,average_score,best_score,worst_score,most_common_weakness,improvement_rate)
            VALUES (?,1,?,?,?,?,0)""", (user_id, new_score, new_score, new_score, weakness))
    conn.commit()
    conn.close()


# ================================================================
#  LAIBA — Evaluation, Chat, Sessions, Analytics
# ================================================================

@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    data        = request.get_json()
    user_id     = data.get("user_id", 1)
    prompt_text = data.get("prompt_text", "").strip()
    if not prompt_text: return jsonify({"error": "No prompt provided"}), 400
    try:
        language   = detect_language(prompt_text)
        word_count = len(prompt_text.split())
        results    = orchestrator.run_full_evaluation(prompt_text, user_id)
        evaluation = results["evaluation"]
        security   = results["security"]
        difficulty = results["difficulty"]
        domain     = results["domain"]
        answer     = results["answer"]
        grade      = calculate_grade(evaluation.get("total_score", 0))

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO prompt_attempts
            (user_id,prompt_text,prompt_type,language,word_count,
             clarity_score,context_score,specificity_score,constraints_score,format_score,
             total_score,grade,confidence,feedback,improved_prompt,explanation,answer,
             difficulty,domain,threat_level)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, prompt_text, evaluation.get("prompt_type", "general"), language, word_count,
             evaluation.get("clarity_score", 0), evaluation.get("context_score", 0),
             evaluation.get("specificity_score", 0), evaluation.get("constraints_score", 0),
             evaluation.get("format_score", 0), evaluation.get("total_score", 0),
             grade, evaluation.get("confidence", "Medium"),
             json.dumps(evaluation.get("feedback", [])),
             evaluation.get("improved_prompt", ""), evaluation.get("explanation", ""),
             answer, difficulty.get("difficulty", "Beginner"),
             domain.get("detected_domain", "General"), security.get("threat_level", "SAFE")))
        cursor.execute("INSERT INTO score_history (user_id,score,grade) VALUES (?,?,?)",
                       (user_id, evaluation.get("total_score", 0), grade))
        cursor.execute("INSERT INTO security_logs (user_id,prompt_text,threat_level,threat_type,explanation) VALUES (?,?,?,?,?)",
            (user_id, prompt_text, security.get("threat_level", "SAFE"),
             security.get("threat_type", "None"), security.get("explanation", "")))
        cursor.execute("INSERT INTO difficulty_logs (user_id,prompt_text,difficulty,current_skills,missing_skills,next_level_tips) VALUES (?,?,?,?,?,?)",
            (user_id, prompt_text, difficulty.get("difficulty", "Beginner"),
             json.dumps(difficulty.get("current_skills", [])),
             json.dumps(difficulty.get("missing_skills", [])),
             json.dumps(difficulty.get("next_level_tips", []))))
        conn.commit()
        conn.close()
        update_analytics(user_id, evaluation.get("total_score", 0), evaluation.get("most_common_weakness", ""))

        return jsonify({
            "success": True, "prompt_text": prompt_text,
            "language": language, "word_count": word_count,
            "prompt_type": evaluation.get("prompt_type", "general"),
            "scores": {
                "clarity": evaluation.get("clarity_score", 0),
                "context": evaluation.get("context_score", 0),
                "specificity": evaluation.get("specificity_score", 0),
                "constraints": evaluation.get("constraints_score", 0),
                "format": evaluation.get("format_score", 0),
                "total": evaluation.get("total_score", 0)
            },
            "grade": grade, "confidence": evaluation.get("confidence", "Medium"),
            "feedback": evaluation.get("feedback", []),
            "improved_prompt": evaluation.get("improved_prompt", ""),
            "explanation": evaluation.get("explanation", ""),
            "answer": answer, "security": security,
            "difficulty": difficulty, "domain": domain
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/suggest", methods=["POST"])
def suggest():
    data        = request.get_json()
    prompt_text = data.get("prompt_text", "").strip()
    if len(prompt_text) < 8:
        return jsonify({"ready_prompts": [], "missing": ""})
    try:
        return jsonify(orchestrator.suggestion.suggest(prompt_text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/multi-agent", methods=["POST"])
def multi_agent():
    data        = request.get_json()
    user_id     = data.get("user_id", 1)
    prompt_text = data.get("prompt_text", "").strip()
    if not prompt_text: return jsonify({"error": "No prompt provided"}), 400
    try:
        result = orchestrator.run_debate(prompt_text)
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO agent_debates
            (user_id,prompt_text,critic_score,critic_feedback,
             optimist_score,optimist_feedback,professor_score,professor_feedback,
             consensus_score,consensus_reasoning,final_verdict)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, prompt_text,
             result["agents"]["critic"].get("score", 0),
             json.dumps(result["agents"]["critic"].get("feedback", [])),
             result["agents"]["optimist"].get("score", 0),
             json.dumps(result["agents"]["optimist"].get("feedback", [])),
             result["agents"]["professor"].get("score", 0),
             json.dumps(result["agents"]["professor"].get("feedback", [])),
             result["consensus"].get("consensus_score", 0),
             result["consensus"].get("reasoning", ""),
             result["consensus"].get("final_verdict", "")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "prompt_text": prompt_text, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/security", methods=["POST"])
def security():
    data        = request.get_json()
    user_id     = data.get("user_id", 1)
    prompt_text = data.get("prompt_text", "").strip()
    if not prompt_text: return jsonify({"error": "No prompt provided"}), 400
    try:
        result = orchestrator.security.scan(prompt_text)
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO security_logs (user_id,prompt_text,threat_level,threat_type,explanation) VALUES (?,?,?,?,?)",
            (user_id, prompt_text, result.get("threat_level", "SAFE"),
             result.get("threat_type", "None"), result.get("explanation", "")))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "prompt_text": prompt_text, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/difficulty", methods=["POST"])
def difficulty():
    data        = request.get_json()
    user_id     = data.get("user_id", 1)
    prompt_text = data.get("prompt_text", "").strip()
    if not prompt_text: return jsonify({"error": "No prompt provided"}), 400
    try:
        result = orchestrator.difficulty.classify(prompt_text)
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO difficulty_logs (user_id,prompt_text,difficulty,current_skills,missing_skills,next_level_tips) VALUES (?,?,?,?,?,?)",
            (user_id, prompt_text, result.get("difficulty", "Beginner"),
             json.dumps(result.get("current_skills", [])),
             json.dumps(result.get("missing_skills", [])),
             json.dumps(result.get("next_level_tips", []))))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "prompt_text": prompt_text, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mutate", methods=["POST"])
def mutate():
    data        = request.get_json()
    user_id     = data.get("user_id", 1)
    prompt_text = data.get("prompt_text", "").strip()
    if not prompt_text: return jsonify({"error": "No prompt provided"}), 400
    try:
        result = orchestrator.mutation.mutate(prompt_text)
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mutation_logs (user_id,original,mutations) VALUES (?,?,?)",
            (user_id, prompt_text, json.dumps(result.get("mutations", []))))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "prompt_text": prompt_text, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/domain", methods=["POST"])
def domain():
    data        = request.get_json()
    prompt_text = data.get("prompt_text", "").strip()
    if not prompt_text: return jsonify({"error": "No prompt provided"}), 400
    try:
        result = orchestrator.domain.evaluate(prompt_text)
        return jsonify({"success": True, "prompt_text": prompt_text, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json()
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message: return jsonify({"error": "No message provided"}), 400
    try:
        orchestrator.chat.memory = history[-10:]
        result = orchestrator.chat.chat(message, history)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/<int:user_id>", methods=["GET"])
def history(user_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""SELECT prompt_text,prompt_type,language,word_count,total_score,grade,
        confidence,feedback,improved_prompt,explanation,answer,difficulty,domain,threat_level,timestamp
        FROM prompt_attempts WHERE user_id=? ORDER BY timestamp DESC""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "prompt": row[0], "prompt_type": row[1], "language": row[2], "word_count": row[3],
        "score": row[4], "grade": row[5], "confidence": row[6],
        "feedback": json.loads(row[7]) if row[7] else [],
        "improved_prompt": row[8], "explanation": row[9], "answer": row[10],
        "difficulty": row[11], "domain": row[12], "threat_level": row[13], "timestamp": row[14]
    } for row in rows])


@app.route("/api/analytics/<int:user_id>", methods=["GET"])
def analytics(user_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT total_attempts,average_score,best_score,worst_score,most_common_weakness,improvement_rate FROM user_analytics WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row: return jsonify({"message": "No analytics yet"})
    return jsonify({
        "total_attempts": row[0], "average_score": row[1], "best_score": row[2],
        "worst_score": row[3], "most_common_weakness": row[4], "improvement_rate": f"{row[5]}%"
    })


@app.route("/api/progress/<int:user_id>", methods=["GET"])
def progress(user_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT score,grade,timestamp FROM score_history WHERE user_id=? ORDER BY timestamp ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows: return jsonify({"message": "No progress yet"})
    scores = [r[0] for r in rows]
    improvement = round(scores[-1] - scores[0], 1)
    return jsonify({
        "user_id": user_id, "total_attempts": len(rows),
        "first_score": scores[0], "latest_score": scores[-1],
        "improvement": f"+{improvement}" if improvement >= 0 else str(improvement),
        "history": [{"attempt_number": i+1, "score": r[0], "grade": r[1], "timestamp": r[2]}
                    for i, r in enumerate(rows)]
    })


@app.route("/api/templates", methods=["GET"])
def templates():
    t      = request.args.get("type", None)
    conn   = sqlite3.connect(DB)
    cursor = conn.cursor()
    if t:
        cursor.execute("SELECT prompt_type,template_text,description,example FROM prompt_templates WHERE prompt_type=?", (t,))
    else:
        cursor.execute("SELECT prompt_type,template_text,description,example FROM prompt_templates")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"type": r[0], "template": r[1], "description": r[2], "example": r[3]} for r in rows])


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id,average_score,best_score,total_attempts FROM user_analytics ORDER BY average_score DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"rank": i+1, "user_id": r[0], "average_score": r[1], "best_score": r[2], "total_attempts": r[3]}
                    for i, r in enumerate(rows)])


@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    conn   = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM prompt_attempts")
    total_users = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM prompt_attempts")
    total_prompts = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(total_score) FROM prompt_attempts")
    avg_score = round(cursor.fetchone()[0] or 0, 1)
    cursor.execute("SELECT COUNT(*) FROM agent_debates")
    total_debates = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM security_logs WHERE threat_level != 'SAFE'")
    threats = cursor.fetchone()[0] or 0
    cursor.execute("SELECT grade, COUNT(*) FROM prompt_attempts GROUP BY grade")
    grade_dist = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.execute("SELECT DATE(timestamp), COUNT(*) FROM prompt_attempts GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7")
    daily = [{"date": r[0], "count": r[1]} for r in cursor.fetchall()]
    conn.close()
    return jsonify({
        "overview": {"total_users": total_users, "total_prompts": total_prompts,
            "average_score": avg_score, "total_debates": total_debates, "threats_caught": threats},
        "grade_distribution": grade_dist, "daily_activity": daily
    })


# Sessions
@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    user_id = request.args.get("user_id", 1)
    conn    = sqlite3.connect(DB)
    cursor  = conn.cursor()
    cursor.execute("SELECT session_id,title,created_at,updated_at FROM chat_sessions WHERE user_id=? ORDER BY updated_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"session_id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows])


@app.route("/api/sessions", methods=["POST"])
def create_session():
    data    = request.get_json()
    user_id = data.get("user_id", 1)
    title   = data.get("title", "New Chat")
    conn    = sqlite3.connect(DB)
    cursor  = conn.cursor()
    cursor.execute("INSERT INTO chat_sessions (user_id,title) VALUES (?,?)", (user_id, title))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"session_id": session_id, "title": title})


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    conn   = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE session_id=?", (session_id,))
    cursor.execute("DELETE FROM chat_sessions WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/sessions/<int:session_id>/messages", methods=["GET"])
def get_messages(session_id):
    conn   = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT role,content,eval_data,created_at FROM chat_messages WHERE session_id=? ORDER BY created_at ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "role": r[0], "content": r[1],
        "eval_data": json.loads(r[2]) if r[2] else None,
        "created_at": r[3]
    } for r in rows])


@app.route("/api/sessions/<int:session_id>/messages", methods=["POST"])
def save_message(session_id):
    data      = request.get_json()
    role      = data.get("role", "user")
    content   = data.get("content", "")
    eval_data = data.get("eval_data", None)
    conn      = sqlite3.connect(DB)
    cursor    = conn.cursor()
    cursor.execute("INSERT INTO chat_messages (session_id,role,content,eval_data) VALUES (?,?,?,?)",
        (session_id, role, content, json.dumps(eval_data) if eval_data else None))
    cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id=?", (session_id,))
    count = cursor.fetchone()[0]
    if count == 1 and role == "user":
        title = content[:40] + "..." if len(content) > 40 else content
        cursor.execute("UPDATE chat_sessions SET title=?,updated_at=? WHERE session_id=?",
                       (title, datetime.now(), session_id))
    else:
        cursor.execute("UPDATE chat_sessions SET updated_at=? WHERE session_id=?",
                       (datetime.now(), session_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ================================================================
#  AREEBA / FATIMA / RABIA — consolidated frontend contract
# ================================================================

def _get_user_column(conn: sqlite3.Connection, table: str, column: str):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")].__contains__(column)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hashed = stored_hash.split("$", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
        return hmac.compare_digest(check, hashed)
    except Exception:
        return False


def validate_password(password: str) -> str | None:
    if len(password) < 6:
        return "Password must be at least 6 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must include at least one symbol"
    return None


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def make_user(row: sqlite3.Row | dict) -> dict:
    if isinstance(row, dict):
        user = row
    else:
        user = dict(row)
    return {
        "id": user.get("id"),
        "name": user.get("username") or user.get("name"),
        "username": user.get("username") or user.get("name"),
        "email": user.get("email"),
        "created_at": user.get("created_at"),
        "last_activity": user.get("last_activity") or user.get("created_at"),
    }


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        conn = get_db()
        user = conn.execute(
            """
            SELECT u.* FROM users u
            JOIN user_sessions s ON s.user_id = u.id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        conn.close()
        if not user:
            return jsonify({"error": "Invalid token"}), 401
        request.current_user = dict(user)
        return fn(*args, **kwargs)

    return wrapper


def update_activity(user_id: int, activity_type: str, detail: str):
    conn = get_db()
    conn.execute("UPDATE users SET last_activity=? WHERE id=?", (now(), user_id))
    conn.execute(
        "INSERT INTO activity_logs (user_id, activity_type, detail, created_at) VALUES (?, ?, ?, ?)",
        (user_id, activity_type, detail, now()),
    )
    conn.commit()
    conn.close()


def _update_streak(user_id: int, conn: sqlite3.Connection):
    row = conn.execute("SELECT * FROM user_streaks WHERE user_id=?", (user_id,)).fetchone()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if row:
        conn.execute(
            "UPDATE user_streaks SET current_streak=?, longest_streak=?, last_activity_date=?, updated_at=? WHERE user_id=?",
            (row["current_streak"], row["longest_streak"], today, now(), user_id),
        )
    else:
        conn.execute(
            "INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date, updated_at) VALUES (?, 1, 1, ?, ?)",
            (user_id, today, now()),
        )


def _seed_chapters_and_questions(conn: sqlite3.Connection):
    chapter_rows = conn.execute("SELECT COUNT(*) AS c FROM chapters").fetchone()[0]
    if chapter_rows == 0:
        chapters = [
            ("chapter-1", "Role & Context", "Learn how to define the role, audience, and task clearly.", "15 min", 4, "# Chapter 1\n\n- Define a clear role\n- Set the audience\n- State the desired output format", "https://youtu.be/dQw4w9WgXcQ"),
            ("chapter-2", "Clarity & Constraints", "Make your instructions specific and constrained for better output.", "10 min", 3, "# Chapter 2\n\n- Add constraints\n- Remove ambiguity\n- Specify boundaries", None),
            ("chapter-3", "Examples & Few-shot", "Use examples to teach the model the pattern you want.", "12 min", 3, "# Chapter 3\n\n- Include one good example\n- Show the expected structure\n- Keep examples short", None),
            ("chapter-4", "Structure & Formatting", "Guide the model into structured, machine-readable outputs.", "14 min", 4, "# Chapter 4\n\n- Use bullets or JSON\n- Define length and sections\n- Ask for a summary", None),
            ("chapter-5", "Refinement & Iteration", "Improve prompts by iterating on weak areas and feedback.", "16 min", 3, "# Chapter 5\n\n- Review answers\n- Detect gaps\n- Refine prompts", None),
            ("chapter-6", "Security & Reliability", "Protect your prompts from injection and unreliable output.", "13 min", 3, "# Chapter 6\n\n- Avoid unsafe instructions\n- Add guardrails\n- Verify output", None),
        ]
        for chapter_id, title, description, duration, lessons, content, video_url in chapters:
            conn.execute(
                "INSERT INTO chapters (id, title, description, duration, lessons, content, video_url, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (chapter_id, title, description, duration, lessons, content, video_url, len(chapters)),
            )

    question_rows = conn.execute("SELECT COUNT(*) AS c FROM practice_questions").fetchone()[0]
    if question_rows == 0:
        questions = [
            ("chapter-1", "Write a concise onboarding email", "Write a short welcome email for a new customer who just signed up.", "Write a clear, engaging, and professional welcome email.", "[]", "[]", "beginner"),
            ("chapter-2", "Describe a product update", "Summarize a new feature update for non-technical users.", "Explain the update in 3 bullet points with clear constraints.", "[]", "[]", "intermediate"),
            ("chapter-3", "Generate a structured report", "Create a short report about team performance.", "Return the answer as JSON with title, summary, and next steps.", "[]", "[]", "intermediate"),
            ("chapter-4", "Refine a vague prompt", "Improve a vague prompt for an AI assistant.", "Show how you would make it precise, specific, and useful.", "[]", "[]", "intermediate"),
            ("chapter-5", "Create a lesson plan", "Design a lesson plan for beginners.", "Include goals, activities, and a short assessment.", "[]", "[]", "advanced"),
            ("chapter-6", "Handle a data request safely", "Explain how to safely collect user data.", "Produce a safe, privacy-conscious answer with guardrails.", "[]", "[]", "advanced"),
        ]
        for chapter_id, title, scenario, statement, hints, expected_elements, difficulty in questions:
            conn.execute(
                "INSERT INTO practice_questions (chapter_id, title, scenario, statement, hints, expected_elements, difficulty, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                (chapter_id, title, scenario, statement, hints, expected_elements, difficulty),
            )

    conn.commit()


def evaluate_prompt(prompt_text: str, question: sqlite3.Row | dict):
    prompt_text = (prompt_text or "").strip()
    words = max(1, len(prompt_text.split()))
    clarity = min(100, 55 + min(30, words // 8))
    structure = min(100, 50 + (1 if prompt_text.count("\n") else 0) * 15 + (1 if "{" in prompt_text or "[" in prompt_text else 0) * 10)
    specificity = min(100, 45 + min(25, words // 6))
    score = round((clarity + structure + specificity) / 3)
    strengths = []
    if len(prompt_text) >= 20:
        strengths.append("The prompt includes enough detail to be actionable")
    if any(token in prompt_text.lower() for token in ["for", "with", "format", "audience"]):
        strengths.append("The prompt gives concrete context")
    weaknesses = []
    if len(prompt_text.split()) < 8:
        weaknesses.append("The prompt could be more specific")
    if not any(token in prompt_text.lower() for token in ["format", "audience", "role", "goal"]):
        weaknesses.append("The prompt could define the output format or audience")
    suggestions = ["Add a clearer role or audience", "Specify output formatting", "Include constraints or examples"]
    detailed_feedback = (
        f"Your prompt is generally clear, but it could be improved by defining the expected structure and audience. "
        f"Try to include the task, the audience, and the desired format in one concise instruction."
    )
    prompt_quality_analysis = "The prompt is understandable but still medium quality; it needs more context and structure."
    improvement_recommendations = ["State the role", "Specify audience", "Add constraints"]
    return {
        "score": score,
        "clarity": clarity,
        "structure": structure,
        "specificity": specificity,
        "strengths": strengths or ["The prompt is readable"],
        "weaknesses": weaknesses or ["The prompt could be more detailed"],
        "suggestions": suggestions,
        "detailed_feedback": detailed_feedback,
        "prompt_quality_analysis": prompt_quality_analysis,
        "improvement_recommendations": improvement_recommendations,
        "passed": score >= 70,
    }


def build_enhanced_prompt(prompt_text: str, iteration: int = 1) -> str:
    base = (prompt_text or "").strip()
    if not base:
        return "Write a clear, specific prompt with role, context, constraints, and format."
    iteration = max(1, min(iteration, 3))
    templates = [
        f"You are an expert assistant. Improve this prompt by making it more specific and actionable: {base}",
        f"Refine this prompt with a clear role, audience, and desired output format: {base}",
        f"Rewrite this prompt to be concise, structured, and easy for an AI to follow: {base}",
    ]
    return templates[iteration - 1]


def serialize_question(row: sqlite3.Row | dict):
    if isinstance(row, dict):
        row = row
    else:
        row = dict(row)
    return {
        "id": row.get("id"),
        "chapter_id": row.get("chapter_id"),
        "title": row.get("title"),
        "scenario": row.get("scenario") or row.get("statement"),
        "statement": row.get("statement") or row.get("scenario"),
        "hints": json.loads(row.get("hints") or "[]") if row.get("hints") else [],
        "expected_elements": json.loads(row.get("expected_elements") or "[]") if row.get("expected_elements") else [],
        "difficulty": row.get("difficulty"),
    }


def serialize_chapter(chapter_row: sqlite3.Row | dict, progress_row: sqlite3.Row | None = None, question_count: int = 0):
    if isinstance(chapter_row, dict):
        row = chapter_row
    else:
        row = dict(chapter_row)
    progress = dict(progress_row) if progress_row else {}
    completed = bool(progress.get("completed") or 0)
    completed_questions = int(progress.get("completed_questions") or 0)
    best_score = int(progress.get("best_score") or 0)
    average_score = round(float(progress.get("average_score") or 0), 1)
    attempt_count = int(progress.get("attempt_count") or 0)
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "description": row.get("description"),
        "duration": row.get("duration"),
        "lessons": int(row.get("lessons") or 0),
        "content": row.get("content"),
        "videoUrl": row.get("video_url"),
        "progress": int(progress.get("progress") or 0),
        "completed": completed,
        "completed_questions": completed_questions,
        "total_questions": int(question_count or row.get("total_questions") or 0),
        "best_score": best_score,
        "average_score": average_score,
        "attempt_count": attempt_count,
    }


def refresh_chapter_progress(conn: sqlite3.Connection, user_id: int, chapter_id: str):
    total_questions = conn.execute("SELECT COUNT(*) AS c FROM practice_questions WHERE chapter_id=? AND is_active=1", (chapter_id,)).fetchone()[0] or 0
    attempts = conn.execute(
        "SELECT score FROM practice_attempts WHERE user_id=? AND chapter_id=? ORDER BY created_at ASC",
        (user_id, chapter_id),
    ).fetchall()
    completed_questions = max(0, len(attempts))
    completed = total_questions > 0 and completed_questions >= total_questions
    progress = round((completed_questions / total_questions) * 100) if total_questions else 100 if completed else 0
    best_score = max((row[0] for row in attempts), default=0) if attempts else 0
    average_score = round(sum(row[0] for row in attempts) / len(attempts), 1) if attempts else 0
    existing = conn.execute("SELECT id FROM chapter_progress WHERE user_id=? AND chapter_id=?", (user_id, chapter_id)).fetchone()
    if existing:
        conn.execute(
            "UPDATE chapter_progress SET completed=?, progress=?, best_score=?, average_score=?, completed_questions=?, attempt_count=?, updated_at=? WHERE user_id=? AND chapter_id=?",
            (1 if completed else 0, progress, best_score, average_score, completed_questions, len(attempts), now(), user_id, chapter_id),
        )
    else:
        conn.execute(
            "INSERT INTO chapter_progress (user_id, chapter_id, completed, progress, best_score, average_score, completed_questions, attempt_count, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, chapter_id, 1 if completed else 0, progress, best_score, average_score, completed_questions, len(attempts), now()),
        )
    conn.commit()
    return {
        "chapter_id": chapter_id,
        "completed": completed,
        "progress": progress,
        "best_score": best_score,
        "average_score": average_score,
        "completed_questions": completed_questions,
        "attempt_count": len(attempts),
    }


def get_or_create_session(conn: sqlite3.Connection, user_id: int, chapter_id: str, question_id: int | None = None):
    chapter = conn.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if not chapter:
        return None
    if question_id is None:
        question = conn.execute(
            "SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1 ORDER BY id ASC LIMIT 1",
            (chapter_id,),
        ).fetchone()
    else:
        question = conn.execute(
            "SELECT * FROM practice_questions WHERE id=? AND chapter_id=? AND is_active=1",
            (question_id, chapter_id),
        ).fetchone()
    if not question:
        return None
    title = f"{chapter['title']} - {question['title']}"
    cur = conn.execute(
        "INSERT INTO practice_sessions (user_id, chapter_id, question_id, session_title, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'active', ?, ?)",
        (user_id, chapter_id, question['id'], title, now(), now()),
    )
    conn.commit()
    return conn.execute("SELECT * FROM practice_sessions WHERE id=?", (cur.lastrowid,)).fetchone()


def serialize_session(conn: sqlite3.Connection, row: sqlite3.Row | dict, include_details: bool = True):
    if isinstance(row, dict):
        session_row = row
    else:
        session_row = dict(row)
    question = conn.execute("SELECT * FROM practice_questions WHERE id=?", (session_row.get("question_id"),)).fetchone()
    attempts = conn.execute(
        "SELECT * FROM practice_attempts WHERE session_id=? ORDER BY created_at ASC",
        (session_row.get("id"),),
    ).fetchall()
    messages = conn.execute(
        "SELECT * FROM practice_messages WHERE session_id=? ORDER BY created_at ASC",
        (session_row.get("id"),),
    ).fetchall()
    latest_attempt = attempts[-1] if attempts else None
    result = {
        "id": session_row.get("id"),
        "chapter_id": session_row.get("chapter_id"),
        "chapter_title": session_row.get("session_title"),
        "question_id": session_row.get("question_id"),
        "question": serialize_question(question) if question else None,
        "status": session_row.get("status"),
        "session_title": session_row.get("session_title"),
        "latest_score": latest_attempt["score"] if latest_attempt else None,
        "messages": [
            {"id": m["id"], "role": m["role"], "content": m["content"], "created_at": m["created_at"]}
            for m in messages
        ],
        "attempts": [
            {
                "id": a["id"],
                "attempt_number": a["attempt_number"],
                "prompt_text": a["prompt_text"],
                "score": a["score"],
                "clarity": a["clarity"],
                "structure": a["structure"],
                "specificity": a["specificity"],
                "strengths": json.loads(a["strengths"]) if a["strengths"] else [],
                "weaknesses": json.loads(a["weaknesses"]) if a["weaknesses"] else [],
                "suggestions": json.loads(a["suggestions"]) if a["suggestions"] else [],
                "detailed_feedback": a["detailed_feedback"],
                "prompt_quality_analysis": a["prompt_quality_analysis"],
                "improvement_recommendations": json.loads(a["improvement_recommendations"]) if a["improvement_recommendations"] else [],
                "created_at": a["created_at"],
            }
            for a in attempts
        ],
        "created_at": session_row.get("created_at"),
        "updated_at": session_row.get("updated_at"),
    }
    if not include_details:
        result.pop("messages", None)
        result.pop("attempts", None)
    return result


def _serialize_enhancement_session(conn: sqlite3.Connection, session_id: int, user_id: int):
    session_row = conn.execute("SELECT * FROM enhancement_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone()
    if not session_row:
        return None
    messages = conn.execute(
        "SELECT * FROM enhancement_messages WHERE session_id=? AND user_id=? ORDER BY created_at ASC",
        (session_id, user_id),
    ).fetchall()
    versions = conn.execute(
        "SELECT * FROM enhancement_versions WHERE session_id=? AND user_id=? ORDER BY version_number ASC",
        (session_id, user_id),
    ).fetchall()
    latest_version = versions[-1] if versions else None
    return {
        "id": session_row["id"],
        "title": session_row["title"],
        "original_prompt": session_row["original_prompt"],
        "status": session_row["status"],
        "created_at": session_row["created_at"],
        "updated_at": session_row["updated_at"],
        "messages": [
            {"id": m["id"], "role": m["role"], "content": m["content"], "iteration": m["iteration"], "created_at": m["created_at"]}
            for m in messages
        ],
        "versions": [
            {"id": v["id"], "version_number": v["version_number"], "enhanced_prompt": v["enhanced_prompt"], "overall_score": v["overall_score"], "created_at": v["created_at"]}
            for v in versions
        ],
        "latest_version": {
            "id": latest_version["id"],
            "version_number": latest_version["version_number"],
            "enhanced_prompt": latest_version["enhanced_prompt"],
            "overall_score": latest_version["overall_score"],
            "created_at": latest_version["created_at"],
        } if latest_version else None,
    }


@app.route("/api/areeba/register", methods=["POST"])
def areeba_register():
    data = request.get_json() or {}
    username = (data.get("username") or data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not username or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    pw_error = validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    conn = get_db()
    if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        conn.close()
        return jsonify({"error": "Email already exists"}), 409

    otp = f"{random.randint(100000, 999999)}"
    conn.execute(
        "INSERT INTO pending_registrations (username, email, password_hash, verification_code, expires_at, last_sent_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, email, hash_password(password), otp, (datetime.utcnow() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"), now()),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Verification code sent", "email": email, "expires_in": 600, "resend_after": 45}), 202


@app.route("/api/areeba/verify-registration", methods=["POST"])
def areeba_verify_registration():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    conn = get_db()
    pending = conn.execute("SELECT * FROM pending_registrations WHERE email=?", (email,)).fetchone()
    if not pending:
        conn.close()
        return jsonify({"error": "Verification request not found"}), 404
    if not hmac.compare_digest(code, pending["verification_code"]):
        conn.close()
        return jsonify({"error": "Invalid code"}), 400
    cur = conn.execute(
        "INSERT INTO users (username, email, password_hash, created_at, last_activity) VALUES (?, ?, ?, ?, ?)",
        (pending["username"], pending["email"], pending["password_hash"], now(), now()),
    )
    user_id = cur.lastrowid
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO user_sessions (user_id, token, created_at) VALUES (?, ?, ?)", (user_id, token, now()))
    conn.execute("DELETE FROM pending_registrations WHERE email=?", (email,))
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return jsonify({"message": "Email verified and account created", "token": token, "user": make_user(user)}), 201


@app.route("/api/areeba/resend-registration-code", methods=["POST"])
def areeba_resend_registration_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    conn = get_db()
    pending = conn.execute("SELECT * FROM pending_registrations WHERE email=?", (email,)).fetchone()
    if not pending:
        conn.close()
        return jsonify({"error": "Verification request not found"}), 404
    otp = f"{random.randint(100000, 999999)}"
    conn.execute(
        "UPDATE pending_registrations SET verification_code=?, last_sent_at=? WHERE email=?",
        (otp, now(), email),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "A new verification code was sent.", "resend_after": 45})


@app.route("/api/areeba/login", methods=["POST"])
def areeba_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not verify_password(password, user.get("password_hash") or user.get("password") or ""):
        conn.close()
        return jsonify({"error": "Invalid email or password"}), 401
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO user_sessions (user_id, token, created_at) VALUES (?, ?, ?)", (user["id"], token, now()))
    conn.execute("UPDATE users SET last_activity=? WHERE id=?", (now(), user["id"]))
    conn.execute("INSERT INTO activity_logs (user_id, activity_type, detail, created_at) VALUES (?, ?, ?, ?)", (user["id"], "login", "User logged in", now()))
    conn.commit()
    conn.close()
    return jsonify({"message": "Login successful", "token": token, "user": make_user(user)})


@app.route("/api/areeba/me", methods=["GET"])
@require_auth
def areeba_me():
    update_activity(request.current_user["id"], "active", "Checked session")
    return jsonify({"user": make_user(request.current_user)})


@app.route("/api/areeba/logout", methods=["POST"])
@require_auth
def areeba_logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    conn = get_db()
    conn.execute("DELETE FROM user_sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Logged out"})


@app.route("/api/areeba/forgot-password", methods=["POST"])
def areeba_forgot_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"message": "If that email is registered, a reset code has been sent."}), 200
    otp = f"{random.randint(100000, 999999)}"
    conn.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (user["id"],))
    conn.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
        (user["id"], otp, (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"), now()),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "If that email is registered, a reset code has been sent."}), 200


@app.route("/api/areeba/reset-password", methods=["POST"])
def areeba_reset_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    new_password = data.get("new_password") or ""
    if not email or not otp or not new_password:
        return jsonify({"error": "Email, OTP, and new password are required"}), 400
    pw_error = validate_password(new_password)
    if pw_error:
        return jsonify({"error": pw_error}), 400
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "Invalid or expired reset code"}), 400
    token_row = conn.execute(
        "SELECT * FROM password_reset_tokens WHERE user_id=? AND token=? AND used=0 AND datetime(expires_at) > datetime('now') ORDER BY created_at DESC LIMIT 1",
        (user["id"], otp),
    ).fetchone()
    if not token_row:
        conn.close()
        return jsonify({"error": "Invalid or expired reset code"}), 400
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_password), user["id"]))
    conn.execute("UPDATE password_reset_tokens SET used=1 WHERE user_id=? AND token=?", (user["id"], otp))
    conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user["id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Password reset successfully."}), 200


@app.route("/api/areeba/prompt-history", methods=["POST"])
@require_auth
def areeba_prompt_history():
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        "INSERT INTO prompt_history (user_id, module_type, original_prompt, ai_response, improved_prompt, explanation, resources, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (request.current_user["id"], data.get("module_type") or "direct_prompt", data.get("original_prompt") or "", data.get("ai_response"), data.get("improved_prompt"), data.get("explanation"), data.get("resources"), now()),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Prompt history saved"}), 201


@app.route("/api/areeba/chat-history", methods=["POST"])
@require_auth
def areeba_chat_history():
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (user_id, user_message, bot_response, created_at) VALUES (?, ?, ?, ?)",
        (request.current_user["id"], data.get("user_message") or "", data.get("bot_response"), now()),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Chat history saved"}), 201


@app.route("/api/areeba/history", methods=["GET"])
@require_auth
def areeba_history():
    conn = get_db()
    prompts = conn.execute("SELECT * FROM prompt_history WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (request.current_user["id"],)).fetchall()
    chats = conn.execute("SELECT * FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (request.current_user["id"],)).fetchall()
    conn.close()
    return jsonify({"prompts": [dict(p) for p in prompts], "chats": [dict(c) for c in chats]})


@app.route("/api/areeba/dashboard/me", methods=["GET"])
@require_auth
def areeba_dashboard_me():
    return areeba_dashboard(request.current_user["id"])


@app.route("/api/areeba/dashboard/<int:user_id>", methods=["GET"])
def areeba_dashboard(user_id: int):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    prompt_total = conn.execute("SELECT COUNT(*) AS c FROM prompt_history WHERE user_id=?", (user_id,)).fetchone()[0] or 0
    chat_total = conn.execute("SELECT COUNT(*) AS c FROM chat_history WHERE user_id=?", (user_id,)).fetchone()[0] or 0
    recent_activity = conn.execute("SELECT activity_type, detail, created_at FROM activity_logs WHERE user_id=? ORDER BY created_at DESC LIMIT 8", (user_id,)).fetchall()
    streak = conn.execute("SELECT * FROM user_streaks WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return jsonify({
        "user": make_user(user),
        "stats": {
            "total_prompts": prompt_total,
            "total_chats": chat_total,
            "learning_count": 0,
            "direct_prompt_count": 0,
            "total_activity": prompt_total + chat_total,
            "last_activity": user["last_activity"],
        },
        "recent_activity": [dict(a) for a in recent_activity],
        "streak": {
            "current_streak": streak["current_streak"] if streak else 0,
            "longest_streak": streak["longest_streak"] if streak else 0,
            "last_activity_date": streak["last_activity_date"] if streak else None,
            "updated_at": streak["updated_at"] if streak else None,
        },
    })


@app.route("/api/areeba/users", methods=["GET"])
def areeba_users():
    conn = get_db()
    users = conn.execute("SELECT id, username, email, created_at, last_activity FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([{
        "id": u["id"],
        "username": u["username"],
        "email": u["email"],
        "created_at": u["created_at"],
        "last_activity": u["last_activity"],
    } for u in users])


@app.route("/api/areeba/streak/me", methods=["GET"])
@require_auth
def areeba_streak_me():
    conn = get_db()
    streak = conn.execute("SELECT * FROM user_streaks WHERE user_id=?", (request.current_user["id"],)).fetchone()
    conn.close()
    return jsonify({
        "current_streak": streak["current_streak"] if streak else 0,
        "longest_streak": streak["longest_streak"] if streak else 0,
        "last_activity_date": streak["last_activity_date"] if streak else None,
        "updated_at": streak["updated_at"] if streak else None,
    })


@app.route("/api/fatima/chapters", methods=["GET"])
@require_auth
def fatima_chapters():
    conn = get_db()
    rows = conn.execute("SELECT * FROM chapters ORDER BY sort_order ASC, id ASC").fetchall()
    progress_rows = conn.execute("SELECT * FROM chapter_progress WHERE user_id=?", (request.current_user["id"],)).fetchall()
    progress_map = {r["chapter_id"]: r for r in progress_rows}
    result = []
    for chapter in rows:
        chapter_id = chapter["id"]
        question_count = conn.execute("SELECT COUNT(*) AS c FROM practice_questions WHERE chapter_id=? AND is_active=1", (chapter_id,)).fetchone()[0] or 0
        result.append(serialize_chapter(chapter, progress_map.get(chapter_id), question_count))
    conn.close()
    return jsonify({"chapters": result})


@app.route("/api/fatima/chapters/<chapter_id>", methods=["GET"])
@require_auth
def fatima_chapter_detail(chapter_id: str):
    conn = get_db()
    chapter = conn.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if not chapter:
        conn.close()
        return jsonify({"error": "Chapter not found"}), 404
    progress = conn.execute("SELECT * FROM chapter_progress WHERE user_id=? AND chapter_id=?", (request.current_user["id"], chapter_id)).fetchone()
    questions = conn.execute("SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1 ORDER BY id ASC", (chapter_id,)).fetchall()
    conn.close()
    return jsonify({"chapter": serialize_chapter(chapter, progress, len(questions)), "questions": [serialize_question(q) for q in questions]})


@app.route("/api/fatima/practice/start", methods=["POST"])
@require_auth
def fatima_practice_start():
    data = request.get_json() or {}
    chapter_id = str(data.get("chapter_id") or "chapter-1").strip()
    conn = get_db()
    chapter = conn.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if not chapter:
        conn.close()
        return jsonify({"error": "Chapter not found"}), 404

    attempted_ids = {r["question_id"] for r in conn.execute("SELECT DISTINCT question_id FROM practice_attempts WHERE user_id=? AND chapter_id=?", (request.current_user["id"], chapter_id)).fetchall()}
    candidate = conn.execute(
        "SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1 AND id NOT IN (SELECT question_id FROM practice_attempts WHERE user_id=? AND chapter_id=?) ORDER BY id ASC LIMIT 1",
        (chapter_id, request.current_user["id"], chapter_id),
    ).fetchone()
    if not candidate:
        conn.close()
        return jsonify({"all_completed": True, "message": "You have attempted all practice questions for this chapter."}), 200

    session_row = get_or_create_session(conn, request.current_user["id"], chapter_id, candidate["id"])
    session = serialize_session(conn, session_row, include_details=True)
    conn.close()
    return jsonify({"session": session}), 201


@app.route("/api/fatima/practice/<int:session_id>/submit", methods=["POST"])
@require_auth
def fatima_practice_submit(session_id: int):
    data = request.get_json() or {}
    prompt_text = (data.get("prompt_text") or "").strip()
    if not prompt_text:
        return jsonify({"error": "Prompt text is required"}), 400
    conn = get_db()
    session = conn.execute("SELECT * FROM practice_sessions WHERE id=? AND user_id=?", (session_id, request.current_user["id"])).fetchone()
    if not session:
        conn.close()
        return jsonify({"error": "Practice session not found"}), 404
    question = conn.execute("SELECT * FROM practice_questions WHERE id=?", (session["question_id"],)).fetchone()
    evaluation = evaluate_prompt(prompt_text, question)
    latest_attempt = conn.execute("SELECT COALESCE(MAX(attempt_number), 0) AS n FROM practice_attempts WHERE session_id=?", (session_id,)).fetchone()[0] or 0
    conn.execute(
        "INSERT INTO practice_attempts (session_id, user_id, chapter_id, question_id, attempt_number, prompt_text, score, clarity, structure, specificity, strengths, weaknesses, suggestions, detailed_feedback, prompt_quality_analysis, improvement_recommendations, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, request.current_user["id"], session["chapter_id"], session["question_id"], int(latest_attempt) + 1, prompt_text, evaluation["score"], evaluation["clarity"], evaluation["structure"], evaluation["specificity"], json.dumps(evaluation["strengths"]), json.dumps(evaluation["weaknesses"]), json.dumps(evaluation["suggestions"]), evaluation["detailed_feedback"], evaluation["prompt_quality_analysis"], json.dumps(evaluation["improvement_recommendations"]), now()),
    )
    conn.execute("INSERT INTO practice_messages (session_id, user_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)", (session_id, request.current_user["id"], prompt_text, now()))
    conn.execute("INSERT INTO practice_messages (session_id, user_id, role, content, created_at) VALUES (?, ?, 'assistant', ?, ?)", (session_id, request.current_user["id"], evaluation["detailed_feedback"], now()))
    conn.execute("UPDATE practice_sessions SET status='completed' WHERE id=?", (session_id,))
    conn.commit()
    progress = refresh_chapter_progress(conn, request.current_user["id"], session["chapter_id"])
    session_row = conn.execute("SELECT * FROM practice_sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return jsonify({"evaluation": evaluation, "attempt": {"id": session_id, "attempt_number": int(latest_attempt) + 1, **evaluation}, "session": serialize_session(get_db(), session_row, include_details=True), "progress": progress})


@app.route("/api/fatima/practice/<int:session_id>/change-question", methods=["POST"])
@require_auth
def fatima_change_question(session_id: int):
    conn = get_db()
    session = conn.execute("SELECT * FROM practice_sessions WHERE id=? AND user_id=?", (session_id, request.current_user["id"])).fetchone()
    if not session:
        conn.close()
        return jsonify({"error": "Practice session not found"}), 404
    chapter_id = session["chapter_id"]
    candidate = conn.execute(
        "SELECT * FROM practice_questions WHERE chapter_id=? AND is_active=1 AND id NOT IN (SELECT question_id FROM practice_attempts WHERE user_id=? AND chapter_id=?) ORDER BY id ASC LIMIT 1",
        (chapter_id, request.current_user["id"], chapter_id),
    ).fetchone()
    if not candidate:
        conn.close()
        return jsonify({"all_completed": True, "message": "You have attempted all practice questions for this chapter."}), 200
    conn.execute("UPDATE practice_sessions SET status='saved', updated_at=? WHERE id=?", (now(), session_id))
    new_session = get_or_create_session(conn, request.current_user["id"], chapter_id, candidate["id"])
    session_payload = serialize_session(conn, new_session, include_details=True)
    conn.close()
    return jsonify({"session": session_payload}), 201


@app.route("/api/fatima/practice/sessions", methods=["GET"])
@require_auth
def fatima_practice_sessions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM practice_sessions WHERE user_id=? ORDER BY updated_at DESC", (request.current_user["id"],)).fetchall()
    conn.close()
    return jsonify({"sessions": [serialize_session(get_db(), r, include_details=False) for r in rows]})


@app.route("/api/fatima/practice/sessions/<int:session_id>", methods=["GET"])
@require_auth
def fatima_practice_session_detail(session_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM practice_sessions WHERE id=? AND user_id=?", (session_id, request.current_user["id"])).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Practice session not found"}), 404
    conn.close()
    return jsonify({"session": serialize_session(get_db(), row, include_details=True)})


@app.route("/api/fatima/progress/me", methods=["GET"])
@require_auth
def fatima_progress_me():
    conn = get_db()
    chapter_ids = [r["id"] for r in conn.execute("SELECT id FROM chapters ORDER BY sort_order ASC").fetchall()]
    progress = [refresh_chapter_progress(conn, request.current_user["id"], chapter_id) for chapter_id in chapter_ids]
    conn.close()
    return jsonify({"progress": progress})


@app.route("/api/fatima/dashboard/me", methods=["GET"])
@require_auth
def fatima_dashboard_me():
    conn = get_db()
    chapter_ids = [r["id"] for r in conn.execute("SELECT id FROM chapters ORDER BY sort_order ASC").fetchall()]
    for chapter_id in chapter_ids:
        refresh_chapter_progress(conn, request.current_user["id"], chapter_id)
    total_chapters = len(chapter_ids)
    completed_chapters = conn.execute("SELECT COUNT(*) AS c FROM chapter_progress WHERE user_id=? AND completed=1", (request.current_user["id"],)).fetchone()[0] or 0
    attempts = conn.execute("SELECT COUNT(*) AS c, COALESCE(AVG(score), 0) AS avg_score, COALESCE(MAX(score), 0) AS best_score FROM practice_attempts WHERE user_id=?", (request.current_user["id"],)).fetchone()
    sessions = conn.execute("SELECT COUNT(DISTINCT session_id) AS c FROM practice_attempts WHERE user_id=?", (request.current_user["id"],)).fetchone()[0] or 0
    messages = conn.execute("SELECT COUNT(*) AS c FROM practice_messages WHERE user_id=?", (request.current_user["id"],)).fetchone()[0] or 0
    recent_sessions = conn.execute("SELECT * FROM practice_sessions WHERE user_id=? ORDER BY updated_at DESC LIMIT 5", (request.current_user["id"],)).fetchall()
    conn.close()
    return jsonify({
        "stats": {
            "total_chapters": total_chapters,
            "chapters_completed": completed_chapters,
            "chapters_remaining": max(total_chapters - completed_chapters, 0),
            "completion_percentage": round((completed_chapters / total_chapters) * 100) if total_chapters else 0,
            "practice_sessions": sessions,
            "practice_submissions": int(attempts[0]),
            "average_score": round(float(attempts[1]), 1),
            "best_score": int(attempts[2]),
            "chat_messages": messages,
            "passing_score": 70,
        },
        "recent_sessions": [serialize_session(get_db(), row, include_details=False) for row in recent_sessions],
    })


@app.route("/api/fatima/practice-feedback", methods=["POST"])
def fatima_practice_feedback_legacy():
    data = request.get_json() or {}
    prompt_text = data.get("prompt_text") or ""
    chapter_id = data.get("chapter_id") or "chapter-1"
    evaluation = evaluate_prompt(prompt_text, {"id": 1})
    conn = get_db()
    conn.execute("INSERT INTO practice_attempts (user_id, chapter_id, prompt_text, score, clarity, structure, specificity, strengths, weaknesses, suggestions, detailed_feedback, prompt_quality_analysis, improvement_recommendations, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (data.get("user_id", 1), chapter_id, prompt_text, evaluation["score"], evaluation["clarity"], evaluation["structure"], evaluation["specificity"], json.dumps(evaluation["strengths"]), json.dumps(evaluation["weaknesses"]), json.dumps(evaluation["suggestions"]), evaluation["detailed_feedback"], evaluation["prompt_quality_analysis"], json.dumps(evaluation["improvement_recommendations"]), now()))
    conn.commit()
    conn.close()
    return jsonify(evaluation)


@app.route("/api/fatima/update-progress", methods=["POST"])
def fatima_update_progress_legacy():
    data = request.get_json() or {}
    chapter_id = str(data.get("chapter_id") or "chapter-1")
    user_id = int(data.get("user_id") or 1)
    conn = get_db()
    progress = refresh_chapter_progress(conn, user_id, chapter_id)
    conn.commit()
    conn.close()
    return jsonify({"message": "Progress refreshed", "progress": progress})


@app.route("/api/fatima/progress/<int:user_id>", methods=["GET"])
def fatima_progress_legacy(user_id: int):
    conn = get_db()
    rows = conn.execute("SELECT * FROM chapter_progress WHERE user_id=? ORDER BY chapter_id ASC", (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/fatima/final-test/status", methods=["GET"])
@require_auth
def fatima_final_test_status():
    conn = get_db()
    chapter_ids = [r["id"] for r in conn.execute("SELECT id FROM chapters ORDER BY sort_order ASC").fetchall()]
    completed = conn.execute("SELECT COUNT(*) AS c FROM chapter_progress WHERE user_id=? AND completed=1", (request.current_user["id"],)).fetchone()[0] or 0
    certificate = conn.execute("SELECT * FROM certificates WHERE user_id=?", (request.current_user["id"],)).fetchone()
    last_attempt = conn.execute("SELECT * FROM final_test_attempts WHERE user_id=? ORDER BY id DESC LIMIT 1", (request.current_user["id"],)).fetchone()
    cooldown_remaining = 0
    if last_attempt and last_attempt["status"] != "active":
        submitted = last_attempt["submitted_at"] or last_attempt["started_at"]
        if submitted:
            elapsed_days = (datetime.utcnow() - datetime.strptime(submitted, "%Y-%m-%d %H:%M:%S")).total_seconds() / 86400
            cooldown_remaining = max(0, 7 - elapsed_days)
    active = conn.execute("SELECT * FROM final_test_attempts WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1", (request.current_user["id"],)).fetchone()
    conn.close()
    return jsonify({
        "all_chapters_completed": len(chapter_ids) > 0 and completed >= len(chapter_ids),
        "has_certificate": certificate is not None,
        "certificate": dict(certificate) if certificate else None,
        "cooldown_remaining_hours": round(cooldown_remaining * 24, 1),
        "can_attempt": len(chapter_ids) > 0 and completed >= len(chapter_ids) and certificate is None and cooldown_remaining == 0,
        "active_attempt": {
            "id": active["id"],
            "status": active["status"],
            "started_at": active["started_at"],
            "remaining_seconds": max(0, 1800 - int((datetime.utcnow() - datetime.strptime(active["started_at"], "%Y-%m-%d %H:%M:%S")).total_seconds())),
            "score": active["score"],
            "passed": bool(active["passed"]),
            "timed_out": bool(active["timed_out"]),
        } if active else None,
        "pass_score": 75,
        "duration_seconds": 1800,
        "total_questions": 6,
    })


@app.route("/api/fatima/final-test/start", methods=["POST"])
@require_auth
def fatima_final_test_start():
    conn = get_db()
    chapter_ids = [r["id"] for r in conn.execute("SELECT id FROM chapters ORDER BY sort_order ASC").fetchall()]
    completed = conn.execute("SELECT COUNT(*) AS c FROM chapter_progress WHERE user_id=? AND completed=1", (request.current_user["id"],)).fetchone()[0] or 0
    if len(chapter_ids) == 0 or completed < len(chapter_ids):
        conn.close()
        return jsonify({"error": "Complete all chapters before taking the final test"}), 403
    if conn.execute("SELECT id FROM certificates WHERE user_id=?", (request.current_user["id"],)).fetchone():
        conn.close()
        return jsonify({"error": "You have already passed and received a certificate"}), 409
    active = conn.execute("SELECT * FROM final_test_attempts WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1", (request.current_user["id"],)).fetchone()
    if active:
        questions = conn.execute("SELECT * FROM final_test_questions ORDER BY id ASC").fetchall()
        conn.close()
        return jsonify({"attempt": {"id": active["id"], "status": active["status"], "started_at": active["started_at"], "remaining_seconds": max(0, 1800 - int((datetime.utcnow() - datetime.strptime(active["started_at"], "%Y-%m-%d %H:%M:%S")).total_seconds())), "score": active["score"], "passed": bool(active["passed"]), "timed_out": bool(active["timed_out"])}, "questions": [{"id": q["id"], "question": q["question"], "options": json.loads(q["options"]) if q["options"] else []} for q in questions]})
    cur = conn.execute("INSERT INTO final_test_attempts (user_id, started_at, status) VALUES (?, ?, 'active')", (request.current_user["id"], now()))
    conn.commit()
    attempt = conn.execute("SELECT * FROM final_test_attempts WHERE id=?", (cur.lastrowid,)).fetchone()
    questions = conn.execute("SELECT * FROM final_test_questions ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify({"attempt": {"id": attempt["id"], "status": attempt["status"], "started_at": attempt["started_at"], "remaining_seconds": 1800, "score": None, "passed": False, "timed_out": False}, "questions": [{"id": q["id"], "question": q["question"], "options": json.loads(q["options"]) if q["options"] else []} for q in questions]}), 201


@app.route("/api/fatima/final-test/submit", methods=["POST"])
@require_auth
def fatima_final_test_submit():
    data = request.get_json() or {}
    conn = get_db()
    active = conn.execute("SELECT * FROM final_test_attempts WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1", (request.current_user["id"],)).fetchone()
    if not active:
        conn.close()
        return jsonify({"error": "No active test session"}), 404
    answers = data.get("answers") or {}
    questions = conn.execute("SELECT * FROM final_test_questions ORDER BY id ASC").fetchall()
    correct = 0
    details = []
    for q in questions:
        selected = answers.get(str(q["id"]))
        is_correct = selected == q["answer"]
        if is_correct:
            correct += 1
        details.append({"id": q["id"], "question": q["question"], "options": json.loads(q["options"]) if q["options"] else [], "your_answer": selected, "correct_answer": q["answer"], "is_correct": is_correct, "explanation": q["explanation"]})
    score = round((correct / len(questions)) * 100) if questions else 0
    passed = score >= 75
    conn.execute("UPDATE final_test_attempts SET submitted_at=?, answers=?, score=?, passed=?, timed_out=?, status='submitted' WHERE id=?", (now(), json.dumps(answers), score, 1 if passed else 0, 0, active["id"]))
    if passed:
        conn.execute("INSERT OR IGNORE INTO certificates (user_id, attempt_id, score, issued_at) VALUES (?, ?, ?, ?)", (request.current_user["id"], active["id"], score, now()))
    conn.commit()
    certificate = conn.execute("SELECT * FROM certificates WHERE user_id=?", (request.current_user["id"],)).fetchone()
    conn.close()
    return jsonify({"score": score, "passed": passed, "correct": correct, "total": len(questions), "attempted": len(details), "timed_out": False, "details": details, "certificate": dict(certificate) if certificate else None})


@app.route("/api/fatima/certificate/me", methods=["GET"])
@require_auth
def fatima_certificate_me():
    conn = get_db()
    cert = conn.execute("SELECT * FROM certificates WHERE user_id=?", (request.current_user["id"],)).fetchone()
    conn.close()
    if not cert:
        return jsonify({"has_certificate": False})
    return jsonify({"has_certificate": True, "certificate": dict(cert)})


@app.route("/api/rabia/enhancer/sessions", methods=["GET"])
@require_auth
def rabia_get_sessions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM enhancement_sessions WHERE user_id=? ORDER BY updated_at DESC", (request.current_user["id"],)).fetchall()
    conn.close()
    return jsonify({"sessions": [
        {"id": r["id"], "title": r["title"], "original_prompt": r["original_prompt"], "status": r["status"], "created_at": r["created_at"], "updated_at": r["updated_at"]}
        for r in rows
    ]})


@app.route("/api/rabia/enhancer/sessions", methods=["POST"])
@require_auth
def rabia_create_session():
    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    title = (data.get("title") or "New enhancement").strip() or "New enhancement"
    conn = get_db()
    cur = conn.execute("INSERT INTO enhancement_sessions (user_id, title, original_prompt, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)", (request.current_user["id"], title, prompt, now(), now()))
    conn.commit()
    session = _serialize_enhancement_session(conn, cur.lastrowid, request.current_user["id"])
    conn.close()
    return jsonify({"session": session}), 201


@app.route("/api/rabia/enhancer/sessions/<int:session_id>", methods=["GET"])
@require_auth
def rabia_get_session(session_id: int):
    conn = get_db()
    session = _serialize_enhancement_session(conn, session_id, request.current_user["id"])
    conn.close()
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"session": session})


@app.route("/api/rabia/enhancer/sessions/<int:session_id>", methods=["DELETE"])
@require_auth
def rabia_delete_session(session_id: int):
    conn = get_db()
    conn.execute("DELETE FROM enhancement_sessions WHERE id=? AND user_id=?", (session_id, request.current_user["id"]))
    conn.execute("DELETE FROM enhancement_messages WHERE session_id=? AND user_id=?", (session_id, request.current_user["id"]))
    conn.execute("DELETE FROM enhancement_versions WHERE session_id=? AND user_id=?", (session_id, request.current_user["id"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Session deleted"})


@app.route("/api/rabia/enhancer/enhance", methods=["POST"])
@require_auth
def rabia_enhance_prompt():
    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    conn = get_db()
    title = f"Enhancement for {prompt[:40]}"
    cur = conn.execute("INSERT INTO enhancement_sessions (user_id, title, original_prompt, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)", (request.current_user["id"], title, prompt, now(), now()))
    session_id = cur.lastrowid
    enhanced = build_enhanced_prompt(prompt, 1)
    conn.execute("INSERT INTO enhancement_versions (session_id, user_id, version_number, input_prompt, enhanced_prompt, clarity_score, specificity_score, structure_score, completeness_score, intent_score, overall_score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (session_id, request.current_user["id"], 1, prompt, enhanced, 80, 78, 79, 77, 80, 79, now()))
    conn.execute("INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration, created_at) VALUES (?, ?, 'user', ?, 1, ?)", (session_id, request.current_user["id"], prompt, now()))
    conn.execute("INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration, created_at) VALUES (?, ?, 'assistant', ?, 1, ?)", (session_id, request.current_user["id"], enhanced, now()))
    conn.commit()
    session = _serialize_enhancement_session(conn, session_id, request.current_user["id"])
    conn.close()
    return jsonify({"session": session})


@app.route("/api/rabia/enhancer/sessions/<int:session_id>/enhance-again", methods=["POST"])
@require_auth
def rabia_enhance_again(session_id: int):
    conn = get_db()
    session = conn.execute("SELECT * FROM enhancement_sessions WHERE id=? AND user_id=?", (session_id, request.current_user["id"])).fetchone()
    if not session:
        conn.close()
        return jsonify({"error": "Session not found"}), 404
    last_version = conn.execute("SELECT MAX(version_number) AS max_v FROM enhancement_versions WHERE session_id=? AND user_id=?", (session_id, request.current_user["id"])).fetchone()[0] or 0
    next_iteration = min(int(last_version) + 1, 3)
    enhanced = build_enhanced_prompt(session["original_prompt"], next_iteration)
    conn.execute("INSERT INTO enhancement_versions (session_id, user_id, version_number, input_prompt, enhanced_prompt, clarity_score, specificity_score, structure_score, completeness_score, intent_score, overall_score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (session_id, request.current_user["id"], next_iteration, session["original_prompt"], enhanced, 81, 80, 82, 78, 81, 80, now()))
    conn.execute("INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration, created_at) VALUES (?, ?, 'user', ?, ?, ?)", (session_id, request.current_user["id"], "enhance again", next_iteration, now()))
    conn.execute("INSERT INTO enhancement_messages (session_id, user_id, role, content, iteration, created_at) VALUES (?, ?, 'assistant', ?, ?, ?)", (session_id, request.current_user["id"], enhanced, next_iteration, now()))
    conn.commit()
    session_payload = _serialize_enhancement_session(conn, session_id, request.current_user["id"])
    conn.close()
    return jsonify({"session": session_payload})


@app.route("/api/rabia/enhancer/sessions/<int:session_id>/versions", methods=["GET"])
@require_auth
def rabia_get_versions(session_id: int):
    conn = get_db()
    rows = conn.execute("SELECT * FROM enhancement_versions WHERE session_id=? AND user_id=? ORDER BY version_number ASC", (session_id, request.current_user["id"])).fetchall()
    conn.close()
    return jsonify({"versions": [
        {"id": r["id"], "version_number": r["version_number"], "enhanced_prompt": r["enhanced_prompt"], "overall_score": r["overall_score"], "created_at": r["created_at"]}
        for r in rows
    ]})


@app.route("/api/rabia/enhancer/sessions/<int:session_id>/messages", methods=["GET"])
@require_auth
def rabia_get_messages(session_id: int):
    conn = get_db()
    rows = conn.execute("SELECT * FROM enhancement_messages WHERE session_id=? AND user_id=? ORDER BY created_at ASC", (session_id, request.current_user["id"])).fetchall()
    conn.close()
    return jsonify({"messages": [
        {"id": r["id"], "role": r["role"], "content": r["content"], "iteration": r["iteration"], "created_at": r["created_at"]}
        for r in rows
    ]})


# ================================================================
#  HEALTH CHECK
# ================================================================
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": " Running", "url": "http://localhost:5000",
                    "message": "Sab kuch ek jagah chal raha hai!"})


# ================================================================
#  RUN
# ================================================================
# Runs both when this file is executed directly (python main.py)
# AND when imported by a production server like gunicorn (gunicorn main:app)
init_db()

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  PromptLab - Single Backend")
    print("="*55)
    print("  URL: http://localhost:5000")
    print()
    print("  Laiba   -> /api/evaluate, /api/chat, /api/sessions ...")
    print("  Areeba  -> /api/areeba/register, /api/areeba/login ...")
    print("  Fatima  -> /api/fatima/practice-feedback ...")
    print("  Rabia   -> /api/rabia/enhance, /api/rabia/quick-answer ...")
    print()
    print("  Health: http://localhost:5000/api/health")
    print("="*55 + "\n")
    app.run(debug=False, use_reloader=False, port=5000)
