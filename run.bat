@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Simple bootstrap + run script for Windows (double-click friendly)
REM 1. Creates venv if missing
REM 2. Installs requirements (first time)
REM 3. Creates placeholder .env if absent
REM 4. Launches Streamlit app

IF NOT EXIST .venv (
  echo [Bootstrap] Creating virtual environment...
  py -3 -m venv .venv || (echo Failed to create venv & exit /b 1)
  echo [Bootstrap] Upgrading pip...
  .venv\Scripts\python -m pip install --upgrade pip >NUL
  echo [Bootstrap] Installing requirements...
  .venv\Scripts\python -m pip install -r requirements.txt || (echo Failed to install requirements & exit /b 1)
) ELSE (
  if "%1"=="--reinstall" (
    echo [Bootstrap] Re-installing requirements...
    .venv\Scripts\python -m pip install -r requirements.txt || (echo Failed to install requirements & exit /b 1)
  )
)

IF NOT EXIST .env (
  echo [Bootstrap] Creating .env placeholder
  (echo CANVAS_BASE_URL=https://canvas.instructure.com) > .env
  (echo CANVAS_API_TOKEN=REPLACE_WITH_YOUR_TOKEN) >> .env
  echo Edit .env and set your real Canvas token.
)

echo [Run] Starting Streamlit (Ctrl+C to stop)...
REM Updated to packaged Streamlit entrypoint
.venv\Scripts\python -m streamlit run python/canvas_agent/apps/streamlit_app.py

pause
