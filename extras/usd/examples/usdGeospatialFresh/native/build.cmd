@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
"C:\progs\CMake\bin\cmake.exe" -S "%~dp0." -B "%~dp0..\native-build" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -DUSD_ROOT=C:/git/usd-geospatial-fresh/inst -DPROJ_ROOT=C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff -DPYTHON_ROOT=C:/Users/aluk/AppData/Local/Programs/Python/Python310
if errorlevel 1 exit /b 1
"C:\progs\CMake\bin\cmake.exe" --build "%~dp0..\native-build"
