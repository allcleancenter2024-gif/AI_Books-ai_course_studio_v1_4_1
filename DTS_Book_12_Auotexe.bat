@echo off
setlocal EnableExtensions DisableDelayedExpansion
title DTS Book 12 - AI Course Studio v1.24.0

rem Use ASCII-only output for CMD compatibility on all Korean Windows code pages.
cd /d "%~dp0" || (
  echo [ERROR] Cannot open the program folder.
  echo Put this file in the AI Course Studio folder and run it again.
  pause
  exit /b 20
)

echo.
echo ============================================================
echo   DTS Book 12 - AI Course Studio Launcher v1.24.0
echo ============================================================
echo [INFO] Starting the current secured Studio launcher.
echo [INFO] HWPX, PPTX, and PDF export support is included.
echo [INFO] Your default browser opens when Studio is ready; sign in on the opening screen.
echo.

call "%~dp0run_windows.bat"
set "DTS_EXIT=%errorlevel%"
goto finished

:finished
if "%DTS_EXIT%"=="0" exit /b 0

echo.
echo [ERROR] Studio did not start. Check these logs for details:
echo        logs\startup_error.log
echo        logs\server_stderr.log
echo [HELP] Check your internet connection, Python version, and whether another app uses port 8765.
pause
exit /b %DTS_EXIT%
