@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm --clean --windowed --name FreeDomainServer --collect-all requests --paths . launcher.py
echo.
echo Build finished. Your app is in dist\FreeDomainServer\FreeDomainServer.exe
pause
