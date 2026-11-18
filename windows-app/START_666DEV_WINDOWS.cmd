@echo off
setlocal
pushd "%~dp0.." || exit /b 1

where git.exe >nul 2>&1
if errorlevel 1 goto missing_git
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto missing_checkout

py.exe -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if not errorlevel 1 goto start_with_launcher
python.exe -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto missing_python
python.exe "windows-app\app.py"
goto finished

:start_with_launcher
py.exe -3 "windows-app\app.py"
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
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo 666DEV Windows Control beendet mit Fehlercode %APP_EXIT%.
    pause
)
popd
exit /b %APP_EXIT%

:failed
pause
popd
exit /b 1
