@echo off
cd /d %~dp0
echo STARTING OPENCLAW SUITE...
start "TRADING ENGINE" cmd /c RUN_ENGINE.bat
start "MARKET WATCHER" cmd /c RUN_WATCHER.bat
start "AI SCHEDULER" cmd /c RUN_SCHEDULER.bat
echo Full suite is starting in separate windows.
pause
