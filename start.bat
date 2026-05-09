@echo off
REM EvoTrade dev runner for Windows
REM PAPER TRADING ONLY — no real money involved

echo === EvoTrade Dev Server ===

REM ── Backend ──────────────────────────────────────────────────────────────
echo [1/4] Setting up Python virtual environment...
cd /d "%~dp0backend"

if not exist "venv" (
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [2/4] Installing backend dependencies...
pip install -q -r requirements.txt

if not exist "models" mkdir models

echo [3/4] Starting backend on http://localhost:8000 ...
start "EvoTrade Backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM ── Frontend ─────────────────────────────────────────────────────────────
cd /d "%~dp0frontend"

echo [4/4] Installing frontend dependencies...
if not exist "node_modules" (
    npm install
)

echo Starting frontend on http://localhost:5173 ...
start "EvoTrade Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo  EvoTrade is starting up!
echo  Frontend  ^>  http://localhost:5173
echo  Backend   ^>  http://localhost:8000
echo  API docs  ^>  http://localhost:8000/docs
echo ========================================
echo.
echo Close the two terminal windows to stop servers.
pause
