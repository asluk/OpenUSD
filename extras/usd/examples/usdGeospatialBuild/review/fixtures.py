"""Composition controls derived from the shared proposal, without placement fields."""
from pathlib import Path
import re
from pxr import Usd, UsdGeom, Sdf


def source_definitions(root):
    text = (Path(root) / 'proposal/proposal-source.txt').read_text(encoding='utf-8')
    definitions = []
    for heading in ['### 3D Geocentric (ECEF) with dynamic datum', '### Compound CRS: NAD83 / California zone 5 (ftUS) + NAVD88 height']:
        section = text.split(heading, 1)[1]
        definitions.append(re.search(r'```lisp\n(.*?)\n```', section, re.S).group(1))
    return definitions


def marker(prim):
    prim.SetMetadata('apiSchemas', Sdf.TokenListOp.CreateExplicit(['GeospatialCRSBindingAPI']))


def build(root, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    first, second = source_definitions(root)
    library = Usd.Stage.CreateNew(str(directory / 'crs-library.usda'))
    for name, value in [('ECEF', first), ('Grid', second)]:
        prim = library.DefinePrim('/Definitions/' + name, 'CoordinateReferenceSystem')
        prim.CreateAttribute('crs:wkt', Sdf.ValueTypeNames.Token, custom=False, variability=Sdf.VariabilityUniform).Set(value)
    library.GetRootLayer().Save()
    jobs = []

    def stage(name):
        result = Usd.Stage.CreateNew(str(directory / (name + '.usda')))
        parent = UsdGeom.Xform.Define(result, '/World').GetPrim()
        result.SetDefaultPrim(parent)
        UsdGeom.SetStageMetersPerUnit(result, .01)
        UsdGeom.SetStageUpAxis(result, UsdGeom.Tokens.y)
        UsdGeom.Xformable(parent).AddTranslateOp().Set((1, 2, 3))
        result.DefinePrim('/World/Data', 'Scope')
        return result, parent

    def bind(prim, name):
        marker(prim)
        prim.GetReferences().AddReference('./crs-library.usda', '/Definitions/' + name)

    def ok(path, owner, value):
        return {'prim': path, 'success': True, 'binding_prim': owner, 'wkt': value}

    def bad(path, message):
        return {'prim': path, 'success': False, 'error': message}

    def save(name, result, expected, load_none=False):
        result.GetRootLayer().Save()
        jobs.append({'name': name, 'stage': str(directory / (name + '.usda')),
                     'load_none': load_none, 'queries': [x['prim'] for x in expected], 'expected': expected})

    base, parent = stage('references')
    ordinary_before = UsdGeom.Xformable(parent).GetLocalTransformation()
    bind(parent, 'ECEF')
    child = UsdGeom.Xform.Define(base, '/World/Independent').GetPrim()
    bind(child, 'Grid')
    base.DefinePrim('/World/Independent/Data', 'Scope')
    base.DefinePrim('/World/Unmarked', 'Scope').CreateAttribute('crs:wkt', Sdf.ValueTypeNames.Token, variability=Sdf.VariabilityUniform).Set(second)
    assert ordinary_before == UsdGeom.Xformable(parent).GetLocalTransformation()
    save('references', base, [ok('/World', '/World', first), ok('/World/Data', '/World', first),
         ok('/World/Independent/Data', '/World/Independent', second), ok('/World/Unmarked', '/World', first)])

    assembly = Usd.Stage.CreateNew(str(directory / 'referenced-assembly.usda'))
    UsdGeom.SetStageMetersPerUnit(assembly, .01)
    UsdGeom.SetStageUpAxis(assembly, UsdGeom.Tokens.y)
    assembly.DefinePrim('/Assembly', 'Xform').GetReferences().AddReference('./references.usda', '/World')
    save('referenced-assembly', assembly, [ok('/Assembly/Data', '/Assembly', first),
         ok('/Assembly/Independent/Data', '/Assembly/Independent', second)])

    strong = Usd.Stage.CreateNew(str(directory / 'stronger-layer.usda'))
    strong.GetRootLayer().subLayerPaths = ['./references.usda']
    strong.OverridePrim('/World').CreateAttribute('crs:wkt', Sdf.ValueTypeNames.Token, variability=Sdf.VariabilityUniform).Set(second)
    save('stronger-layer', strong, [ok('/World/Data', '/World', second),
         ok('/World/Independent/Data', '/World/Independent', second)])

    variant, parent = stage('variant-selection')
    marker(parent)
    variants = parent.GetVariantSets().AddVariantSet('coordinateContext')
    for name in ['ECEF', 'Grid']:
        variants.AddVariant(name)
        variants.SetVariantSelection(name)
        with variants.GetVariantEditContext():
            parent.GetReferences().AddReference('./crs-library.usda', '/Definitions/' + name)
    variants.SetVariantSelection('Grid')
    save('variant-selection', variant, [ok('/World/Data', '/World', second)])

    inherited, parent = stage('class-inheritance')
    definition = inherited.CreateClassPrim('/Classes/CRS')
    definition.CreateAttribute('crs:wkt', Sdf.ValueTypeNames.Token, variability=Sdf.VariabilityUniform).Set(first)
    marker(parent)
    parent.GetInherits().AddInherit('/Classes/CRS')
    save('class-inheritance', inherited, [ok('/World/Data', '/World', first)])

    flat = base.Flatten()
    flat.Export(str(directory / 'equivalent-composed-data.usda'))
    jobs.append({'name': 'equivalent-composed-data', 'stage': str(directory / 'equivalent-composed-data.usda'),
                 'load_none': False, 'queries': ['/World/Data', '/World/Independent/Data'],
                 'expected': [ok('/World/Data', '/World', first), ok('/World/Independent/Data', '/World/Independent', second)]})

    payload = Usd.Stage.CreateNew(str(directory / 'payload.usda'))
    payload.DefinePrim('/Payload', 'Xform')
    payload.DefinePrim('/Payload/UnavailableWhenUnloaded', 'Scope')
    payload.GetRootLayer().Save()
    unloaded, parent = stage('unloaded-payload')
    bind(parent, 'ECEF')
    unloaded.DefinePrim('/World/Payload', 'Xform').GetPayloads().AddPayload('./payload.usda', '/Payload')
    save('unloaded-payload', unloaded, [ok('/World/Payload', '/World', first),
         bad('/World/Payload/UnavailableWhenUnloaded', 'Prim is not available in the composed stage')], load_none=True)

    empty, parent = stage('no-binding')
    save('no-binding', empty, [bad('/World/Data', 'No CRS binding in the composed ancestry')])
    broken, parent = stage('broken-nearest-binding')
    bind(parent, 'ECEF')
    child = UsdGeom.Xform.Define(broken, '/World/Broken').GetPrim()
    bind(child, 'Missing')
    broken.DefinePrim('/World/Broken/Data', 'Scope')
    save('broken-nearest-binding', broken, [bad('/World/Broken/Data', 'Nearest direct binding has no authored CRS definition')])

    for name, kind, variability, value, error in [
        ('wrong-wkt-type', Sdf.ValueTypeNames.String, Sdf.VariabilityUniform, first, 'CRS definition must be a token'),
        ('wrong-wkt-variability', Sdf.ValueTypeNames.Token, Sdf.VariabilityVarying, first, 'CRS definition must be uniform'),
        ('empty-wkt', Sdf.ValueTypeNames.Token, Sdf.VariabilityUniform, '', 'CRS definition is empty')]:
        result, parent = stage(name)
        marker(parent)
        parent.CreateAttribute('crs:wkt', kind, variability=variability).Set(value)
        save(name, result, [bad('/World/Data', error)])
    return jobs
