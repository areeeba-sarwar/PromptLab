# PromptLab

AI-powered prompt engineering learning and evaluation platform for FYP-1 2026.

PromptLab helps users practice prompt writing, evaluate prompt quality, improve weak prompts, and track learning progress. The project includes authentication, learning chapters, practice sessions, prompt evaluation, prompt enhancement, chat history, and progress dashboards.

The README follows the module order used by the project team: Areeba, Fatima, Laiba, Rabia.

## Team

| Member | Responsibility |
| --- | --- |
| Areeba | User management, authentication, dashboard, reminders |
| Fatima | Learning mode, practice sessions, evaluation, final test, certificates |
| Laiba | Prompt evaluation, chat, analytics, multi-agent review |
| Rabia | Prompt enhancer, quick answers, enhancement history |

## Features

- User registration, login, logout, password reset, and session-based authentication
- Dashboard with user progress, streaks, and activity data
- Structured learning chapters and prompt-writing practice questions
- AI practice feedback with scores, strengths, weaknesses, and suggestions
- Final test and certificate flow for learning completion
- Prompt evaluation across clarity, context, specificity, constraints, and format
- Multi-agent prompt review using Critic, Optimist, and Professor perspectives
- Security scanner for prompt injection, jailbreak, and unsafe prompt patterns
- Difficulty classifier for beginner, intermediate, advanced, and expert prompts
- Chat and prompt history tracking
- Prompt mutation tools
- Prompt enhancement tools
- SQLite-backed local persistence for development

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Radix UI |
| Backend | Python, Flask, Flask-CORS |
| Database | SQLite |
| AI | Groq API, default model `llama-3.3-70b-versatile` |

## Project Structure

```text
Final-year-project-1/
  Backend/
    main.py              # Single combined backend on port 5000
    run_all.py           # Starts the four separate module backends
    gateway.py           # Gateway/proxy backend on port 8000
    requirements.txt
    Areeba/app.py        # Auth service, port 5001
    Fatima/app.py        # Learning service, port 5002
    Laiba/app.py         # Evaluation service, port 5000
    Rabia/app.py         # Enhancer service, port 5003
  Frontend/
    app/
    components/
    contexts/
    package.json
    pnpm-lock.yaml
```

## Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer
- pnpm, or npm if you prefer npm installs
- Groq API key from `https://console.groq.com`

## Environment Variables

Create `Backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Optional backend variables:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_email_app_password
AREEBA_API=http://127.0.0.1:5001
FATIMA_DB_PATH=fatima_learning.db
RABIA_DB_PATH=rabia_enhancer.db
RABIA_PORT=5003
RABIA_USE_GROQ=false
FLASK_DEBUG=false
PRACTICE_PASSING_SCORE=70
```

Create `Frontend/.env.local`:

```env
NEXT_PUBLIC_AREEBA_API=http://127.0.0.1:5001
NEXT_PUBLIC_FATIMA_API=http://127.0.0.1:5002
NEXT_PUBLIC_LAIBA_API=http://localhost:5000
NEXT_PUBLIC_RABIA_API=http://127.0.0.1:5003
```

Do not commit `.env`, `.env.local`, or database files.

## Backend Setup

```bash
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Frontend Setup

```bash
cd Frontend
pnpm install
```

If pnpm is not installed:

```bash
npm install
```

## Running The Project

The frontend currently uses separate API URLs for Areeba, Fatima, Laiba, and Rabia. For the full app experience, run the multi-service backend.

Terminal 1, backend services:

```bash
cd Backend
venv\Scripts\activate
python run_all.py
```

This starts:

| Service | URL |
| --- | --- |
| Areeba auth backend | `http://127.0.0.1:5001` |
| Fatima learning backend | `http://127.0.0.1:5002` |
| Laiba evaluation backend | `http://localhost:5000` |
| Rabia enhancer backend | `http://127.0.0.1:5003` |

Terminal 2, frontend:

```bash
cd Frontend
pnpm run dev
```

Open `http://localhost:3000`.

### Single Backend Mode

For development or API testing, the combined backend can also be run directly:

```bash
cd Backend
venv\Scripts\activate
python main.py
```

This starts a combined Flask backend on `http://localhost:5000`. Some frontend screens expect the separate services on ports 5001, 5002, and 5003, so use `run_all.py` for full frontend testing.

## API Overview

### General

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | Backend health check |

### Areeba: Authentication And Dashboard

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/areeba/register` | Register a user |
| POST | `/api/areeba/verify-registration` | Verify registration code |
| POST | `/api/areeba/resend-registration-code` | Resend verification code |
| POST | `/api/areeba/login` | Login |
| GET | `/api/areeba/me` | Current logged-in user |
| POST | `/api/areeba/logout` | Logout |
| POST | `/api/areeba/forgot-password` | Request password reset |
| POST | `/api/areeba/reset-password` | Reset password |
| GET | `/api/areeba/dashboard/me` | Current user dashboard |
| GET | `/api/areeba/dashboard/<user_id>` | Dashboard by user ID |
| GET | `/api/areeba/streak/me` | Current user streak |
| GET | `/api/areeba/history` | Current user history |

### Fatima: Learning, Practice, Evaluation and Certificate

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/fatima/health` | Learning service health check |
| GET | `/api/fatima/chapters` | List learning chapters |
| GET | `/api/fatima/chapters/<chapter_id>` | Chapter details |
| GET | `/api/fatima/chapters/<chapter_id>/questions` | Chapter questions |
| POST | `/api/fatima/practice/start` | Start practice session |
| POST | `/api/fatima/practice/<session_id>/submit` | Submit practice answer |
| POST | `/api/fatima/practice/<session_id>/change-question` | Change practice question |
| GET | `/api/fatima/practice/sessions` | Practice session list |
| GET | `/api/fatima/practice/sessions/<session_id>` | Practice session details |
| GET | `/api/fatima/progress/me` | Current user progress |
| GET | `/api/fatima/dashboard/me` | Learning dashboard |
| POST | `/api/fatima/practice-feedback` | AI practice feedback |
| GET | `/api/fatima/final-test/status` | Final test status |
| POST | `/api/fatima/final-test/start` | Start final test |
| POST | `/api/fatima/final-test/submit` | Submit final test |
| GET | `/api/fatima/certificate/me` | Current user certificate |

### Laiba: Live Evaluation And Chat

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/evaluate` | Full prompt evaluation |
| POST | `/api/suggest` | Live prompt suggestions |
| POST | `/api/multi-agent` | Multi-agent prompt review |
| POST | `/api/security` | Prompt security scan |
| POST | `/api/difficulty` | Prompt difficulty classification |
| POST | `/api/mutate` | Generate prompt variations |
| POST | `/api/domain` | Domain-specific evaluation |
| POST | `/api/chat` | Chat with AI memory |
| GET | `/api/history/<user_id>` | Prompt/chat history |
| GET | `/api/analytics/<user_id>` | User analytics |
| GET | `/api/progress/<user_id>` | Score history |
| GET | `/api/templates` | Prompt templates |
| GET | `/api/leaderboard` | Leaderboard data |
| GET | `/api/admin/stats` | Admin statistics |

### Rabia: Prompt Enhancer

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/rabia/health` | Enhancer service health check |
| GET | `/api/rabia/enhancer/history` | Enhancement history |
| GET | `/api/rabia/enhancer/sessions` | List enhancer sessions |
| POST | `/api/rabia/enhancer/sessions` | Create enhancer session |
| GET | `/api/rabia/enhancer/sessions/<session_id>` | Enhancer session details |
| DELETE | `/api/rabia/enhancer/sessions/<session_id>` | Delete enhancer session |
| POST | `/api/rabia/enhancer/enhance` | Enhance a prompt |
| POST | `/api/rabia/enhancer/sessions/<session_id>/enhance-again` | Re-enhance prompt |
| GET | `/api/rabia/enhancer/sessions/<session_id>/versions` | Prompt enhancement versions |
| GET | `/api/rabia/enhancer/sessions/<session_id>/messages` | Enhancer messages |

## Useful Commands

```bash
# Frontend development server
cd Frontend
pnpm run dev

# Frontend production build
cd Frontend
pnpm run build

# Frontend lint
cd Frontend
pnpm run lint

# Combined backend
cd Backend
python main.py

# Multi-service backend
cd Backend
python run_all.py
```

## Notes

- Backend database files are local SQLite files and are ignored by Git.
- `Backend/main.py` uses `Backend/promptlab.db`.
- The separate service apps may create their own local database files.
- If the frontend cannot load a page, confirm the matching backend service is running on the expected port.
