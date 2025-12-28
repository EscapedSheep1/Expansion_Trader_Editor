@echo off
echo Building DayZ Trader Editor executable (debug mode - shows console)...
echo.

REM Install PyInstaller and Pillow if not already installed
python -m pip install pyinstaller pillow

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist dayz_trader_editor.spec del dayz_trader_editor.spec

REM Build the executable WITHOUT --windowed to see error messages
python -m PyInstaller --name="DayZ Trader Editor" ^
    --onefile ^
    --icon=icon.png ^
    --add-data "icon.png;." ^
    --add-data "icon.txt;." ^
    --add-data "example.json;." ^
    --collect-all tkinter ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.filedialog ^
    --hidden-import=tkinter.messagebox ^
    --hidden-import=tkinter.scrolledtext ^
    --hidden-import=tkinter.colorchooser ^
    --hidden-import=tkinter.simpledialog ^
    --hidden-import=xml.etree.ElementTree ^
    --hidden-import=xml.etree.cElementTree ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    dayz_trader_editor.py

echo.
echo Build complete! Executable is in the 'dist' folder.
echo This version shows a console window for debugging.
pause

