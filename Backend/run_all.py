# ================================================================
#  PromptLab - Unified Backend Launcher
#
#  Run:  python run_all.py
#  Starts all four services:
#    [LAIBA]  Laiba/app.py  -> http://localhost:5000
#    [AREEBA] Areeba/app.py -> http://localhost:5001
#    [FATIMA] Fatima/app.py -> http://localhost:5002
#    [RABIA]  Rabia/app.py  -> http://localhost:5003
# ================================================================

import os
import signal
import subprocess
import sys
import threading

BASE = os.path.dirname(os.path.abspath(__file__))


def _find_python() -> str:
    candidates = [
        os.path.join(BASE, "venv", "Scripts", "python.exe"),
        os.path.join(BASE, "venv", "bin", "python"),
        os.path.join(BASE, ".venv", "Scripts", "python.exe"),
        os.path.join(BASE, ".venv", "bin", "python"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return sys.executable


PYTHON = _find_python()


def _build_env() -> dict:
    """Merge project .env files so every service gets shared variables."""
    merged = os.environ.copy()

    env_files = [
        os.path.join(BASE, ".env"),
        os.path.join(BASE, "Fatima", ".env"),
        os.path.join(BASE, "Areeba", ".env"),
        os.path.join(BASE, "Rabia", ".env"),
        os.path.join(BASE, "Laiba", ".env"),
    ]

    for path in env_files:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                merged.setdefault(key, value)

    return merged


ENV = _build_env()

SERVICES = [
    {
        "name": "LAIBA",
        "script": os.path.join(BASE, "Laiba", "app.py"),
        "cwd": os.path.join(BASE, "Laiba"),
    },
    {
        "name": "AREEBA",
        "script": os.path.join(BASE, "Areeba", "app.py"),
        "cwd": os.path.join(BASE, "Areeba"),
    },
    {
        "name": "FATIMA",
        "script": os.path.join(BASE, "Fatima", "app.py"),
        "cwd": os.path.join(BASE, "Fatima"),
    },
    {
        "name": "RABIA",
        "script": os.path.join(BASE, "Rabia", "app.py"),
        "cwd": os.path.join(BASE, "Rabia"),
    },
]

_processes: list[subprocess.Popen] = []
_lock = threading.Lock()


def _prefix_stream(stream, label: str, is_err: bool = False) -> None:
    colour = "\033[91m" if is_err else "\033[0m"
    reset = "\033[0m"
    try:
        for raw in stream:
            line = raw.rstrip("\n").rstrip("\r\n")
            if line.strip():
                print(f"[{label}] {colour}{line}{reset}", flush=True)
    except Exception:
        pass


def _launch(service: dict) -> subprocess.Popen | None:
    name = service["name"]
    script = service["script"]
    cwd = service["cwd"]

    if not os.path.isfile(script):
        print(f"[{name}] ERROR: {script} not found - skipping.", flush=True)
        return None

    try:
        proc = subprocess.Popen(
            [PYTHON, script],
            cwd=cwd,
            env=ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=_prefix_stream, args=(proc.stdout, name, False), daemon=True).start()
        threading.Thread(target=_prefix_stream, args=(proc.stderr, name, True), daemon=True).start()
        print(f"[{name}] Started (PID {proc.pid})", flush=True)
        return proc
    except Exception as exc:
        print(f"[{name}] ERROR: Failed to start - {exc}", flush=True)
        return None


def _shutdown(signum=None, frame=None) -> None:
    print("\n[RUNNER] Shutting down all services...", flush=True)
    with _lock:
        for proc in _processes:
            if proc and proc.poll() is None:
                proc.terminate()
        for proc in _processes:
            if proc and proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    print("[RUNNER] All services stopped.", flush=True)
    sys.exit(0)


def _watch(proc: subprocess.Popen, name: str) -> None:
    code = proc.wait()
    if code != 0:
        print(f"[{name}] Exited with code {code}.", flush=True)


def main() -> None:
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("=" * 60, flush=True)
    print("  PromptLab - Starting all backend services", flush=True)
    print(f"  Python: {PYTHON}", flush=True)
    has_grok_key = any(
        key.startswith("GROK_API_KEY_") and value.strip()
        for key, value in ENV.items()
    ) or bool((ENV.get("GROK_API_KEY") or ENV.get("GROQ_API_KEY") or "").strip())
    if not has_grok_key:
        print("  WARNING: No Grok API keys found in any .env file.", flush=True)
        print("  Add them to Backend/.env:  GROK_API_KEY_1=your_key_here", flush=True)
    print("=" * 60, flush=True)

    for service in SERVICES:
        proc = _launch(service)
        if proc:
            with _lock:
                _processes.append(proc)
            threading.Thread(target=_watch, args=(proc, service["name"]), daemon=True).start()

    print("=" * 60, flush=True)
    print("  [LAIBA]  http://localhost:5000", flush=True)
    print("  [AREEBA] http://localhost:5001", flush=True)
    print("  [FATIMA] http://localhost:5002", flush=True)
    print("  [RABIA]  http://localhost:5003", flush=True)
    print("  Press Ctrl+C to stop all services.", flush=True)
    print("=" * 60, flush=True)

    try:
        for proc in list(_processes):
            proc.wait()
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
