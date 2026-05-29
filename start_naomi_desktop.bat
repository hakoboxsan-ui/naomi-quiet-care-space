@echo off
setlocal

set "PROJECT_DIR=D:\NAOMI_Project"
set "APP_PATH=frontend\streamlit_app.py"
set "PORT=8507"
set "URL=http://localhost:%PORT%"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\start_naomi_desktop.log"
set "STREAMLIT_LOG_FILE=%LOG_DIR%\streamlit_%PORT%.log"

title NAOMI Desktop Launcher

echo ========================================
echo  NAOMI Desktop Launcher
echo ========================================
echo.

cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo [ERROR] Project directory was not found: %PROJECT_DIR%
    echo Please check that NAOMI is located at D:\NAOMI_Project.
    pause
    exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
echo.>> "%LOG_FILE%"
echo [%date% %time%] Starting NAOMI desktop launcher.>> "%LOG_FILE%"

if not exist "%APP_PATH%" (
    echo [ERROR] Streamlit app was not found: %PROJECT_DIR%\%APP_PATH%
    echo Please check that frontend\streamlit_app.py exists.
    echo [%date% %time%] ERROR: App file missing.>> "%LOG_FILE%"
    pause
    exit /b 1
)

set "PYTHON_EXE="
if exist "%PROJECT_DIR%\venv\Scripts\python.exe" set "PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe"
if not defined PYTHON_EXE (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python was not found.
        echo Install Python, or create a virtual environment at %PROJECT_DIR%\venv.
        echo Example:
        echo   py -m venv venv
        echo   venv\Scripts\pip install -r requirements.txt
        echo [%date% %time%] ERROR: Python not found.>> "%LOG_FILE%"
        pause
        exit /b 1
    )
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m streamlit --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Streamlit was not found for this Python:
    echo   %PYTHON_EXE%
    echo Install dependencies with:
    echo   "%PYTHON_EXE%" -m pip install -r requirements.txt
    echo [%date% %time%] ERROR: Streamlit not found for %PYTHON_EXE%.>> "%LOG_FILE%"
    pause
    exit /b 1
)

set "PORT_STATUS=FREE"
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 set "PORT_STATUS=BUSY"

if "%PORT_STATUS%"=="BUSY" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%URL%/_stcore/health' -TimeoutSec 3; if ($r.StatusCode -eq 200 -and $r.Content -match 'ok') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
    if errorlevel 1 goto PORT_BUSY
    echo NAOMI is already running on %URL%.
    echo Opening browser without starting another Streamlit process...
    echo [%date% %time%] Existing Streamlit service detected on port %PORT%; opening browser only.>> "%LOG_FILE%"
    start "" "%URL%"
    exit /b 0
)

:PORT_BUSY
if "%PORT_STATUS%"=="BUSY" (
    echo [ERROR] Port %PORT% is already in use by another process.
    echo The service on %URL% did not respond like a Streamlit app.
    echo Close the process using port %PORT%, then run this launcher again.
    echo [%date% %time%] ERROR: Port %PORT% busy with a non-Streamlit service.>> "%LOG_FILE%"
    pause
    exit /b 1
)

echo Starting NAOMI on %URL%
echo Launcher log: %LOG_FILE%
echo Streamlit log: %STREAMLIT_LOG_FILE%
echo.
echo The browser will open automatically. Keep this window open while using NAOMI.
echo Press Ctrl+C in this window to stop NAOMI.
echo.
echo [%date% %time%] Launching Streamlit on port %PORT%.>> "%LOG_FILE%"

start "" "%URL%"
"%PYTHON_EXE%" -m streamlit run "%APP_PATH%" --server.port %PORT% --server.headless false --browser.serverAddress localhost >> "%STREAMLIT_LOG_FILE%" 2>&1

echo.
echo [ERROR] NAOMI stopped or failed to start.
echo Please check the log files:
echo   %LOG_FILE%
echo   %STREAMLIT_LOG_FILE%
echo [%date% %time%] Streamlit process exited with code %ERRORLEVEL%.>> "%LOG_FILE%"
pause
exit /b %ERRORLEVEL%
