@echo off
REM =============================================================================
REM A3-Agent v7.1.0 — Windows PyInstaller Build Script
REM =============================================================================
REM Requires: pyinstaller, Python 3.10+, all deps from requirements.txt installed
REM
REM Usage:
REM   desktop\build.bat
REM
REM Output: dist\A3-Agent\A3-Agent.exe
REM =============================================================================

echo ============================================
echo   A3-Agent v7.1.0 — PyInstaller Build
echo ============================================
echo.

REM ── Clean previous build ──────────────────────
if exist "dist\A3-Agent" rmdir /s /q "dist\A3-Agent"
if exist "build\A3-Agent" rmdir /s /q "build\A3-Agent"

REM ── PyInstaller build ─────────────────────────
pyinstaller --onedir --name A3-Agent --clean --noconfirm ^
  --add-data "app.py;." ^
  --add-data "src;src" ^
  --add-data "web;web" ^
  --add-data "utils;utils" ^
  --add-data "knowledge_base;knowledge_base" ^
  --add-data "storage/a3.db;storage" ^
  --add-data "demo/fixtures;demo/fixtures" ^
  --add-data ".streamlit/config.toml;.streamlit" ^
  --add-data ".env.example;." ^
  --add-data "LICENSE;." ^
  --hidden-import fastapi ^
  --hidden-import uvicorn ^
  --hidden-import streamlit ^
  --hidden-import veritas ^
  --hidden-import veritas.llm ^
  --hidden-import veritas.llm.factory ^
  --hidden-import veritas.llm.provider ^
  --hidden-import veritas.llm.mock_provider ^
  --hidden-import veritas.llm.deepseek_provider ^
  --hidden-import veritas.llm.openai_provider ^
  --hidden-import veritas.llm.xunfei_provider ^
  --hidden-import veritas.llm.rule_provider ^
  --hidden-import veritas.memory ^
  --hidden-import veritas.runtime ^
  --hidden-import keyring ^
  --hidden-import keyring.backend ^
  --hidden-import keyring.backends ^
  --hidden-import keyring.errors ^
  --hidden-import keyring.credentials ^
  --hidden-import SecretStorage ^
  --hidden-import jeepney ^
  --hidden-import jaraco.classes ^
  --hidden-import jaraco.functools ^
  --collect-all fastapi ^
  --collect-all uvicorn ^
  --collect-all streamlit ^
  --collect-all veritas ^
  --exclude-module pyarrow ^
  --exclude-module scipy ^
  --exclude-module pytest ^
  --exclude-module matplotlib ^
  --exclude-module tkinter ^
  --runtime-hook desktop/hooks/runtime_hook.py ^
  desktop/launcher.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================
    echo   BUILD FAILED — see output above
    echo ============================================
    exit /b 1
)

echo.
echo ============================================
echo   BUILD SUCCESS
echo   Output: dist\A3-Agent\A3-Agent.exe
echo ============================================
echo.
echo Size:
dir dist\A3-Agent /s 2>nul | findstr /C:"File(s)" >nul 2>&1 && dir dist\A3-Agent /s | findstr /C:"File(s)"
echo.
echo To test: dist\A3-Agent\A3-Agent.exe
