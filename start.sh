#!/usr/bin/env bash
set -u

# ==============================================================================
#  start.sh - One-click launcher for ChatUI (macOS / Linux)
#
#  Starts the FastAPI backend (chatui-backend, port 8000), waits for it to
#  report healthy, starts the Vite frontend (app, port 5173) directly via its
#  local vite binary rather than through npm (so its PID is the real
#  dev-server process and can be stopped cleanly by stop.sh), waits for it to
#  respond, then opens the browser. Mirrors START.bat's behavior and ports.
#
#  Both server processes are started with `exec` inside a subshell so their
#  PID is the real process PID (not a wrapper's), and are `disown`ed so they
#  keep running after this script exits. Real SIGTERM handling on Unix means
#  stop.sh can shut the backend down gracefully (letting FastAPI's shutdown
#  hook stop llama-server) far more reliably than is possible on Windows.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

BACKEND_DIR="$SCRIPT_DIR/chatui-backend"
FRONTEND_DIR="$SCRIPT_DIR/app"
VENV_DIR="$BACKEND_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_PORT="5173"

LOG="$SCRIPT_DIR/chatui-start.log"
BACKEND_OUT="$SCRIPT_DIR/chatui-backend-output.log"
BACKEND_ERR="$SCRIPT_DIR/chatui-backend-error.log"
FRONTEND_OUT="$SCRIPT_DIR/chatui-frontend-output.log"
FRONTEND_ERR="$SCRIPT_DIR/chatui-frontend-error.log"
BACKEND_PID_FILE="$SCRIPT_DIR/.chatui-backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/.chatui-frontend.pid"

log() {
  printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG"
}

fail() {
  echo ""
  echo "================================================"
  echo " [FAILED] $1"
  echo "================================================"
  if [ -f "$BACKEND_ERR" ]; then
    echo ""
    echo "--- last lines of $BACKEND_ERR ---"
    tail -n 15 "$BACKEND_ERR"
  fi
  if [ -f "$FRONTEND_ERR" ]; then
    echo ""
    echo "--- last lines of $FRONTEND_ERR ---"
    tail -n 15 "$FRONTEND_ERR"
  fi
  echo ""
  echo "Full log: $LOG"
  exit 1
}

port_in_use() {
  ( exec 3<>"/dev/tcp/127.0.0.1/$1" ) 2>/dev/null
  local result=$?
  exec 3>&- 2>/dev/null
  exec 3<&- 2>/dev/null
  return $result
}

# Returns 0 = ready, 1 = timed out, 2 = the process exited before becoming ready
wait_for_http() {
  local url="$1"
  local timeout_seconds="$2"
  local pid_to_check="$3"
  local deadline=$((SECONDS + timeout_seconds))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if [ -n "$pid_to_check" ] && ! kill -0 "$pid_to_check" 2>/dev/null; then
      return 2
    fi
    if curl -s -o /dev/null -m 2 -w '%{http_code}' "$url" 2>/dev/null | grep -q '^200$'; then
      return 0
    fi
    sleep 0.75
  done
  return 1
}

open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 &
  elif command -v wslview >/dev/null 2>&1; then
    wslview "$url" >/dev/null 2>&1
  else
    echo "Could not detect how to open a browser automatically. Please open $url manually."
  fi
}

{
  echo "=============================================="
  echo "ChatUI startup - $(date)"
  echo "Root: $SCRIPT_DIR"
  echo "=============================================="
} >> "$LOG"

echo "================================================"
echo " ChatUI - starting..."
echo " Project root: $SCRIPT_DIR"
echo " Full log:     $LOG"
echo "================================================"
echo ""

# ------------------------------------------------------------------------
# 1. Sanity checks
# ------------------------------------------------------------------------
[ -f "$BACKEND_DIR/main.py" ] || fail "Could not find chatui-backend/main.py under $BACKEND_DIR. Is start.sh in the project root, next to the app and chatui-backend folders?"
[ -f "$FRONTEND_DIR/package.json" ] || fail "Could not find app/package.json under $FRONTEND_DIR. Is start.sh in the project root, next to the app and chatui-backend folders?"
echo "[1/6] Project folders found."

echo "[2/6] Checking for Python..."
PY_LAUNCHER=""
if command -v python3 >/dev/null 2>&1; then
  PY_LAUNCHER="python3"
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q "Python 3"; then
  PY_LAUNCHER="python"
fi
[ -n "$PY_LAUNCHER" ] || fail "Python 3 was not found (checked python3 and python). Install Python 3, then try again."
echo "      Using: $PY_LAUNCHER"

echo "[2/6] Checking for Node.js / npm..."
command -v npm >/dev/null 2>&1 || fail "npm was not found. Install Node.js from nodejs.org, then try again."
command -v curl >/dev/null 2>&1 || fail "curl was not found. Install curl, then try again."

# ------------------------------------------------------------------------
# 1b. Fail fast if the ports are already taken by something else
# ------------------------------------------------------------------------
if port_in_use "$BACKEND_PORT"; then
  fail "Port $BACKEND_PORT is already in use by another program. Close whatever is using it, or run ./stop.sh first, then try again."
fi
if port_in_use "$FRONTEND_PORT"; then
  fail "Port $FRONTEND_PORT is already in use by another program. Close whatever is using it, or run ./stop.sh first, then try again."
fi

# ------------------------------------------------------------------------
# 2. First-run backend environment setup (venv + requirements)
# ------------------------------------------------------------------------
if [ ! -x "$VENV_PY" ]; then
  echo "[3/6] Creating backend virtual environment (first run only, please wait)..."
  log "Creating venv at $VENV_DIR"
  if ! "$PY_LAUNCHER" -m venv "$VENV_DIR" >> "$LOG" 2>&1; then
    fail "Failed to create the backend virtual environment. See $LOG. Your Python install may be missing the venv module."
  fi
fi
[ -x "$VENV_PY" ] || fail "Backend virtual environment still missing after creation attempt at $VENV_PY. See $LOG."

echo "[3/6] Checking backend dependencies (first run may take a minute)..."
log "pip install -r requirements.txt"
if ! "$VENV_PY" -m pip install --disable-pip-version-check -q -r "$BACKEND_DIR/requirements.txt" >> "$LOG" 2>&1; then
  fail "Failed to install backend dependencies. See $LOG."
fi

# ------------------------------------------------------------------------
# 3. First-run frontend environment setup (npm install)
#
# Checked via the vite binary actually existing, not just node_modules/
# being present -- a node_modules dir can exist but be incomplete (e.g.
# from a previously interrupted install), which a plain directory-existence
# check would wrongly treat as "already installed" and skip reinstalling.
# ------------------------------------------------------------------------
VITE_BIN="$FRONTEND_DIR/node_modules/.bin/vite"

if [ ! -x "$VITE_BIN" ]; then
  echo "[4/6] Installing frontend dependencies (first run only, may take a minute)..."
  log "npm install in $FRONTEND_DIR"
  if ! (cd "$FRONTEND_DIR" && npm install >> "$LOG" 2>&1); then
    fail "Failed to install frontend dependencies via npm install. See $LOG."
  fi
else
  echo "[4/6] Frontend dependencies already installed."
fi

[ -x "$VITE_BIN" ] || fail "Could not find vite at $VITE_BIN after npm install. See $LOG."

# ------------------------------------------------------------------------
# 4. Start backend
# ------------------------------------------------------------------------
echo "[5/6] Starting backend and frontend (this can take up to ~90 seconds on first run)..."
rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"

(
  cd "$BACKEND_DIR" || exit 1
  exec "$VENV_PY" -m uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) > "$BACKEND_OUT" 2> "$BACKEND_ERR" &
BACKEND_PID=$!
disown "$BACKEND_PID" 2>/dev/null
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
log "Backend process started, pid=$BACKEND_PID"

wait_for_http "http://$BACKEND_HOST:$BACKEND_PORT/health" 90 "$BACKEND_PID"
result=$?
if [ "$result" = "2" ]; then
  fail "Backend process exited on its own shortly after starting. See $BACKEND_ERR for the Python error."
elif [ "$result" != "0" ]; then
  fail "Backend started but never responded on http://$BACKEND_HOST:$BACKEND_PORT/health within 90 seconds. See $LOG and $BACKEND_OUT / $BACKEND_ERR."
fi
log "Backend is ready."

# ------------------------------------------------------------------------
# 5. Start frontend
# ------------------------------------------------------------------------
(
  cd "$FRONTEND_DIR" || exit 1
  exec "$VITE_BIN" --port "$FRONTEND_PORT"
) > "$FRONTEND_OUT" 2> "$FRONTEND_ERR" &
FRONTEND_PID=$!
disown "$FRONTEND_PID" 2>/dev/null
echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"
log "Frontend process started, pid=$FRONTEND_PID"

wait_for_http "http://127.0.0.1:$FRONTEND_PORT/" 60 "$FRONTEND_PID"
result=$?
if [ "$result" = "2" ]; then
  fail "Frontend process exited on its own shortly after starting. See $FRONTEND_ERR for the npm/Vite error."
elif [ "$result" != "0" ]; then
  fail "Frontend started but never responded on http://127.0.0.1:$FRONTEND_PORT/ within 60 seconds. See $LOG and $FRONTEND_OUT / $FRONTEND_ERR."
fi
log "Frontend is ready."

# ------------------------------------------------------------------------
# 6. Open browser
# ------------------------------------------------------------------------
open_url "http://127.0.0.1:$FRONTEND_PORT/"
log "Opened browser at http://127.0.0.1:$FRONTEND_PORT/"

echo "[6/6] ChatUI is running."
echo ""
echo "================================================"
echo " Backend:  http://$BACKEND_HOST:$BACKEND_PORT/health"
echo " Frontend: http://127.0.0.1:$FRONTEND_PORT/"
echo " Run ./stop.sh to shut it down."
echo "================================================"
exit 0
