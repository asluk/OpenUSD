"""Embedding launcher: run the async authored-scene probe through real app updates."""
import sys,os,ctypes,runpy,time
from pathlib import Path
root=Path(os.environ['GEOBUILD_OV_SDK']);os.environ['CARB_APP_PATH']=str(root)
sys.path[:]=[p for p in sys.path if 'AppData\\Roaming\\Python' not in p and 'AppData/Roaming/Python' not in p]
os.add_dll_directory(str(root));ctypes.CDLL(str(root/'carb.dll'))
sys.path.insert(0,str(root/'kernel/py'))
import carb,omni.kit.app
framework=carb.get_framework();framework.load_plugins(loaded_file_wildcards=['omni.kit.app.plugin'],search_paths=[str(root/'kernel/plugins')])
app=omni.kit.app.get_app();source=Path(__file__).parent
app.startup('geospatial-candidate',str(root),[sys.argv[0],str(source/'geobuild.kit'),'--no-window','--/log/level=warn','--/app/settings/persistent=false'])
Path(os.environ['GEOBUILD_OV_ERROR']+'.launch.txt').write_text('startup returned; running='+str(app.is_running()))
try:runpy.run_path(str(source/'run_live.py'))
except BaseException:
    import traceback
    Path(os.environ['GEOBUILD_OV_ERROR']).write_text(traceback.format_exc());raise
Path(os.environ['GEOBUILD_OV_ERROR']+'.launch.txt').write_text('probe scheduled; running='+str(app.is_running()))
started=time.monotonic()
while app.is_running():
    app.update()
    if time.monotonic()-started>600:
        Path(os.environ['GEOBUILD_OV_ERROR']).write_text('OV run timed out without completing; no passing result claimed');app.post_quit(1)
code=app.shutdown();sys.exit(code)
