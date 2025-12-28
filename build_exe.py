"""
Build script for creating DayZ Trader Editor executable
Run this script to create a single .exe file using PyInstaller
"""
import subprocess
import sys
import os

def main():
    print("Building DayZ Trader Editor executable...")
    print()
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully!")
        print()
    
    # Clean previous builds
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            import shutil
            shutil.rmtree(folder)
            print(f"Cleaned {folder} folder")
    
    if os.path.exists("dayz_trader_editor.spec"):
        os.remove("dayz_trader_editor.spec")
        print("Cleaned spec file")
    
    print()
    print("Building executable...")
    print()
    
    # Build command
    cmd = [
        "pyinstaller",
        "--name=DayZ Trader Editor",
        "--onefile",
        "--windowed",
        "--icon=icon.png",
        "--add-data", "icon.png;.",
        "--add-data", "icon.txt;.",
        "--add-data", "example.json;.",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.scrolledtext",
        "--hidden-import=tkinter.colorchooser",
        "--hidden-import=tkinter.simpledialog",
        "dayz_trader_editor.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print()
        print("=" * 50)
        print("Build complete! Executable is in the 'dist' folder.")
        print("=" * 50)
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

