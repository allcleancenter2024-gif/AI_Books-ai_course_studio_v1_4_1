@echo off
setlocal EnableExtensions DisableDelayedExpansion
title AI Course Studio v1.26.0 - Secure Launcher
cd /d "%~dp0"
echo.
echo AI Course Studio v1.26.0 - secure local launcher
echo HWPX, PPTX, PDF export support enabled.
echo The browser will open after the server is ready.
echo Sign in on the Studio opening screen.
echo.
where py.exe >nul 2>nul
if not errorlevel 1 goto use_py
where python.exe >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3 was not found.
echo Install Python 3.10 or newer, then run this file again.
pause
exit /b 10
:use_py
py -3 launcher.py
goto done
:use_python
python launcher.py
:done
set code=%errorlevel%
if not %code%==0 pause
exit /b %code%
