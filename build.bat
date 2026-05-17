@ECHO OFF
set PYTHON=E:\Develop\Anaconda\envs\forza-auto-gear-6\python.exe
%PYTHON% -m PyInstaller build.spec --clean --noconfirm
echo.
echo Build complete. Output: output\
