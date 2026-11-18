@echo off
setlocal EnableExtensions DisableDelayedExpansion
pushd "%~dp0" || exit /b 1

set "result=0"
set "interactive="
if not "%~2"=="" goto usage_error
if "%~1"=="" goto menu
if /i "%~1"=="--run" goto run
if /i "%~1"=="--check" goto check
if /i "%~1"=="--diagnose" goto diagnose
if /i "%~1"=="--headless" goto headless
if /i "%~1"=="--help" goto usage
goto usage_error

:menu
set "interactive=1"
echo 666DEV Windows Control ^| 666SOUNDsDESIGn - FRAGGLEPOWER666
echo.
echo   [1] Start 666DEV
echo   [2] Check portable installation
echo   [3] Write diagnostic log
echo   [Q] Quit
choice /n /c 123Q /m "Select: "
set "selection=%ERRORLEVEL%"
if "%selection%"=="1" goto run
if "%selection%"=="2" goto check
if "%selection%"=="3" goto diagnose
if not "%selection%"=="4" set "result=%selection%"
set "interactive="
goto finish

:run
if not exist ".\666DEV.exe" goto missing_exe
".\666DEV.exe"
set "result=%ERRORLEVEL%"
goto finish

:check
if not exist ".\666DEV.exe" goto missing_exe
".\666DEV.exe" --check
set "result=%ERRORLEVEL%"
goto finish

:headless
if not exist ".\666DEV.exe" goto missing_exe
".\666DEV.exe" --no-window --port 0
set "result=%ERRORLEVEL%"
goto finish

:diagnose
if not exist ".\666DEV.exe" goto missing_exe
set "log_dir=checkout\.work\windows-app\logs"
if not exist "%log_dir%\." mkdir "%log_dir%"
if not exist "%log_dir%\." goto log_error
set "log_file=%log_dir%\diagnose-%RANDOM%-%RANDOM%.log"
(
    echo 666DEV Windows Control portable diagnostic
    echo Started: %DATE% %TIME%
    ".\666DEV.exe" --check
) > "%log_file%" 2>&1
set "result=%ERRORLEVEL%"
if not exist "%log_file%" goto log_error
type "%log_file%"
echo Diagnostic log: "%CD%\%log_file%"
goto finish

:missing_exe
>&2 echo 666DEV.exe is missing. Extract the entire ZIP before starting.
set "result=1"
goto finish

:log_error
>&2 echo Could not write the diagnostic log.
set "result=1"
goto finish

:usage_error
set "result=2"
:usage
echo Usage: STARTEN.bat [--run ^| --check ^| --diagnose ^| --headless ^| --help]
goto finish

:finish
if defined interactive pause
popd
endlocal & exit /b %result%
