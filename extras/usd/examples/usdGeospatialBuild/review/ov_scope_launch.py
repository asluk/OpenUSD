"""Read the shared CRS binding data through a live OV stage context."""
import asyncio
import ctypes
import json
import math
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
        from pxr import Sdf, Usd, UsdGeom
        dependency = os.environ.get('GEOBUILD_PYTHON_DEPENDENCIES')
        if dependency:
            sys.path.append(dependency)
        from pyproj import CRS, Transformer, proj_version_str
        jobs = json.loads(Path(os.environ['GEOBUILD_SCOPE_JOBS']).read_text())
        results = []
        for job in jobs:
            initial_load = omni.usd.UsdContextInitialLoadSet.LOAD_NONE if job['load_none'] else omni.usd.UsdContextInitialLoadSet.LOAD_ALL
            opened, message = await context.open_stage_async(job['stage'], load_set=initial_load)
            if not opened:
                raise RuntimeError('OV could not ingest scope fixture: ' + message)
            await app.next_update_async()
            stage = context.get_stage()
            if job.get('kind') in ['placement_values', 'origin_coordinates']:
                stage.SetInterpolationType(Usd.InterpolationTypeHeld if job['interpolation'] == 'held' else Usd.InterpolationTypeLinear)
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
                    if job.get('kind') in ['placement_values', 'origin_coordinates']:
                        if not UsdGeom.Xformable(current):
                            raise ValueError('Model binding must be on Xformable')
                        for name, required, fallback in [
                                ('position', Sdf.ValueTypeNames.Double3, None),
                                ('orientation', Sdf.ValueTypeNames.Quatd, (1., 0., 0., 0.)),
                                ('scale', Sdf.ValueTypeNames.Double3, (1., 1., 1.))]:
                            field = current.GetAttribute('crs:' + name)
                            if field and field.GetTypeName() != required:
                                raise ValueError('Placement ' + name + ' has wrong type')
                            if field and field.GetVariability() != Sdf.VariabilityVarying:
                                raise ValueError('Placement ' + name + ' must be varying')
                            if not field or not field.HasAuthoredValueOpinion():
                                if fallback is None:
                                    raise ValueError('Placement position is unavailable')
                                components = fallback
                            else:
                                resolved = field.Get(Usd.TimeCode(job['time']))
                                if resolved is None:
                                    raise ValueError('Placement ' + name + ' is unavailable')
                                components = (resolved.GetReal(), *resolved.GetImaginary()) if name == 'orientation' else tuple(resolved)
                            if not all(math.isfinite(component) for component in components):
                                raise ValueError('Placement ' + name + ' is nonfinite')
                            if name == 'orientation':
                                if not any(components):
                                    raise ValueError('Placement orientation is a zero quaternion')
                                row[name] = {'real': components[0], 'imaginary': list(components[1:])}
                            else:
                                row[name] = list(components)
                    if job.get('kind') == 'origin_coordinates':
                        if str(current.GetPath())!=path or not current.GetParent().IsPseudoRoot():
                            raise ValueError('This origin adapter supports only direct top-level anchors; dependent frame request stopped')
                        output_wkt = job['output_wkt']
                        if not output_wkt:
                            default = stage.GetDefaultPrim()
                            while default and not default.IsPseudoRoot():
                                schemas = default.GetMetadata('apiSchemas')
                                if schemas and 'GeospatialCRSBindingAPI' in schemas.GetAppliedItems():
                                    field = default.GetAttribute('crs:wkt')
                                    if field and field.GetTypeName()==Sdf.ValueTypeNames.Token and field.GetVariability()==Sdf.VariabilityUniform:
                                        output_wkt=field.Get()
                                    break
                                default=default.GetParent()
                            if not output_wkt:
                                raise ValueError('No usable output CRS on composed defaultPrim')
                        if UsdGeom.Xformable(current).GetOrderedXformOps():
                            raise ValueError('Ordinary-adjustment frame is unspecified; origin query stopped')
                        source, target = CRS.from_wkt(row['wkt']), CRS.from_wkt(output_wkt)
                        for definition in [source, target]:
                            if definition.is_bound:
                                raise ValueError('Bound CRS origin-query profile not implemented; no embedded transform dropped')
                            roles = {axis.direction for axis in definition.axis_info}
                            if roles not in [{'east', 'north', 'up'}, {'geocentricX', 'geocentricY', 'geocentricZ'}]:
                                raise ValueError('Unsupported coordinate component set')
                        values = list(row['position'])
                        if source.is_geographic:
                            factors = {axis.direction:axis.unit_conversion_factor*180/math.pi for axis in source.axis_info}
                            values[0] *= factors['east']; values[1] *= factors['north']
                        transformer = Transformer.from_crs(source, target, always_xy=True, allow_ballpark=False, only_best=True)
                        try:
                            coordinate = list(transformer.transform(*values, errcheck=True))
                        except Exception as error:
                            raise ValueError('Coordinate operation failed; no substitute') from error
                        if not all(math.isfinite(value) for value in coordinate):
                            raise ValueError('Coordinate operation failed; no substitute')
                        try: operation = transformer.get_last_used_operation()
                        except Exception: operation = transformer
                        if 't_epoch=' in operation.definition or 'proj=deformation' in operation.definition:
                            raise ValueError('Epoch-dependent operations are deferred')
                        if target.is_geographic:
                            factors = {axis.direction:axis.unit_conversion_factor*180/math.pi for axis in target.axis_info}
                            coordinate[0] /= factors['east']; coordinate[1] /= factors['north']
                        row = {'prim':path, 'success':True, 'coordinates':coordinate,
                               'operation':operation.description, 'operation_definition':operation.definition,
                               'operation_accuracy_metres':operation.accuracy if operation.accuracy>=0 else None,
                               'engine':'PROJ', 'engine_version':proj_version_str}
                except ValueError as error:
                    row = {'prim': path, 'success': False, 'error': str(error)}
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
