@echo off
setlocal EnableExtensions DisableDelayedExpansion
title AI Course Studio - Startup Diagnostics
cd /d "%~dp0"
echo Running diagnostics for the secured Studio launcher...
where py.exe >nul 2>nul
if not errorlevel 1 goto use_py
where python.exe >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3 was not found.
pause
exit /b 10
:use_py
py -3 launcher.py --diagnose
goto done
:use_python
python launcher.py --diagnose
:done
echo.
echo Diagnostics finished.
pause
