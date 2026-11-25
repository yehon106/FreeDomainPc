@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
py -3 -m freedomain.app
if errorlevel 1 pause
