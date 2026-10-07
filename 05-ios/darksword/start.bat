@echo off
cd /d "%~dp0"

rem Force UTF-8 console output; server.py prints non-ASCII glyphs that
rem otherwise crash with UnicodeEncodeError on a GBK Windows console.
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found in PATH.
    pause
    exit /b 1
)

echo =======================================================
echo   DarkSword-RCE Research Server
echo =======================================================
echo.

python server.py

echo.
echo [*] Server stopped.
pause
