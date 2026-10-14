@echo off
REM Crea TV_Finder.exe (serve Python 3.11+ installato SOLO su questo PC, una volta)
cd /d %~dp0app
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --add-data "..\web\catalogo.json;." --name TV_Finder tv_matcher.py
copy /Y dist\TV_Finder.exe ..\TV_Finder.exe
echo.
echo Fatto: TV_Finder.exe nella cartella principale.
pause
