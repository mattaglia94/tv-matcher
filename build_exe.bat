@echo off
REM Crea Radar_TV.exe (serve Python 3.11+ installato SOLO su questo PC, una volta)
cd /d %~dp0app
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --add-data "..\web\catalogo.json;." --name Radar_TV tv_matcher.py
copy /Y dist\Radar_TV.exe ..\Radar_TV.exe
echo.
echo Fatto: Radar_TV.exe nella cartella principale.
pause
