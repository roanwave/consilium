@echo off
:: Consilium Launcher - Double-click to start
:: First run installs pystray/Pillow, then launches without console

:: Check if pystray is installed
python -c "import pystray" 2>nul
if errorlevel 1 (
    echo First-time setup: Installing launcher dependencies...
    pip install pystray Pillow -q
    echo Done!
    echo.
)

:: Launch without console window using pythonw
start "" pythonw "%~dp0Consilium.pyw"
