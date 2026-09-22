"""Build the native consumer against an explicitly selected stock OpenUSD SDK."""
import os
from pathlib import Path
import shutil
import subprocess
from geobuild.delivery import sha


def build(root,output,env):
    sdk=env.get('GEO_USD_SDK')
    if not sdk or not (Path(sdk)/'pxrConfig.cmake').is_file():
        raise ValueError('Complete run needs GEO_USD_SDK with stock imaging libraries')
    cmake=env.get('GEO_CMAKE') or shutil.which('cmake')
    if not cmake:
        raise ValueError('CMake is required for the native consumer')
    folder=output/'native-build'
    configure=[cmake,'-S',str(root/'native'),'-B',str(folder),'-DCMAKE_BUILD_TYPE=Release',
               '-Dpxr_DIR='+sdk,'-DCMAKE_PREFIX_PATH='+sdk]
    if env.get('GEO_NINJA'):
        configure+=['-G','Ninja','-DCMAKE_MAKE_PROGRAM='+env['GEO_NINJA']]
    compile=[cmake,'--build',str(folder),'--config','Release']
    if os.name=='nt' and env.get('GEO_VCVARS'):
        def quote(value):
            if any(c in value for c in '\r\n"%&|<>^!'):
                raise ValueError('Unsupported shell metacharacter in native build path')
            return '"'+value+'"'
        script=output/'compile-native.cmd'
        script.write_text('@echo off\ncall '+quote(env['GEO_VCVARS'])+' > nul\nif errorlevel 1 exit /b %errorlevel%\n'+
            ' '.join(map(quote,configure))+'\nif errorlevel 1 exit /b %errorlevel%\n'+
            ' '.join(map(quote,compile))+'\n',encoding='utf-8')
        commands=[['cmd.exe','/d','/c',str(script)]]
    else:
        commands=[configure,compile]
    with (output/'native-build.log').open('w',encoding='utf-8') as log:
        for command in commands:
            subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    names=['geobuildHydra.exe','Release/geobuildHydra.exe'] if os.name=='nt' else ['geobuildHydra']
    executable=next((folder/name for name in names if (folder/name).is_file()),None)
    if not executable:
        raise ValueError('Native build did not produce an executable')
    env['GEO_HYDRA_EXECUTABLE']=str(executable)
    env['GEO_HYDRA_LIBRARY_PATH']=os.pathsep.join([str(Path(sdk)/'lib'),str(Path(sdk)/'bin'),env.get('GEO_HYDRA_LIBRARY_PATH','')])
    return {'executable_sha256':sha(executable),'source_sha256':{p.name:sha(p) for p in (root/'native').iterdir() if p.is_file()},
            'built_in_this_run':True,'link_scope':'stock OpenUSD imaging libraries; no retired geospatial implementation'}
