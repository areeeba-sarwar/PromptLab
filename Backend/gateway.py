# ================================================================
#  PromptLab — API GATEWAY
#  Yeh file SIRF YAHI chalani hai frontend ke liye
#
#  Run: python gateway.py
#  Port: 8000
#
#  Internally yeh in services ko call karta hai:
#    Laiba   → http://localhost:5000
#    Areeba  → http://localhost:5001
#    Fatima  → http://localhost:5002
#    Rabia   → http://localhost:5003
#
#  Frontend mein SIRF ek URL use karo:
#    http://localhost:8000
# ================================================================

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests as req
import json

app = Flask(__name__)
CORS(app)

# ── Service URLs ──────────────────────────────────────────────
LAIBA  = "http://localhost:5000"
AREEBA = "http://localhost:5001"
FATIMA = "http://localhost:5002"
RABIA  = "http://localhost:5003"


# ── Helper: forward request to a service ─────────────────────
def forward(method, url, **kwargs):
    """
    Kisi bhi service pe request forward karta hai.
    Agar service band ho to error object return karta hai — crash nahi hota.
    """
    try:
        resp = req.request(method, url, timeout=60, **kwargs)
        return resp.json(), resp.status_code
    except req.exceptions.ConnectionError:
        service = url.split("localhost:")[1].split("/")[0]
        names   = {"5000": "Laiba", "5001": "Areeba", "5002": "Fatima", "5003": "Rabia"}
        name    = names.get(service, f"Port {service}")
        return {"error": f"{name} ka server band hai — python app.py chala ke dekho"}, 503
    except Exception as e:
        return {"error": str(e)}, 500


def fwd_get(url, params=None):
    return forward("GET", url, params=params)

def fwd_post(url, body=None):
    return forward("POST", url, json=body)

def fwd_delete(url):
    return forward("DELETE", url)

def auth_headers():
    headers = {}
    auth = request.headers.get("Authorization")
    if auth:
        headers["Authorization"] = auth
    return headers

def fwd_get_auth(url, params=None):
    return forward("GET", url, params=params, headers=auth_headers())

def fwd_post_auth(url, body=None):
    return forward("POST", url, json=body, headers=auth_headers())

def fwd_delete_auth(url):
    return forward("DELETE", url, headers=auth_headers())


# ================================================================
#  LAIBA ROUTES (Port 5000)
#  Core evaluation, chat, sessions, analytics
# ================================================================

@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    data, status = fwd_post(f"{LAIBA}/api/evaluate", request.get_json())
    return jsonify(data), status


@app.route("/api/chat", methods=["POST"])
def chat():
    data, status = fwd_post(f"{LAIBA}/api/chat", request.get_json())
    return jsonify(data), status


@app.route("/api/suggest", methods=["POST"])
def suggest():
    data, status = fwd_post(f"{LAIBA}/api/suggest", request.get_json())
    return jsonify(data), status


@app.route("/api/multi-agent", methods=["POST"])
def multi_agent():
    data, status = fwd_post(f"{LAIBA}/api/multi-agent", request.get_json())
    return jsonify(data), status


@app.route("/api/security", methods=["POST"])
def security():
    data, status = fwd_post(f"{LAIBA}/api/security", request.get_json())
    return jsonify(data), status


@app.route("/api/difficulty", methods=["POST"])
def difficulty():
    data, status = fwd_post(f"{LAIBA}/api/difficulty", request.get_json())
    return jsonify(data), status


@app.route("/api/mutate", methods=["POST"])
def mutate():
    data, status = fwd_post(f"{LAIBA}/api/mutate", request.get_json())
    return jsonify(data), status


@app.route("/api/domain", methods=["POST"])
def domain():
    data, status = fwd_post(f"{LAIBA}/api/domain", request.get_json())
    return jsonify(data), status


@app.route("/api/history/<int:user_id>", methods=["GET"])
def history(user_id):
    data, status = fwd_get(f"{LAIBA}/api/history/{user_id}")
    return jsonify(data), status


@app.route("/api/analytics/<int:user_id>", methods=["GET"])
def analytics(user_id):
    data, status = fwd_get(f"{LAIBA}/api/analytics/{user_id}")
    return jsonify(data), status


@app.route("/api/progress/<int:user_id>", methods=["GET"])
def progress(user_id):
    data, status = fwd_get(f"{LAIBA}/api/progress/{user_id}")
    return jsonify(data), status


@app.route("/api/templates", methods=["GET"])
def templates():
    data, status = fwd_get(f"{LAIBA}/api/templates", params=request.args)
    return jsonify(data), status


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    data, status = fwd_get(f"{LAIBA}/api/leaderboard")
    return jsonify(data), status


@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    data, status = fwd_get(f"{LAIBA}/api/admin/stats")
    return jsonify(data), status


# Sessions
@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    data, status = fwd_get(f"{LAIBA}/api/sessions", params=request.args)
    return jsonify(data), status


@app.route("/api/sessions", methods=["POST"])
def create_session():
    data, status = fwd_post(f"{LAIBA}/api/sessions", request.get_json())
    return jsonify(data), status


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    data, status = fwd_delete(f"{LAIBA}/api/sessions/{session_id}")
    return jsonify(data), status


@app.route("/api/sessions/<int:session_id>/messages", methods=["GET"])
def get_messages(session_id):
    data, status = fwd_get(f"{LAIBA}/api/sessions/{session_id}/messages")
    return jsonify(data), status


@app.route("/api/sessions/<int:session_id>/messages", methods=["POST"])
def save_message(session_id):
    data, status = fwd_post(f"{LAIBA}/api/sessions/{session_id}/messages", request.get_json())
    return jsonify(data), status


# ================================================================
#  AREEBA ROUTES (Port 5001)
#  User management, login, register, dashboard
# ================================================================

@app.route("/api/areeba/register", methods=["POST"])
def areeba_register():
    data, status = fwd_post(f"{AREEBA}/api/areeba/register", request.get_json())
    return jsonify(data), status


@app.route("/api/areeba/login", methods=["POST"])
def areeba_login():
    data, status = fwd_post(f"{AREEBA}/api/areeba/login", request.get_json())
    return jsonify(data), status


@app.route("/api/areeba/users", methods=["GET"])
def areeba_users():
    data, status = fwd_get(f"{AREEBA}/api/areeba/users")
    return jsonify(data), status


@app.route("/api/areeba/dashboard/<int:user_id>", methods=["GET"])
def areeba_dashboard(user_id):
    data, status = fwd_get(f"{AREEBA}/api/areeba/dashboard/{user_id}")
    return jsonify(data), status


@app.route("/api/areeba/tip/<int:user_id>", methods=["GET"])
def areeba_tip(user_id):
    data, status = fwd_get(f"{AREEBA}/api/areeba/tip/{user_id}")
    return jsonify(data), status


# ================================================================
#  FATIMA ROUTES (Port 5002)
#  Learning mode, practice feedback, progress tracking
# ================================================================

@app.route("/api/fatima/save-prompt", methods=["POST"])
def fatima_save_prompt():
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/save-prompt", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/prompts/<int:user_id>", methods=["GET"])
def fatima_prompts(user_id):
    data, status = fwd_get(f"{FATIMA}/api/fatima/prompts/{user_id}")
    return jsonify(data), status


@app.route("/api/fatima/learning-tip", methods=["POST"])
def fatima_learning_tip():
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/learning-tip", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/practice-feedback", methods=["POST"])
def fatima_practice_feedback():
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/practice-feedback", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/update-progress", methods=["POST"])
def fatima_update_progress():
    data, status = fwd_post(f"{FATIMA}/api/fatima/update-progress", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/progress/<int:user_id>", methods=["GET"])
def fatima_progress(user_id):
    data, status = fwd_get(f"{FATIMA}/api/fatima/progress/{user_id}")
    return jsonify(data), status


@app.route("/api/fatima/chapters", methods=["GET"])
def fatima_chapters():
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/chapters")
    return jsonify(data), status


@app.route("/api/fatima/chapters/<chapter_id>", methods=["GET"])
def fatima_chapter(chapter_id):
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/chapters/{chapter_id}")
    return jsonify(data), status


@app.route("/api/fatima/chapters/<chapter_id>/questions", methods=["GET"])
def fatima_chapter_questions(chapter_id):
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/chapters/{chapter_id}/questions")
    return jsonify(data), status


@app.route("/api/fatima/practice/start", methods=["POST"])
def fatima_practice_start():
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/practice/start", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/practice/<int:session_id>/submit", methods=["POST"])
def fatima_practice_submit(session_id):
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/practice/{session_id}/submit", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/practice/<int:session_id>/change-question", methods=["POST"])
def fatima_practice_change_question(session_id):
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/practice/{session_id}/change-question", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/practice/sessions", methods=["GET"])
def fatima_practice_sessions():
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/practice/sessions")
    return jsonify(data), status


@app.route("/api/fatima/practice/sessions/<int:session_id>", methods=["GET"])
def fatima_practice_session(session_id):
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/practice/sessions/{session_id}")
    return jsonify(data), status


@app.route("/api/fatima/progress/me", methods=["GET"])
def fatima_progress_me():
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/progress/me")
    return jsonify(data), status


@app.route("/api/fatima/dashboard/me", methods=["GET"])
def fatima_dashboard_me():
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/dashboard/me")
    return jsonify(data), status


@app.route("/api/fatima/final-test/status", methods=["GET"])
def fatima_final_test_status():
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/final-test/status")
    return jsonify(data), status


@app.route("/api/fatima/final-test/start", methods=["POST"])
def fatima_final_test_start():
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/final-test/start", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/final-test/submit", methods=["POST"])
def fatima_final_test_submit():
    data, status = fwd_post_auth(f"{FATIMA}/api/fatima/final-test/submit", request.get_json())
    return jsonify(data), status


@app.route("/api/fatima/certificate/me", methods=["GET"])
def fatima_certificate_me():
    data, status = fwd_get_auth(f"{FATIMA}/api/fatima/certificate/me")
    return jsonify(data), status


# ================================================================
#  RABIA ROUTES (Port 5003)
#  Quick answer, prompt enhancer, history
# ================================================================

@app.route("/api/rabia/quick-answer", methods=["POST"])
def rabia_quick_answer():
    data, status = fwd_post(f"{RABIA}/api/rabia/quick-answer", request.get_json())
    return jsonify(data), status


@app.route("/api/rabia/enhance", methods=["POST"])
def rabia_enhance():
    data, status = fwd_post(f"{RABIA}/api/rabia/enhance", request.get_json())
    return jsonify(data), status


@app.route("/api/rabia/history/<int:user_id>", methods=["GET"])
def rabia_history(user_id):
    data, status = fwd_get(f"{RABIA}/api/rabia/history/{user_id}")
    return jsonify(data), status


@app.route("/api/rabia/rate", methods=["POST"])
def rabia_rate():
    data, status = fwd_post(f"{RABIA}/api/rabia/rate", request.get_json())
    return jsonify(data), status


@app.route("/api/rabia/enhancements/<int:user_id>", methods=["GET"])
def rabia_enhancements(user_id):
    data, status = fwd_get(f"{RABIA}/api/rabia/enhancements/{user_id}")
    return jsonify(data), status


@app.route("/api/rabia/suggestions", methods=["POST"])
def rabia_suggestions():
    data, status = fwd_post(f"{RABIA}/api/rabia/suggestions", request.get_json())
    return jsonify(data), status


# ================================================================
#  HEALTH CHECK
#  GET /api/health → check karo kaun kaun sa server chal raha hai
# ================================================================

@app.route("/api/health", methods=["GET"])
def health():
    services = {
        "laiba":  f"{LAIBA}/api/templates",
        "areeba": f"{AREEBA}/api/areeba/users",
        "fatima": f"{FATIMA}/api/fatima/progress/1",
        "rabia":  f"{RABIA}/api/rabia/history/1",
    }
    status = {}
    for name, url in services.items():
        try:
            r = req.get(url, timeout=3)
            status[name] = "✅ Running"
        except:
            status[name] = "❌ Band hai — python app.py chalo"
    return jsonify({"gateway": "✅ Running", "services": status})


# ================================================================
#  RUN
# ================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  PromptLab API Gateway")
    print("="*60)
    print("  Gateway:  http://localhost:8000")
    print()
    print("  Forwarding to:")
    print("    Laiba   → http://localhost:5000  (agent.py)")
    print("    Areeba  → http://localhost:5001  (app.py)")
    print("    Fatima  → http://localhost:5002  (app.py)")
    print("    Rabia   → http://localhost:5003  (app.py)")
    print()
    print("  Health check: http://localhost:8000/api/health")
    print("="*60)
    print()
    print("  ⚠️  Pehle sab services chala lo:")
    print("    Terminal 1: cd laiba   && python agent.py")
    print("    Terminal 2: cd areeba  && python app.py")
    print("    Terminal 3: cd fatima  && python app.py")
    print("    Terminal 4: cd rabia   && python app.py")
    print("    Terminal 5: cd ..      && python gateway.py")
    print()
    print("  ✅ Frontend mein sirf ek URL:")
    print("    http://localhost:8000")
    print("="*60 + "\n")
    app.run(debug=True, port=8000)
