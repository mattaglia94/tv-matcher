@echo off
REM Crea TV_Matcher.exe (serve Python 3.11+ installato SOLO su questo PC, una volta)
cd /d %~dp0app
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --add-data "..\web\catalogo.json;." --name TV_Matcher tv_matcher.py
copy /Y dist\TV_Matcher.exe ..\TV_Matcher.exe
echo.
echo Fatto: TV_Matcher.exe nella cartella principale.
pause
