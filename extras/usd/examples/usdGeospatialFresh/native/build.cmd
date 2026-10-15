@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
"C:\progs\CMake\bin\cmake.exe" -S "%~dp0." -B "%~dp0build" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 exit /b %errorlevel%
"C:\progs\CMake\bin\cmake.exe" --build "%~dp0build" --parallel 4
