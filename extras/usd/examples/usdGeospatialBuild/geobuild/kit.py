"""Execute the Fabric consumer in a real, installed Kit process."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import numpy as np


def consume(frames):
    executable=os.environ.get('GEO_KIT_EXECUTABLE')
    if not executable or not Path(executable).is_file():
        raise RuntimeError('Complete run requires GEO_KIT_EXECUTABLE')
    with tempfile.TemporaryDirectory(prefix='geobuild-kit-') as folder:
        folder=Path(folder)
        source,output=folder/'input.json',folder/'output.json'
        source.write_text(json.dumps({'frames':[f.snapshot() for f in frames]}),encoding='utf-8')
        env=dict(os.environ,GEO_KIT_INPUT=str(source),GEO_KIT_OUTPUT=str(output),PYTHONNOUSERSITE='1')
        env.pop('PYTHONPATH',None)
        env.pop('PXR_PLUGINPATH_NAME',None)
        command=[executable,str(Path(executable).parent/'apps'/'omni.app.empty.kit'),
            '--no-window','--enable','omni.usd','--enable','usdrt.scenegraph','--enable','omni.kit.loop-default',
            '--enable','omni.kit.numpy.common',
            '--/app/renderer/enabled=false','--/app/extensions/registryEnabled=false',
            '--/app/file/ignoreUnsavedOnExit=true','--/app/settings/persistent=false',
            '--/log/level=error','--/log/file='+str(folder/'kit.log'),
            '--exec',str(Path(__file__).with_name('kit_consumer.py'))]
        with (folder/'console.log').open('w',encoding='utf-8') as log:
            completed=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=120)
        if not output.exists():
            raise RuntimeError('Kit did not produce evidence: '+(folder/'console.log').read_text(encoding='utf-8',errors='replace')[-2500:])
        result=json.loads(output.read_text(encoding='utf-8'))
        if result.get('error'):
            raise RuntimeError(result['error'])
        if completed.returncode:
            raise RuntimeError('Kit exited unsuccessfully: '+str(completed.returncode))
    maximum=0
    for frame,actual in zip(frames,result['frames']):
        if set(frame.prims)!=set(actual['prims']):
            raise AssertionError('Fabric returned an incomplete scene')
        for path in frame.prims:
            a=np.array(actual['prims'][path]['world_points']).reshape((-1,3))
            b=frame.world_points(path)
            if a.shape!=b.shape:
                raise AssertionError('Fabric returned an incomplete point array: '+path)
            if len(a):
                maximum=max(maximum,float(np.linalg.norm(a-b,axis=1).max()))
    result['maximum_consumer_residual_output_units']=maximum
    return result
