"""Read source placement records without inventing a resolved frame.

This control validates type, variability, availability and finite values.
It is not the complete geospatial validator or a placement/projection runtime.
In particular, it does not prescribe a near-unit quaternion acceptance tolerance.
"""
import math
from pxr import Sdf, Usd, UsdGeom
from review.scope import discover, ScopeError


def read(prim, time):
    definition = discover(prim)
    owner = prim.GetStage().GetPrimAtPath(definition['binding_prim'])
    if not UsdGeom.Xformable(owner):
        raise ScopeError('Model binding must be on Xformable')
    result = dict(definition)
    if owner.HasAttribute('crs:scale') and owner.GetAttribute('crs:scale').HasAuthoredValueOpinion():
        raise ScopeError('Undocumented crs:scale is not an input')
    for name, kind, fallback in [
            ('position', Sdf.ValueTypeNames.Double3, None),
            ('orientation', Sdf.ValueTypeNames.Quatd, (1., 0., 0., 0.))]:
        attribute = owner.GetAttribute('crs:' + name)
        authored=attribute.GetPropertyStack(Usd.TimeCode(time)) if attribute else []
        if authored and authored[0].typeName!=kind:
            raise ScopeError('Placement ' + name + ' has wrong type')
        if authored and authored[0].variability!=Sdf.VariabilityVarying:
            raise ScopeError('Placement ' + name + ' must be varying')
        if attribute and attribute.GetResolveInfo(Usd.TimeCode(time)).ValueIsBlocked():
            raise ScopeError('Placement ' + name + ' is unavailable')
        if attribute and attribute.GetTypeName() != kind:
            raise ScopeError('Placement ' + name + ' has wrong type')
        if attribute and attribute.GetVariability() != Sdf.VariabilityVarying:
            raise ScopeError('Placement ' + name + ' must be varying')
        if not attribute or not attribute.HasAuthoredValueOpinion():
            if fallback is None:
                raise ScopeError('Placement position is unavailable')
            values = fallback
        else:
            value = attribute.Get(Usd.TimeCode(time))
            if value is None:
                raise ScopeError('Placement ' + name + ' is unavailable')
            values = (value.GetReal(), *value.GetImaginary()) if name == 'orientation' else tuple(value)
        if not all(math.isfinite(v) for v in values):
            raise ScopeError('Placement ' + name + ' is nonfinite')
        if name == 'orientation':
            if not any(values):
                raise ScopeError('Placement orientation is a zero quaternion')
            result[name] = {'real': values[0], 'imaginary': list(values[1:])}
        else:
            result[name] = list(values)
    return result


def queries(stage, paths, time, interpolation):
    stage.SetInterpolationType(Usd.InterpolationTypeHeld if interpolation == 'held' else Usd.InterpolationTypeLinear)
    before = {layer.identifier: layer.ExportToString() for layer in stage.GetUsedLayers()}
    output = []
    for path in paths:
        try:
            output.append({'prim': path, 'success': True, **read(stage.GetPrimAtPath(path), time)})
        except ScopeError as error:
            output.append({'prim': path, 'success': False, 'error': str(error)})
    assert before == {layer.identifier: layer.ExportToString() for layer in stage.GetUsedLayers()}
    return {'queries': output, 'source_unchanged': True}
