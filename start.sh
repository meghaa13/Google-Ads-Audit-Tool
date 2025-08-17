#!/bin/bash
set -euo pipefail

# Allow override of CHROME_PATH via env var; default to /usr/bin/google-chrome
CHROME="${CHROME_PATH:-/usr/bin/google-chrome}"
USER_DATA_DIR="${USER_DATA_DIR:-/tmp/ChromeDebugProfile}"
DEBUG_PORT="${DEBUGGING_PORT:-9222}"

# Create user data dir
mkdir -p "$USER_DATA_DIR"

echo "🚀 Starting Chrome (background) at $CHROME ..."
# Start Chrome in background with container-safe flags.
# NOTE: --no-sandbox is commonly required inside containers.
"$CHROME" \
  --remote-debugging-port="$DEBUG_PORT" \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-gpu \
  --disable-dev-shm-usage \
  --disable-background-networking \
  --disable-background-timer-throttling \
  --disable-breakpad \
  --disable-client-side-phishing-detection \
  --disable-default-apps \
  --disable-extensions \
  --disable-sync \
  --metrics-recording-only \
  --no-sandbox \
  > /dev/null 2>&1 &

CHROME_PID=$!
echo "Chrome started (pid=${CHROME_PID}). Waiting 2s for it to be ready..."
sleep 2

echo "✅ Launching Gunicorn"
# Replace the shell process with gunicorn (keeps PID 1 clean)
exec gunicorn app:app --bind 0.0.0.0:10000
