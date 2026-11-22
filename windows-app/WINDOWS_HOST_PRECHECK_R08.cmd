@echo off
setlocal
if "%~1"=="" (
  echo Usage: WINDOWS_HOST_PRECHECK_R08.cmd EXPECTED_40_CHAR_COMMIT_SHA
  echo Read-only host checks. JSON report under .work\host-acceptance\
  exit /b 2
)
pushd "%~dp0.." || exit /b 2
where py.exe >nul 2>&1
if not errorlevel 1 goto pythonlauncher
where python.exe >nul 2>&1
if errorlevel 1 goto missingpython
python.exe "windows-app\HOST_ACCEPTANCE_R08.py" --expected-sha "%~1"
goto finished
:pythonlauncher
py.exe -3 "windows-app\HOST_ACCEPTANCE_R08.py" --expected-sha "%~1"
goto finished
:missingpython
echo WRITE_BLOCKED: Python 3.11 or newer required. No installation attempted.
popd
exit /b 2
:finished
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
