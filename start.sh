#!/bin/bash
# EvoTrade dev runner — starts backend and frontend together
# PAPER TRADING ONLY — no real money involved
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Backend ──────────────────────────────────────────────────────────────────
echo "🔧 Setting up backend..."
cd "$ROOT/backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

pip install -q -r requirements.txt

mkdir -p models

echo "🚀 Starting backend on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────────────────────────
cd "$ROOT/frontend"
echo "🔧 Setting up frontend..."

if [ ! -d "node_modules" ]; then
    npm install
fi

echo "🚀 Starting frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ EvoTrade running!"
echo "   Frontend → http://localhost:5173"
echo "   Backend  → http://localhost:8000"
echo "   API docs → http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Kill both on exit
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

wait
