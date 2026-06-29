@echo off
echo ============================================
echo  MEGA Account Generator - Windows Build
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Check/install PyInstaller
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Find customtkinter path
for /f "delims=" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i
echo CustomTkinter: %CTK_PATH%

REM Check megatools
if not exist "megatools\megareg.exe" (
    echo WARNING: megatools not found in megatools\ folder.
    echo   Download Windows megatools and place .exe files in megatools\ folder.
    echo   Continuing build anyway...
)

echo.
echo Building standalone EXE...
echo.

python -m PyInstaller --noconfirm --onefile ^
    --add-data "%CTK_PATH%;customtkinter/" ^
    --add-data "logo.ico;." ^
    --add-data "logo.png;." ^
    --add-data "megatools;megatools" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "babel.numbers" ^
    --hidden-import "openpyxl" ^
    --hidden-import "openpyxl.cell._writer" ^
    --hidden-import "openpyxl.workbook._writer" ^
    --hidden-import "openpyxl.worksheet._writer" ^
    --hidden-import "PIL" ^
    --hidden-import "requests" ^
    --hidden-import "colorama" ^
    --hidden-import "tqdm" ^
    --hidden-import "faker" ^
    --hidden-import "faker.providers" ^
    --hidden-import "proxy_manager" ^
    --hidden-import "mailtm_client" ^
    --hidden-import "megatools_helper" ^
    --hidden-import "csv_utils" ^
    --hidden-import "export_utils" ^
    --hidden-import "tag_manager" ^
    --hidden-import "tkinter.filedialog" ^
    --icon "logo.ico" ^
    --name "MEGA-Generator" ^
    gui.py

echo.
echo ============================================
echo  Build complete!
echo ============================================
echo.
echo EXE: dist\MEGA-Generator.exe
echo Size: 
for %%A in (dist\MEGA-Generator.exe) do echo   %%~zA bytes
echo.
pause
