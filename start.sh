#!/usr/bin/env bash
# Launcher for ZebraTur SHS
# Usage: ./start.sh

set -e
cd "$(dirname "$0")"

if [ -f ".env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs)
fi

# Ensure dependencies
python3 -c "import flask, requests" 2>/dev/null || {
  echo "→ Instalez dependențele Python..."
  python3 -m pip install --user flask requests
}

PORT="${PORT:-5050}"
HOST="${HOST:-127.0.0.1}"

echo ""
echo "  🦓 ZebraTur SHS Integration"
echo "  ─────────────────────────────"
echo "  Acces local:  http://${HOST}:${PORT}"
echo "  DB:           data/zebra.db"
echo "  Logs:         stdout"
echo ""

exec python3 app.py
