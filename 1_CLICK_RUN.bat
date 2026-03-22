@echo off
echo ========================================
echo   [OPENCLAW] STARTING FULL SUITE...
echo ========================================
start "TRADING ENGINE" cmd /c RUN_ENGINE.bat
start "MARKET WATCHER" cmd /c RUN_WATCHER.bat
echo Full suite is starting in separate windows.
pause
