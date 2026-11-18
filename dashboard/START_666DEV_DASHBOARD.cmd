@echo off
setlocal
pushd "%~dp0.." || exit /b 1

where git.exe >nul 2>&1
if errorlevel 1 goto missing_git
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto missing_checkout

set "PYTHONPATH=%CD%\src"
py.exe -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if not errorlevel 1 goto start_with_launcher
python.exe -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto missing_python
python.exe -m devhub.cli dashboard
goto finished

:start_with_launcher
py.exe -3 -m devhub.cli dashboard
goto finished

:missing_git
echo Git for Windows ist erforderlich. Stellen Sie sicher, dass git.exe im PATH liegt.
goto failed

:missing_checkout
echo Starten Sie diese Datei aus einem lokalen Git-Checkout von 666DEV.
goto failed

:missing_python
echo Python 3.11 oder neuer ist erforderlich.
goto failed

:finished
set "DASHBOARD_EXIT=%ERRORLEVEL%"
if not "%DASHBOARD_EXIT%"=="0" (
    echo Dashboard beendet mit Fehlercode %DASHBOARD_EXIT%.
    pause
)
popd
exit /b %DASHBOARD_EXIT%

:failed
pause
popd
exit /b 1
