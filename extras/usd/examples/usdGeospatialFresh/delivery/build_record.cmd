@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cl /nologo /EHsc /std:c++17 /O2 /I C:\git\usd-geospatial-fresh\inst\include /I C:\Users\aluk\AppData\Local\Programs\Python\Python310\include "%~dp0record_storm.cpp" /Fo:"%~dp0record_storm.obj" /Fe:"%~dp0record_storm.exe" /link /LIBPATH:C:\git\usd-geospatial-fresh\inst\lib /LIBPATH:C:\Users\aluk\AppData\Local\Programs\Python\Python310\libs usd_usdAppUtils.lib usd_usdImagingGL.lib usd_usdGeom.lib usd_usd.lib usd_sdf.lib usd_tf.lib usd_plug.lib usd_garch.lib usd_gf.lib usd_vt.lib usd_ts.lib usd_ar.lib usd_work.lib usd_python.lib tbb.lib python310.lib opengl32.lib gdi32.lib user32.lib
exit /b %errorlevel%
