import os,sys,ctypes,runpy,time
from pathlib import Path
root=Path(os.environ['GEOBUILD_OV_SDK']);os.environ['CARB_APP_PATH']=str(root)
os.add_dll_directory(str(root));ctypes.CDLL(str(root/'carb.dll'));sys.path.insert(0,str(root/'kernel/py'))
import carb,omni.kit.app
carb.get_framework().load_plugins(loaded_file_wildcards=['omni.kit.app.plugin'],search_paths=[str(root/'kernel/plugins')])
app=omni.kit.app.get_app();source=Path(__file__).parent
app.startup('geospatial-contract-candidate',str(root),[sys.argv[0],str(source.parent/'ov/geobuild.kit'),'--no-window','--/log/level=warn','--/app/settings/persistent=false'])
runpy.run_path(str(source/'ov_live.py'));start=time.monotonic()
while app.is_running():
    app.update()
    if time.monotonic()-start>600:Path(os.environ['GEOBUILD_OV_ERROR']).write_text('Live execution timed out');app.post_quit(1)
sys.exit(app.shutdown())
