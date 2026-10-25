@echo off
echo =======================================================
echo   Building standalone Lumina.exe with PyInstaller
echo =======================================================

python -m pip install -r requirements-client.txt pyinstaller
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b %errorlevel%
)

python -m PyInstaller --onefile --noconsole --name Lumina --clean --hidden-import engineio.async_drivers.threading --hidden-import websocket --hidden-import requests --hidden-import urllib3 Lumina.py
if errorlevel 1 (
    echo Failed to build executable.
    pause
    exit /b %errorlevel%
)

if exist dist\Lumina.exe (
    move /y dist\Lumina.exe .\Lumina.exe
    rd /s /q dist
    rd /s /q build
    echo.
    echo =======================================================
    echo   Lumina.exe successfully built!
    echo =======================================================
)

pause
