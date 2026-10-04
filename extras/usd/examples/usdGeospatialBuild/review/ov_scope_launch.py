"""Read the shared CRS binding data through a live OV stage context."""
import asyncio
import ctypes
import json
import os
from pathlib import Path
import sys
import time

sdk = Path(os.environ['GEOBUILD_OV_SDK'])
os.environ['CARB_APP_PATH'] = str(sdk)
sys.path[:] = [p for p in sys.path if 'AppData\\Roaming\\Python' not in p and 'AppData/Roaming/Python' not in p]
os.add_dll_directory(str(sdk))
ctypes.CDLL(str(sdk / 'carb.dll'))
sys.path.insert(0, str(sdk / 'kernel/py'))
import carb
import omni.kit.app

framework = carb.get_framework()
framework.load_plugins(loaded_file_wildcards=['omni.kit.app.plugin'], search_paths=[str(sdk / 'kernel/plugins')])
app = omni.kit.app.get_app()
app.startup('geospatial-proposal-scope', str(sdk), [sys.argv[0], str(Path(__file__).with_name('scope.kit')), '--no-window', '--/log/level=warn', '--/app/settings/persistent=false'])


async def inspect():
    try:
        import omni.usd
        context = omni.usd.get_context()
        from pxr import Sdf
        jobs = json.loads(Path(os.environ['GEOBUILD_SCOPE_JOBS']).read_text())
        results = []
        for job in jobs:
            initial_load = omni.usd.UsdContextInitialLoadSet.LOAD_NONE if job['load_none'] else omni.usd.UsdContextInitialLoadSet.LOAD_ALL
            opened, message = await context.open_stage_async(job['stage'], load_set=initial_load)
            if not opened:
                raise RuntimeError('OV could not ingest scope fixture: ' + message)
            await app.next_update_async()
            stage = context.get_stage()
            before = {layer.identifier: layer.ExportToString() for layer in stage.GetUsedLayers()}
            queries = []
            for path in job['queries']:
                row = {'prim': path}
                try:
                    current = stage.GetPrimAtPath(path)
                    if not current:
                        raise ValueError('Prim is not available in the composed stage')
                    found = False
                    while current and not current.IsPseudoRoot():
                        schemas = current.GetMetadata('apiSchemas')
                        if schemas and 'GeospatialCRSBindingAPI' in schemas.GetAppliedItems():
                            attribute = current.GetAttribute('crs:wkt')
                            if not attribute or not attribute.HasAuthoredValue():
                                raise ValueError('Nearest direct binding has no authored CRS definition')
                            if attribute.GetTypeName() != Sdf.ValueTypeNames.Token:
                                raise ValueError('CRS definition must be a token')
                            if attribute.GetVariability() != Sdf.VariabilityUniform:
                                raise ValueError('CRS definition must be uniform')
                            value = attribute.Get()
                            if not value:
                                raise ValueError('CRS definition is empty')
                            row.update(success=True, binding_prim=str(current.GetPath()), wkt=value)
                            found = True
                            break
                        current = current.GetParent()
                    if not found:
                        raise ValueError('No CRS binding in the composed ancestry')
                except ValueError as error:
                    row.update(success=False, error=str(error))
                queries.append(row)
            if before != {layer.identifier: layer.ExportToString() for layer in stage.GetUsedLayers()}:
                raise RuntimeError('OV scope query changed source layers')
            results.append({'name': job['name'], 'queries': queries, 'source_ingested': True, 'source_unchanged': True})
            await context.close_stage_async()
        Path(os.environ['GEOBUILD_SCOPE_RESULT']).write_text(json.dumps(results, indent=2) + '\n')
        app.post_quit(0)
    except BaseException:
        import traceback
        Path(os.environ['GEOBUILD_SCOPE_ERROR']).write_text(traceback.format_exc())
        app.post_quit(1)


asyncio.ensure_future(inspect())
started = time.monotonic()
while app.is_running():
    app.update()
    if time.monotonic() - started > 180:
        Path(os.environ['GEOBUILD_SCOPE_ERROR']).write_text('Live scope run timed out; no passing result claimed')
        app.post_quit(1)
sys.exit(app.shutdown())
