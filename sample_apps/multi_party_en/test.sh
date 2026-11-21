#!/bin/sh
# Run from any directory. The hub and bots write logs; the human runs in the foreground.
set -eu
SAMPLE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SAMPLE_DIR/../.." && pwd)
cd "$ROOT"
PORT=5000
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
        --help|-h)
            echo "Usage: sh test.sh [--all-bots] [--cli] [--port PORT]"
            echo "Default: two DialBB participants and one human GUI participant."
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
case "$PORT" in
    ''|0*|*[!0-9]*|??????*) echo "Invalid port: $PORT" >&2; exit 2 ;;
esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || { echo "Invalid port: $PORT" >&2; exit 2; }
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
PIDS=""
cleanup() {
    trap - EXIT HUP INT TERM
    for pid in $PIDS; do kill "$pid" 2>/dev/null || :; done
    for pid in $PIDS; do wait "$pid" 2>/dev/null || :; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
"$DIALBB_PYTHON" -m dialbb.lib.multi_party.hub --port "$PORT" >"$LOG_DIR/hub.log" 2>&1 &
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
"$DIALBB_PYTHON" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config1.yml Tanaka --hub-url "$HUB_URL" >"$LOG_DIR/Tanaka.log" 2>&1 &
PIDS="$PIDS $!"
"$DIALBB_PYTHON" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config2.yml Suzuki --hub-url "$HUB_URL" >"$LOG_DIR/Suzuki.log" 2>&1 &
PIDS="$PIDS $!"
if [ "$ALL_BOTS" -eq 1 ]; then
    "$DIALBB_PYTHON" -m dialbb.lib.multi_party.dialbb_spoke sample_apps/multi_party_en/config3.yml Yamada --hub-url "$HUB_URL" >"$LOG_DIR/Yamada.log" 2>&1 &
    PIDS="$PIDS $!"
    echo "All three bots are running. Press Ctrl+C to stop."
    # Wait for the hub to keep the conversation running, including quiet bots.
    wait "$HUB_PID"
else
    if [ "$CLI" -eq 1 ]; then
        HUMAN_MODULE=dialbb.lib.multi_party.user_spoke
    else
        HUMAN_MODULE=dialbb.lib.multi_party.user_spoke_gui
    fi
    "$DIALBB_PYTHON" -m "$HUMAN_MODULE" Yamada --hub-url "$HUB_URL"
fi
