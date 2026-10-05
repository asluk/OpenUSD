"""Direct anchor-origin coordinate queries with no ordinary adjustment.

No model-axis basis, geometry or local-affine approximation is selected here.
The source tuple is interpolated by USD before a supported CRS operation.
"""
import math
from pxr import UsdGeom
from pyproj import CRS, Transformer, proj_version_str
from review.placement_values import read
from review.scope import ScopeError, discover


def angular_factors(crs):
    if not crs.is_geographic:
        return None
    roles = {axis.direction: axis.unit_conversion_factor for axis in crs.axis_info}
    if set(roles) != {'east', 'north', 'up'}:
        raise ScopeError('Unsupported geographic component set')
    return [roles['east']*180/math.pi, roles['north']*180/math.pi]


def convert(source_wkt, output_wkt, position):
    source, output = CRS.from_wkt(source_wkt), CRS.from_wkt(output_wkt)
    for definition in [source, output]:
        if definition.is_bound:
            raise ScopeError('Bound CRS origin-query profile not implemented; no embedded transform dropped')
        roles = {axis.direction for axis in definition.axis_info}
        if roles not in [{'east', 'north', 'up'}, {'geocentricX', 'geocentricY', 'geocentricZ'}]:
            raise ScopeError('Unsupported coordinate component set')
    if len(source.axis_info) != 3 or len(output.axis_info) != 3:
        raise ScopeError('Complete three-component coordinate definition required')
    values = list(position)
    source_angles = angular_factors(source)
    target_angles = angular_factors(output)
    if source_angles:
        values[0] *= source_angles[0]
        values[1] *= source_angles[1]
    transformer = Transformer.from_crs(source, output, always_xy=True,
                                      allow_ballpark=False, only_best=True)
    try:
        resolved = list(transformer.transform(*values, errcheck=True))
    except Exception as error:
        raise ScopeError('Coordinate operation failed; no substitute') from error
    if not all(math.isfinite(component) for component in resolved):
        raise ScopeError('Coordinate operation failed; no substitute')
    try:
        operation = transformer.get_last_used_operation()
    except Exception:
        operation = transformer
    if 't_epoch=' in operation.definition or '+proj=deformation' in operation.definition:
        raise ScopeError('Epoch-dependent operations are deferred')
    if target_angles:
        resolved[0] /= target_angles[0]
        resolved[1] /= target_angles[1]
    return {'coordinates': resolved, 'operation': operation.description,
            'operation_definition': operation.definition,
            'operation_accuracy_metres': operation.accuracy if operation.accuracy >= 0 else None,
            'engine': 'PROJ', 'engine_version': proj_version_str}


def query(stage, path, output_wkt, time):
    record = read(stage.GetPrimAtPath(path), time)
    if record['binding_prim'] != path or not stage.GetPrimAtPath(path).GetParent().IsPseudoRoot():
        raise ScopeError('This origin adapter supports only direct top-level anchors; dependent frame request stopped')
    if not output_wkt:
        try: output_wkt = discover(stage.GetDefaultPrim())['wkt']
        except ScopeError as error:
            raise ScopeError('No usable output CRS on composed defaultPrim') from error
    owner = stage.GetPrimAtPath(record['binding_prim'])
    if UsdGeom.Xformable(owner).GetOrderedXformOps():
        raise ScopeError('Ordinary-adjustment frame is unspecified; origin query stopped')
    return convert(record['wkt'], output_wkt, record['position'])


def queries(stage, paths, output_wkt, time, interpolation):
    from pxr import Usd
    stage.SetInterpolationType(Usd.InterpolationTypeHeld if interpolation=='held' else Usd.InterpolationTypeLinear)
    before={layer.identifier:layer.ExportToString() for layer in stage.GetUsedLayers()}
    rows=[]
    for path in paths:
        try: rows.append({'prim':path,'success':True,**query(stage,path,output_wkt,time)})
        except ScopeError as error: rows.append({'prim':path,'success':False,'error':str(error)})
    after={layer.identifier:layer.ExportToString() for layer in stage.GetUsedLayers()}
    if before!=after: raise RuntimeError('Origin query changed source layers')
    return {'queries':rows,'source_unchanged':True}
