#!/usr/bin/env bash
set -u

# ==============================================================================
#  stop.sh - One-click shutdown for ChatUI (macOS / Linux)
#
#  Stops only the backend (FastAPI, port 8000) and frontend (Vite, port
#  5173) processes belonging to THIS project. Identifies them by the PID
#  recorded at startup AND by verifying the process's own command line
#  references this project folder (or uvicorn/vite) before touching it, so
#  unrelated Python/Node processes elsewhere on the machine are left alone.
#  Sends SIGTERM first -- letting FastAPI's shutdown handler stop llama-server
#  cleanly -- then SIGKILL only if the process is still alive after a short
#  grace period. Does not close the browser.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

BACKEND_DIR="$SCRIPT_DIR/chatui-backend"
FRONTEND_DIR="$SCRIPT_DIR/app"
BACKEND_PORT="8000"
FRONTEND_PORT="5173"

LOG="$SCRIPT_DIR/chatui-start.log"
BACKEND_PID_FILE="$SCRIPT_DIR/.chatui-backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/.chatui-frontend.pid"

log() {
  printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG"
  echo "$1"
}

{
  echo "=============================================="
  echo "ChatUI shutdown - $(date)"
  echo "=============================================="
} >> "$LOG"

echo "================================================"
echo " ChatUI - stopping..."
echo "================================================"
echo ""

pids_on_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null
  fi
}

process_matches_project() {
  local pid="$1"
  local project_dir="$2"
  local label="$3"
  local cmd
  cmd=$(ps -p "$pid" -o command= -ww 2>/dev/null)
  [ -n "$cmd" ] || cmd=$(ps -p "$pid" -o command= 2>/dev/null)
  [ -n "$cmd" ] || return 1

  local cmd_lower
  cmd_lower=$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')
  local proj_lower
  proj_lower=$(printf '%s' "$project_dir" | tr '[:upper:]' '[:lower:]')

  if printf '%s' "$cmd_lower" | grep -qF "$proj_lower"; then
    return 0
  fi
  if [ "$label" = "backend" ] && printf '%s' "$cmd_lower" | grep -q "uvicorn"; then
    return 0
  fi
  if [ "$label" = "frontend" ] && printf '%s' "$cmd_lower" | grep -q "vite"; then
    return 0
  fi
  return 1
}

stop_one() {
  local pid_file="$1"
  local project_dir="$2"
  local port="$3"
  local label="$4"

  local candidates=""
  if [ -f "$pid_file" ]; then
    local stored_pid
    stored_pid=$(tr -d '[:space:]' < "$pid_file" 2>/dev/null)
    if [ -n "$stored_pid" ]; then
      candidates="$stored_pid"
    fi
  fi

  local port_pids
  port_pids=$(pids_on_port "$port")
  for p in $port_pids; do
    case " $candidates " in
      *" $p "*) ;;
      *) candidates="$candidates $p" ;;
    esac
  done

  local any_stopped=0
  for pid in $candidates; do
    [ -n "$pid" ] || continue
    if ! kill -0 "$pid" 2>/dev/null; then
      continue
    fi
    if ! process_matches_project "$pid" "$project_dir" "$label"; then
      log "Skipped pid=$pid for $label - command line did not match this project."
      continue
    fi

    log "Stopping $label pid=$pid"
    kill -TERM "$pid" 2>/dev/null
    local waited=0
    while [ "$waited" -lt 6 ]; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
      waited=$((waited + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      log "Force-stopping $label pid=$pid"
      kill -KILL "$pid" 2>/dev/null
    fi
    any_stopped=1
  done

  if [ "$any_stopped" = "0" ]; then
    log "No running $label process found for this project (pid file / port $port)."
  fi

  rm -f "$pid_file"
}

echo "Stopping backend..."
stop_one "$BACKEND_PID_FILE" "$BACKEND_DIR" "$BACKEND_PORT" "backend"

echo "Stopping frontend..."
stop_one "$FRONTEND_PID_FILE" "$FRONTEND_DIR" "$FRONTEND_PORT" "frontend"

echo ""
echo "================================================"
echo " Done. ChatUI backend and frontend have been stopped, if they were running."
echo " Full log: $LOG"
echo "================================================"
exit 0
