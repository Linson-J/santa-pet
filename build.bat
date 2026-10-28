@echo off
echo ========================================
echo   Building Santa Pet .exe
echo ========================================

pip install pyinstaller pillow psutil pystray

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "SantaPet" ^
  --icon "assets\santa_icon.ico" ^
  santa_pet.py

echo.
echo Build complete! Check the dist\ folder.
pause
