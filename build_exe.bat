@echo off
chcp 65001 >nul

echo ===================================================
echo  Building UEBA ML Project to .exe...
echo ===================================================

:: Проверяем наличие папок ВНУТРИ app
if not exist "app\artifacts\ueba_autoencoder.pth" (
    echo [!] WARNING: Model file not found in app\artifacts!
    echo     The app will build, but you need to train
    echo     the model first via the app interface.
    echo.
)

if not exist "app\data" (
    echo [!] WARNING: Data folder not found in app\data!
    echo     Creating empty folder...
    mkdir app\data 2>nul
)

echo [OK] Starting PyInstaller...
echo.

pyinstaller --noconfirm --onedir --windowed ^
    --name "UEBA_ML_Project" ^
    --add-data "app/artifacts;artifacts" ^
    --add-data "app/data;data" ^
    --hidden-import "sklearn.utils._weight_vector" ^
    --hidden-import "sklearn.utils._typedefs" ^
    --hidden-import "sklearn.utils._container_aliases" ^
    --collect-all "customtkinter" ^
    app/main_app.py

echo.
echo ===================================================
echo  DONE!
echo  The .exe is located in: dist\UEBA_ML_Project\
echo ===================================================
pause