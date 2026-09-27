# ================================================================
# AREEBA'S BACKEND — Auth, Dashboard, History & Sunday Reminders
# Run: python app.py
# Port: 5001
# ================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import hashlib
import hmac
import os
import random
import re
import secrets
import sqlite3
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # APScheduler is optional until installed
    BackgroundScheduler = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
DB = os.path.join(BASE_DIR, "areeba.db")

app = Flask(__name__)
CORS(app)


# ── DATABASE ─────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            detail TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompt_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_type TEXT NOT NULL,
            original_prompt TEXT NOT NULL,
            ai_response TEXT,
            improved_prompt TEXT,
            explanation TEXT,
            resources TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            bot_response TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminder_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            current_streak INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_activity_date TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            verification_code TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            last_sent_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ── SECURITY HELPERS ──────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash password using PBKDF2. Stores salt + hash in one string."""
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
    """Return an error message if password does not meet strength requirements, else None."""
    if len(password) < 6:
        return "Password must be at least 6 characters"
    if not re.search(r'[A-Z]', password):
        return "Password must include at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return "Password must include at least one lowercase letter"
    if not re.search(r'[^A-Za-z0-9]', password):
        return "Password must include at least one symbol (@, #, $, %...)"
    return None


def send_reset_email(to_email: str, username: str, otp: str) -> tuple[str, str]:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        return "dry_run", otp  # Return raw OTP so devs can test without email

    msg = EmailMessage()
    msg["Subject"] = "PromptLab — Password Reset Code"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(
        f"Hi {username},\n\n"
        f"Your password reset code is: {otp}\n\n"
        "This code expires in 15 minutes. If you didn't request a reset, please ignore this email.\n\n"
        "Regards,\nPromptLab Team"
    )
    tls_context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.ehlo()
        server.starttls(context=tls_context)
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    return "sent", "Reset email sent"


def send_verification_email(to_email: str, username: str, otp: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP_USER and SMTP_PASSWORD are required")

    msg = EmailMessage()
    msg["Subject"] = "PromptLab - Verify your email"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(
        f"Hi {username},\n\n"
        f"Your PromptLab verification code is: {otp}\n\n"
        "This code expires in 10 minutes. If you did not create this account, ignore this email.\n\n"
        "Regards,\nPromptLab Team"
    )

    tls_context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.ehlo()
        server.starttls(context=tls_context)
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def make_user(row):
    return {
        "id": str(row["id"]),
        "name": row["username"],
        "email": row["email"],
        "last_activity": row["last_activity"],
    }


def update_activity(user_id: int, activity_type: str = "active", detail: str | None = None):
    db = get_db()
    db.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
    db.execute(
        "INSERT INTO activity_logs (user_id, activity_type, detail) VALUES (?,?,?)",
        (user_id, activity_type, detail),
    )
    _MEANINGFUL = {"login", "signup", "direct_prompt", "learning", "chat", "practice_attempt", "chapter_completed"}
    if activity_type in _MEANINGFUL:
        _update_streak(user_id, db)
    db.commit()
    db.close()


# ── STREAK HELPERS ────────────────────────────────────────────
def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _yesterday() -> str:
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def _update_streak(user_id: int, db):
    today = _today()
    yesterday = _yesterday()
    row = db.execute("SELECT * FROM user_streaks WHERE user_id=?", (user_id,)).fetchone()

    if not row:
        _backfill_streak(user_id, db)
        return

    last_date = row["last_activity_date"]
    if last_date == today:
        return  # Already recorded today

    current = int(row["current_streak"])
    longest = int(row["longest_streak"])

    if last_date == yesterday:
        new_current = current + 1
        new_longest = max(longest, new_current)
    else:
        new_current = 1
        new_longest = max(longest, 1)

    db.execute(
        "UPDATE user_streaks SET current_streak=?, longest_streak=?, last_activity_date=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
        (new_current, new_longest, today, user_id),
    )


def _backfill_streak(user_id: int, db):
    """Compute streak from existing activity_logs when creating the first streak record."""
    _MEANINGFUL = ("login", "signup", "direct_prompt", "learning", "chat", "practice_attempt", "chapter_completed")
    placeholders = ",".join("?" * len(_MEANINGFUL))
    rows = db.execute(
        f"""
        SELECT DISTINCT date(created_at) AS day
        FROM activity_logs
        WHERE user_id=? AND activity_type IN ({placeholders})
        ORDER BY day DESC
        """,
        (user_id, *_MEANINGFUL),
    ).fetchall()

    today = _today()
    yesterday = _yesterday()

    if not rows:
        db.execute(
            "INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date) VALUES (?,1,1,?)",
            (user_id, today),
        )
        return

    dates = [r["day"] for r in rows]
    last_date = dates[0]

    # Count current streak backwards from most recent date
    current = 1
    for i in range(1, len(dates)):
        expected = (datetime.strptime(dates[i - 1], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if dates[i] == expected:
            current += 1
        else:
            break

    # Streak is broken if last activity is older than yesterday
    if last_date != today and last_date != yesterday:
        current = 1

    # Find longest ever streak
    longest = 1
    run = 1
    for i in range(1, len(dates)):
        expected = (datetime.strptime(dates[i - 1], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if dates[i] == expected:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    longest = max(longest, current)

    db.execute(
        "INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date) VALUES (?,?,?,?)",
        (user_id, current, longest, today),
    )


def get_streak_data(user_id: int, db) -> dict:
    today = _today()
    yesterday = _yesterday()
    row = db.execute("SELECT * FROM user_streaks WHERE user_id=?", (user_id,)).fetchone()

    if not row:
        return {"current_streak": 0, "longest_streak": 0, "status": "broken", "last_activity_date": None}

    last_date = row["last_activity_date"]
    current = int(row["current_streak"])
    longest = int(row["longest_streak"])

    if last_date == today:
        status = "active"
    elif last_date == yesterday:
        status = "at_risk"
    else:
        status = "broken"
        current = 0

    return {
        "current_streak": current,
        "longest_streak": longest,
        "status": status,
        "last_activity_date": last_date,
    }


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if not token:
            return jsonify({"error": "Missing token"}), 401

        db = get_db()
        row = db.execute(
            """
            SELECT users.* FROM users
            JOIN user_sessions ON users.id = user_sessions.user_id
            WHERE user_sessions.token=?
            """,
            (token,),
        ).fetchone()
        db.close()

        if not row:
            return jsonify({"error": "Invalid token"}), 401

        request.current_user = row
        return fn(*args, **kwargs)

    return wrapper


# ── AUTH ROUTES ───────────────────────────────────────────────
@app.route("/api/areeba/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    pw_err = validate_password(password)
    if pw_err:
        return jsonify({"error": pw_err}), 400

    db = get_db()
    try:
        if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            return jsonify({"error": "Email already exists"}), 409

        otp = str(random.randint(100000, 999999))
        now = datetime.utcnow()
        expires_at = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        last_sent_at = now.strftime("%Y-%m-%d %H:%M:%S")
        password_hash = hash_password(password)

        send_verification_email(email, username, otp)
        db.execute(
            """
            INSERT INTO pending_registrations
                (username, email, password_hash, verification_code, expires_at, last_sent_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET
                username=excluded.username,
                password_hash=excluded.password_hash,
                verification_code=excluded.verification_code,
                expires_at=excluded.expires_at,
                last_sent_at=excluded.last_sent_at
            """,
            (username, email, password_hash, otp, expires_at, last_sent_at),
        )
        db.commit()
        return jsonify({
            "message": "Verification code sent",
            "email": email,
            "expires_in": 600,
            "resend_after": 45,
        }), 202
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception:
        app.logger.exception("Registration verification email delivery failed")
        return jsonify({"error": "Failed to send verification email, please try again later."}), 500
    finally:
        db.close()


@app.route("/api/areeba/verify-registration", methods=["POST"])
def verify_registration():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    if not email or not code:
        return jsonify({"error": "Email and verification code are required"}), 400

    db = get_db()
    pending = db.execute(
        "SELECT * FROM pending_registrations WHERE email=?",
        (email,),
    ).fetchone()
    if not pending:
        db.close()
        return jsonify({"error": "Verification request not found. Please sign up again."}), 404
    if datetime.utcnow() > datetime.strptime(pending["expires_at"], "%Y-%m-%d %H:%M:%S"):
        db.close()
        return jsonify({"error": "Verification code expired. Please resend code.", "expired": True}), 410
    if not hmac.compare_digest(code, pending["verification_code"]):
        db.close()
        return jsonify({"error": "Invalid code, please try again."}), 400

    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
            (pending["username"], pending["email"], pending["password_hash"]),
        )
        user_id = cur.lastrowid
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO user_sessions (user_id, token) VALUES (?,?)", (user_id, token))
        db.execute(
            "INSERT INTO activity_logs (user_id, activity_type, detail) VALUES (?,?,?)",
            (user_id, "signup", "User verified email and created account"),
        )
        _update_streak(user_id, db)
        db.execute("DELETE FROM pending_registrations WHERE id=?", (pending["id"],))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return jsonify({
            "message": "Email verified and account created",
            "token": token,
            "user": make_user(user),
        }), 201
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({"error": "Email already exists"}), 409
    finally:
        db.close()


@app.route("/api/areeba/resend-registration-code", methods=["POST"])
def resend_registration_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    db = get_db()
    pending = db.execute(
        "SELECT * FROM pending_registrations WHERE email=?",
        (email,),
    ).fetchone()
    if not pending:
        db.close()
        return jsonify({"error": "Verification request not found. Please sign up again."}), 404

    now = datetime.utcnow()
    last_sent = datetime.strptime(pending["last_sent_at"], "%Y-%m-%d %H:%M:%S")
    remaining = 45 - int((now - last_sent).total_seconds())
    if remaining > 0:
        db.close()
        return jsonify({"error": f"Please wait {remaining} seconds before resending.", "retry_after": remaining}), 429

    otp = str(random.randint(100000, 999999))
    expires_at = (now + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        send_verification_email(email, pending["username"], otp)
        db.execute(
            """
            UPDATE pending_registrations
            SET verification_code=?, expires_at=?, last_sent_at=?
            WHERE id=?
            """,
            (otp, expires_at, now.strftime("%Y-%m-%d %H:%M:%S"), pending["id"]),
        )
        db.commit()
        return jsonify({"message": "A new verification code was sent.", "resend_after": 45})
    except Exception:
        app.logger.exception("Registration verification email resend failed")
        return jsonify({"error": "Failed to resend verification email, please try again later."}), 500
    finally:
        db.close()


@app.route("/api/areeba/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        db.close()
        return jsonify({"error": "Invalid email or password"}), 401

    token = secrets.token_urlsafe(32)
    db.execute("INSERT INTO user_sessions (user_id, token) VALUES (?,?)", (user["id"], token))
    db.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (user["id"],))
    db.execute(
        "INSERT INTO activity_logs (user_id, activity_type, detail) VALUES (?,?,?)",
        (user["id"], "login", "User logged in"),
    )
    _update_streak(user["id"], db)
    db.commit()
    db.close()

    return jsonify({"message": "Login successful", "token": token, "user": make_user(user)})


@app.route("/api/areeba/me", methods=["GET"])
@require_auth
def me():
    update_activity(request.current_user["id"], "active", "Checked session")
    return jsonify({"user": make_user(request.current_user)})


@app.route("/api/areeba/logout", methods=["POST"])
@require_auth
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    db = get_db()
    db.execute("DELETE FROM user_sessions WHERE token=?", (token,))
    db.commit()
    db.close()
    return jsonify({"message": "Logged out"})


@app.route("/api/areeba/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if not user:
        # Don't reveal whether the email exists
        return jsonify({"message": "If that email is registered, a reset code has been sent."}), 200

    otp = str(random.randint(100000, 999999))
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

    # Invalidate any existing unused tokens for this user
    db.execute("UPDATE password_reset_tokens SET used=1 WHERE user_id=? AND used=0", (user["id"],))
    db.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?,?,?)",
        (user["id"], otp, expires_at),
    )
    db.commit()

    try:
        status, detail = send_reset_email(email, user["username"], otp)
    except Exception as exc:
        status, detail = "failed", str(exc)
        app.logger.exception("Password reset email delivery failed")
    db.close()

    if status != "sent":
        # Do not leave a usable reset token behind when delivery failed.
        cleanup_db = get_db()
        cleanup_db.execute(
            "UPDATE password_reset_tokens SET used=1 WHERE user_id=? AND token=?",
            (user["id"], otp),
        )
        cleanup_db.commit()
        cleanup_db.close()
        return jsonify({"error": "Failed to send reset email, please try again later."}), 500

    return jsonify({"message": "If that email is registered, a reset code has been sent."}), 200


@app.route("/api/areeba/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    new_password = data.get("new_password") or ""

    if not email or not otp or not new_password:
        return jsonify({"error": "Email, OTP, and new password are required"}), 400

    pw_err = validate_password(new_password)
    if pw_err:
        return jsonify({"error": pw_err}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        db.close()
        return jsonify({"error": "Invalid or expired reset code"}), 400

    token_row = db.execute(
        """
        SELECT * FROM password_reset_tokens
        WHERE user_id=? AND token=? AND used=0
          AND datetime(expires_at) > datetime('now')
        ORDER BY created_at DESC LIMIT 1
        """,
        (user["id"], otp),
    ).fetchone()

    if not token_row:
        db.close()
        return jsonify({"error": "Invalid or expired reset code. Please request a new one."}), 400

    db.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(new_password), user["id"]),
    )
    db.execute("UPDATE password_reset_tokens SET used=1 WHERE id=?", (token_row["id"],))
    # Invalidate all existing sessions so the user must re-login
    db.execute("DELETE FROM user_sessions WHERE user_id=?", (user["id"],))
    db.commit()
    db.close()

    return jsonify({"message": "Password reset successfully. Please sign in with your new password."}), 200


# ── HISTORY ROUTES ────────────────────────────────────────────
@app.route("/api/areeba/prompt-history", methods=["POST"])
@require_auth
def save_prompt_history():
    data = request.get_json() or {}
    module_type = data.get("module_type") or "direct_prompt"
    original_prompt = data.get("original_prompt") or ""

    if not original_prompt.strip():
        return jsonify({"error": "original_prompt is required"}), 400

    db = get_db()
    db.execute(
        """
        INSERT INTO prompt_history
        (user_id, module_type, original_prompt, ai_response, improved_prompt, explanation, resources)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            request.current_user["id"],
            module_type,
            original_prompt,
            data.get("ai_response"),
            data.get("improved_prompt"),
            data.get("explanation"),
            data.get("resources"),
        ),
    )
    db.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (request.current_user["id"],))
    db.execute(
        "INSERT INTO activity_logs (user_id, activity_type, detail) VALUES (?,?,?)",
        (request.current_user["id"], module_type, original_prompt[:120]),
    )
    _MEANINGFUL = {"direct_prompt", "learning", "chat", "practice_attempt", "chapter_completed"}
    if module_type in _MEANINGFUL:
        _update_streak(request.current_user["id"], db)
    db.commit()
    db.close()
    return jsonify({"message": "Prompt history saved"}), 201


@app.route("/api/areeba/chat-history", methods=["POST"])
@require_auth
def save_chat_history():
    data = request.get_json() or {}
    user_message = data.get("user_message") or ""

    if not user_message.strip():
        return jsonify({"error": "user_message is required"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO chat_history (user_id, user_message, bot_response) VALUES (?,?,?)",
        (request.current_user["id"], user_message, data.get("bot_response")),
    )
    db.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (request.current_user["id"],))
    db.execute(
        "INSERT INTO activity_logs (user_id, activity_type, detail) VALUES (?,?,?)",
        (request.current_user["id"], "chat", user_message[:120]),
    )
    _update_streak(request.current_user["id"], db)
    db.commit()
    db.close()
    return jsonify({"message": "Chat history saved"}), 201


@app.route("/api/areeba/history", methods=["GET"])
@require_auth
def get_history():
    db = get_db()
    prompts = db.execute(
        "SELECT * FROM prompt_history WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (request.current_user["id"],),
    ).fetchall()
    chats = db.execute(
        "SELECT * FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (request.current_user["id"],),
    ).fetchall()
    db.close()
    return jsonify({"prompts": [dict(p) for p in prompts], "chats": [dict(c) for c in chats]})


# ── DASHBOARD ROUTES ─────────────────────────────────────────
@app.route("/api/areeba/dashboard/me", methods=["GET"])
@require_auth
def dashboard_me():
    return dashboard_data(request.current_user["id"], request.current_user)


@app.route("/api/areeba/dashboard/<int:user_id>", methods=["GET"])
def dashboard_by_id(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    db.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return dashboard_data(user_id, user)


def dashboard_data(user_id: int, user_row):
    db = get_db()
    prompt_total = db.execute("SELECT COUNT(*) c FROM prompt_history WHERE user_id=?", (user_id,)).fetchone()["c"]
    chat_total = db.execute("SELECT COUNT(*) c FROM chat_history WHERE user_id=?", (user_id,)).fetchone()["c"]
    learning_count = db.execute(
        "SELECT COUNT(*) c FROM prompt_history WHERE user_id=? AND module_type='learning'",
        (user_id,),
    ).fetchone()["c"]
    direct_count = db.execute(
        "SELECT COUNT(*) c FROM prompt_history WHERE user_id=? AND module_type='direct_prompt'",
        (user_id,),
    ).fetchone()["c"]
    recent_activity = db.execute(
        """
        SELECT activity_type, detail, created_at
        FROM activity_logs
        WHERE user_id=?
        ORDER BY created_at DESC
        LIMIT 8
        """,
        (user_id,),
    ).fetchall()
    streak = get_streak_data(user_id, db)
    db.close()

    return jsonify(
        {
            "user": make_user(user_row),
            "stats": {
                "total_prompts": prompt_total,
                "total_chats": chat_total,
                "learning_count": learning_count,
                "direct_prompt_count": direct_count,
                "total_activity": prompt_total + chat_total,
                "last_activity": user_row["last_activity"],
            },
            "recent_activity": [dict(a) for a in recent_activity],
            "streak": streak,
        }
    )


@app.route("/api/areeba/users", methods=["GET"])
def get_users():
    db = get_db()
    users = db.execute("SELECT id, username, email, created_at, last_activity FROM users ORDER BY created_at DESC").fetchall()
    db.close()
    return jsonify([dict(u) for u in users])


@app.route("/api/areeba/streak/me", methods=["GET"])
@require_auth
def streak_me():
    db = get_db()
    data = get_streak_data(request.current_user["id"], db)
    db.close()
    return jsonify(data)


# ── REMINDER EMAIL SYSTEM ────────────────────────────────────
def send_email(to_email: str, username: str) -> tuple[str, str]:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        return "dry_run", "Email not sent because SMTP_USER/SMTP_PASSWORD are not configured"

    msg = EmailMessage()
    msg["Subject"] = "We miss you on PromptLab"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(
        f"Hi {username},\n\n"
        "You have not used PromptLab recently. Come back this week and continue improving your prompt engineering skills.\n\n"
        "Regards,\nPromptLab Team"
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

    return "sent", "Reminder email sent"


def run_sunday_reminders():
    inactive_days = int(os.getenv("INACTIVE_DAYS", "7"))
    cutoff = datetime.now() - timedelta(days=inactive_days)

    db = get_db()
    users = db.execute(
        "SELECT * FROM users WHERE datetime(last_activity) <= datetime(?)",
        (cutoff.strftime("%Y-%m-%d %H:%M:%S"),),
    ).fetchall()

    results = []
    for user in users:
        try:
            status, message = send_email(user["email"], user["username"])
        except Exception as exc:
            status, message = "failed", str(exc)

        db.execute(
            "INSERT INTO reminder_logs (user_id, email, status, message) VALUES (?,?,?,?)",
            (user["id"], user["email"], status, message),
        )
        results.append({"email": user["email"], "status": status, "message": message})

    db.commit()
    db.close()
    return results


@app.route("/api/areeba/reminders/run", methods=["POST"])
def run_reminders_now():
    results = run_sunday_reminders()
    return jsonify({"checked_at": datetime.now().isoformat(), "results": results})


@app.route("/api/areeba/reminders/logs", methods=["GET"])
def reminder_logs():
    db = get_db()
    rows = db.execute("SELECT * FROM reminder_logs ORDER BY sent_at DESC LIMIT 50").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


def start_scheduler():
    if BackgroundScheduler is None:
        print("APScheduler not installed. Sunday reminders route still works manually.")
        return

    scheduler = BackgroundScheduler(timezone="Asia/Karachi")
    scheduler.add_job(run_sunday_reminders, "cron", day_of_week="sun", hour=9, minute=0)
    scheduler.start()
    print("Sunday reminder scheduler enabled: every Sunday at 09:00 Asia/Karachi")


# ── RUN ───────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    start_scheduler()
    print("\nAreeba's Backend Running")
    print("POST /api/areeba/register")
    print("POST /api/areeba/login")
    print("GET  /api/areeba/me")
    print("GET  /api/areeba/dashboard/me")
    print("POST /api/areeba/reminders/run\n")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
        debug=False
    )