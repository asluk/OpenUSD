"""CRS discovery from composed binding data; no placement or normalization guesses."""
from pxr import Sdf

APPLIED_SCHEMA = 'GeospatialCRSBindingAPI'


class ScopeError(ValueError):
    pass


def discover(prim):
    if not prim:
        raise ScopeError('Prim is not available in the composed stage')
    current = prim
    while current and not current.IsPseudoRoot():
        schemas = current.GetMetadata('apiSchemas')
        if schemas and APPLIED_SCHEMA in schemas.GetAppliedItems():
            attribute = current.GetAttribute('crs:wkt')
            if not attribute or not attribute.HasAuthoredValue():
                raise ScopeError('Nearest direct binding has no authored CRS definition')
            if attribute.GetTypeName() != Sdf.ValueTypeNames.Token:
                raise ScopeError('CRS definition must be a token')
            if attribute.GetVariability() != Sdf.VariabilityUniform:
                raise ScopeError('CRS definition must be uniform')
            value = attribute.Get()
            if not value:
                raise ScopeError('CRS definition is empty')
            return {'binding_prim': str(current.GetPath()), 'wkt': value}
        current = current.GetParent()
    raise ScopeError('No CRS binding in the composed ancestry')


def queries(stage, paths):
    output = []
    before = {layer.identifier: layer.ExportToString() for layer in stage.GetUsedLayers()}
    for path in paths:
        try:
            output.append({'prim': path, 'success': True, **discover(stage.GetPrimAtPath(path))})
        except ScopeError as error:
            output.append({'prim': path, 'success': False, 'error': str(error)})
    after = {layer.identifier: layer.ExportToString() for layer in stage.GetUsedLayers()}
    if before != after:
        raise AssertionError('CRS discovery modified the composed source layers')
    return {'queries': output, 'source_unchanged': True}
