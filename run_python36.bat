@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHON36=C:\Users\86198\anaconda3\envs\myEnvironment\python.exe"
if not exist "%PYTHON36%" set "PYTHON36=C:\Users\86198\AppData\Local\Programs\Python\Python36\python.exe"
if not exist "%PYTHON36%" (
    echo Python 3.6 was not found. See README.md for interpreter setup.
    pause
    exit /b 1
)
"%PYTHON36%" -c "import sys; print('Interpreter:', sys.executable); print('Python:', sys.version); sys.exit(0 if sys.version_info[:2] == (3, 6) else 1)"
if errorlevel 1 (
    echo This launcher requires Python 3.6.
    pause
    exit /b 1
)
pushd "%~dp0"
"%PYTHON36%" main.py %*
set "RUN_RESULT=%ERRORLEVEL%"
echo.
echo Report: %~dp0outputs\report.html
popd
pause
exit /b %RUN_RESULT%
