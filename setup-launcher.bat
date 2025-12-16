@echo off
echo ============================================
echo Consilium Launcher Setup
echo ============================================
echo.
echo Installing required packages...
pip install pystray Pillow -q
echo.
echo Done! You can now:
echo   - Double-click "Consilium.pyw" to launch
echo   - Or run "python launcher.py" for console output
echo.
echo The launcher will:
echo   - Start backend and frontend (hidden)
echo   - Open Chrome automatically
echo   - Add a system tray icon
echo   - Right-click tray icon to exit
echo.
pause
