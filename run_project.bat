@echo off
cd /d C:\Evotrade\EvoTrade

echo.
echo Installing Python dependencies...
python -m pip install -r backend\requirements.txt -q

echo.
echo ===================================================
echo Starting EvoTrade Demo...
echo ===================================================
echo.

python scripts\run_demo.py
