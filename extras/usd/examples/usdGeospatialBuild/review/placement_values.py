"""Evaluate composed placement inputs. Returned quaternions are transient query data,
not authored USD properties. HPR composition and sample selection precede conversion.
"""
import math
from pxr import Gf, Sdf, Usd, UsdGeom
from review.scope import discover, ScopeError


def orientation_sample(attribute, time):
    value = attribute.Get(time)
    if value is None:
        raise ScopeError('Placement orientation is unavailable')
    if not all(math.isfinite(v) for v in value):
        raise ScopeError('Placement orientation is nonfinite')
    h,p,r = [math.radians(v)/2 for v in value]
    qh = Gf.Quatd(math.cos(h), Gf.Vec3d(0,0,-math.sin(h)))
    qp = Gf.Quatd(math.cos(p), Gf.Vec3d(math.sin(p),0,0))
    qr = Gf.Quatd(math.cos(r), Gf.Vec3d(0,math.sin(r),0))
    return (qh*qp*qr).GetNormalized()

def orientation_value(attribute, time, stage):
    time = Usd.TimeCode(time)
    if time.IsDefault():
        return orientation_sample(attribute,time)
    bracket = attribute.GetBracketingTimeSamples(time.GetValue())
    if not bracket:
        return orientation_sample(attribute,time)
    lower,upper = bracket
    first = orientation_sample(attribute,Usd.TimeCode(lower))
    if lower == upper or stage.GetInterpolationType() == Usd.InterpolationTypeHeld:
        return first
    second = orientation_sample(attribute,Usd.TimeCode(upper))
    dot = first.GetReal()*second.GetReal() + Gf.Dot(first.GetImaginary(),second.GetImaginary())
    if dot < 0:
        second=Gf.Quatd(-second.GetReal(),-second.GetImaginary())
    return Gf.Slerp((time.GetValue()-lower)/(upper-lower),first,second).GetNormalized()

def read(prim, time):
    candidate=prim
    while candidate and not candidate.IsPseudoRoot():
        schemas=candidate.GetMetadata('apiSchemas')
        direct=bool(schemas and 'GeospatialCRSBindingAPI' in schemas.GetAppliedItems())
        if not direct:
            for field in ['crs:position','crs:orientation']:
                a=candidate.GetAttribute(field)
                if a and a.GetPropertyStack(Usd.TimeCode(time)):
                    raise ScopeError('Invalid placement field on inherited-only descendant: '+field)
        if direct: break
        candidate=candidate.GetParent()
    definition = discover(prim)
    owner = prim.GetStage().GetPrimAtPath(definition['binding_prim'])
    if not UsdGeom.Xformable(owner):
        raise ScopeError('Model binding must be on Xformable')
    result = dict(definition)
    if owner.HasAttribute('crs:scale') and owner.GetAttribute('crs:scale').HasAuthoredValueOpinion():
        raise ScopeError('Undocumented crs:scale is not an input')
    for name, kind, fallback in [
            ('position', Sdf.ValueTypeNames.Double3, None),
            ('orientation', Sdf.ValueTypeNames.Double3, (1., 0., 0., 0.))]:
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
            value = orientation_value(attribute,time,prim.GetStage()) if name == 'orientation' else attribute.Get(Usd.TimeCode(time))
            if value is None:
                raise ScopeError('Placement ' + name + ' is unavailable')
            values = (value.GetReal(), *value.GetImaginary()) if name == 'orientation' else tuple(value)
        if not all(math.isfinite(v) for v in values):
            raise ScopeError('Placement ' + name + ' is nonfinite')
        if name == 'orientation':
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
