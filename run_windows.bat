@echo off
setlocal EnableExtensions DisableDelayedExpansion
title AI Course Studio v1.29.0 - Secure Launcher
cd /d "%~dp0"
echo AI Course Studio v1.29.0
echo Starting Studio. Keep this window open while using the program.
echo.
where py.exe >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0launcher.py"
  goto :finished
)
where python.exe >nul 2>&1
if not errorlevel 1 (
  python "%~dp0launcher.py"
  goto :finished
)
echo ERROR: Python 3 was not found.
set "STUDIO_EXIT=10"
goto :pause_and_exit
:finished
set "STUDIO_EXIT=%errorlevel%"
:pause_and_exit
echo.
echo Studio launcher stopped. Press any key to close this window.
pause >nul
exit /b %STUDIO_EXIT%
