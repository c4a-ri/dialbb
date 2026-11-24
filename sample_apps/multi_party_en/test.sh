#!/bin/sh
# Run from any directory. Hub output goes to this terminal and the log directory.
set -eu
SAMPLE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SAMPLE_DIR/../.." && pwd)
cd "$ROOT"
PORT=5000
MAX_TURNS=30
ALL_BOTS=0
CLI=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --all-bots) ALL_BOTS=1; shift ;;
        --cli) CLI=1; shift ;;
        --port)
            [ "$#" -ge 2 ] || { echo "--port requires a value." >&2; exit 2; }
            PORT=$2
            shift 2 ;;
        --max-turns)
            [ "$#" -ge 2 ] || { echo "--max-turns requires a value." >&2; exit 2; }
            MAX_TURNS=$2
            shift 2 ;;
        --help|-h)
            echo "Usage: sh test.sh [--all-bots] [--cli] [--port PORT] [--max-turns MAX_TURNS]"
            echo "Default: two DialBB participants and one human GUI participant."
            echo "--max-turns defaults to 30."
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
case "$PORT" in
    ''|0*|*[!0-9]*|??????*) echo "Invalid port: $PORT" >&2; exit 2 ;;
esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || { echo "Invalid port: $PORT" >&2; exit 2; }
case "$MAX_TURNS" in
    ''|0*|*[!0-9]*) echo "--max-turns requires a positive integer without leading zeros." >&2; exit 2 ;;
esac
if [ -z "${DIALBB_PYTHON:-}" ]; then
    if [ -x "$ROOT/.venv/bin/python" ]; then
        DIALBB_PYTHON="$ROOT/.venv/bin/python"
    else
        DIALBB_PYTHON=python3
    fi
fi
command -v "$DIALBB_PYTHON" >/dev/null 2>&1 || { echo "Python executable not found: $DIALBB_PYTHON" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required to check hub readiness." >&2; exit 1; }
export PYTHONUTF8=1
HUB_URL="http://localhost:$PORT"
PROBE_URL="$HUB_URL/socket.io/?EIO=4&transport=polling"
if curl --silent --output /dev/null --connect-timeout 1 --max-time 1 "$HUB_URL/"; then
    echo "Port $PORT is already in use; choose another --port." >&2
    exit 1
fi
LOG_DIR=$(mktemp -d "${TMPDIR:-/tmp}/dialbb-multi_party_en.XXXXXX")
echo "Logs: $LOG_DIR"
HUB_OUTPUT="$LOG_DIR/hub-output"
mkfifo "$HUB_OUTPUT"
PIDS=""
LOG_PID=""
HUB_READY=0
cleanup() {
    trap - EXIT
    trap '' HUP INT TERM
    for pid in $PIDS; do kill "$pid" 2>/dev/null || :; done
    if [ -n "$LOG_PID" ] && [ "$HUB_READY" -eq 0 ]; then
        kill "$LOG_PID" 2>/dev/null || :
    fi
    for pid in $PIDS; do wait "$pid" 2>/dev/null || :; done
    if [ -n "$LOG_PID" ]; then
        wait "$LOG_PID" 2>/dev/null || :
    fi
    rm -f "$HUB_OUTPUT"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
tee "$LOG_DIR/hub.log" <"$HUB_OUTPUT" &
LOG_PID=$!
PYTHONUNBUFFERED=1 "$DIALBB_PYTHON" -m dialbb.lib.multi_party.hub --port "$PORT" --max-turns "$MAX_TURNS" >"$HUB_OUTPUT" 2>&1 &
HUB_PID=$!
PIDS="$HUB_PID"
ATTEMPTS=0
until curl --fail --silent --output /dev/null --connect-timeout 1 --max-time 1 "$PROBE_URL"; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if ! kill -0 "$HUB_PID" 2>/dev/null || [ "$ATTEMPTS" -ge 15 ]; then
        echo "Hub did not start; check $LOG_DIR/hub.log" >&2
        exit 1
    fi
    sleep 1
done
HUB_READY=1
"$DIALBB_PYTHON" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config1.yml John --hub-url "$HUB_URL" >"$LOG_DIR/John.log" 2>&1 &
PIDS="$PIDS $!"
"$DIALBB_PYTHON" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config2.yml Paul --hub-url "$HUB_URL" >"$LOG_DIR/Paul.log" 2>&1 &
PIDS="$PIDS $!"
if [ "$ALL_BOTS" -eq 1 ]; then
    "$DIALBB_PYTHON" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config3.yml Lisa --hub-url "$HUB_URL" >"$LOG_DIR/Lisa.log" 2>&1 &
    PIDS="$PIDS $!"
    echo "All three bots are running. The conversation ends after $MAX_TURNS utterances. Press Ctrl+C to stop early."
    wait "$HUB_PID"
else
    if [ "$CLI" -eq 1 ]; then
        HUMAN_MODULE=dialbb.lib.multi_party.user_spoke
    else
        HUMAN_MODULE=dialbb.lib.multi_party.user_spoke_gui
    fi
    # POSIX shells give asynchronous commands /dev/null unless we pass stdin explicitly.
    exec 3<&0
    "$DIALBB_PYTHON" -m "$HUMAN_MODULE" Lisa --hub-url "$HUB_URL" <&3 3<&- &
    HUMAN_PID=$!
    exec 3<&-
    PIDS="$PIDS $HUMAN_PID"
    while kill -0 "$HUB_PID" 2>/dev/null && kill -0 "$HUMAN_PID" 2>/dev/null; do
        sleep 1
    done
    if kill -0 "$HUB_PID" 2>/dev/null; then
        wait "$HUMAN_PID"
    else
        wait "$HUB_PID"
    fi
fi
