@echo off
echo === Work Sleep Repeat — build ===
echo.

echo [1/3] Generating icon...
python tools\make_icon.py
if errorlevel 1 (echo FAILED & exit /b 1)

echo [2/3] Running PyInstaller...
python -m PyInstaller --clean --noconfirm build.spec
if errorlevel 1 (echo FAILED & exit /b 1)

echo [3/3] Done.
echo Output: dist\WorkSleepRepeat\WorkSleepRepeat.exe
dir dist\WorkSleepRepeat\WorkSleepRepeat.exe
