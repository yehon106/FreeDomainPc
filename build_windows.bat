@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found. Install Python 3.10+ and enable Add Python to PATH.
  pause
  exit /b 1
)
py -3 -m pip install --upgrade pip
if errorlevel 1 goto failed
py -3 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto failed
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name FreeDomainServer --collect-all requests --paths . launcher.py
if errorlevel 1 goto failed
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
  "C:\Program Files\Inno Setup 6\ISCC.exe" installer.iss
) else (
  echo EXE created in dist. Install Inno Setup 6 to create its installer.
)
pause
exit /b 0
:failed
echo BUILD FAILED
pause
exit /b 1
