"""Composition controls derived from the shared proposal, without placement fields."""
from pathlib import Path
import re
from pxr import Usd, UsdGeom, Sdf, Gf
from review.wkt_profile import normalize


def source_definitions(root):
    text = (Path(root) / 'proposal/proposal-source.txt').read_text(encoding='utf-8')
    definitions = []
    for heading in ['### 3D Geocentric (ECEF) with dynamic datum', '### Compound CRS: NAD83 / California zone 5 (ftUS) + NAVD88 height']:
        section = text.split(heading, 1)[1]
        definitions.append(normalize(re.search(r'```lisp\n(.*?)\n```', section, re.S).group(1)))
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
    jobs.extend(placement_jobs(directory, first))
    jobs.extend(origin_jobs(root, directory))
    return jobs


def placement_jobs(directory, wkt):
    """Expected source records are specified before any consumer reads them."""
    jobs = []
    for name in ['placement-defaults', 'placement-linear', 'placement-held',
                 'geographic-no-unwrapping', 'same-crs-independent-anchor',
                 'position-missing', 'orientation-blocked', 'position-wrong-type',
                 'position-wrong-variability', 'nonfinite-scale', 'zero-quaternion',
                 'singular-source-scale']:
        stage = Usd.Stage.CreateNew(str(directory/(name+'.usda')))
        UsdGeom.SetStageMetersPerUnit(stage, .01)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        parent = UsdGeom.Xform.Define(stage, '/Model').GetPrim()
        marker(parent)
        parent.GetReferences().AddReference('./crs-library.usda', '/Definitions/ECEF')
        # An ordinary transform is deliberately unrelated to the source tuple.
        UsdGeom.Xformable(parent).AddTranslateOp().Set((1000, 2000, 3000))
        p = parent.CreateAttribute('crs:position', Sdf.ValueTypeNames.Double3, custom=False)
        p.Set((10., 20., 30.))
        expected_position = [10., 20., 30.]
        expected_orientation = {'real': 1., 'imaginary': [0., 0., 0.]}
        expected_scale = [1., 1., 1.]
        time, interpolation = 5., 'linear'
        query, owner, error = '/Model', '/Model', None
        if name in ['placement-linear', 'placement-held']:
            p.Clear()
            p.Set((0., 0., 1.), 0)
            p.Set((10., 20., 3.), 10)
            orientation = parent.CreateAttribute('crs:orientation', Sdf.ValueTypeNames.Quatd, custom=False)
            orientation.Set(Gf.Quatd(1., Gf.Vec3d(0)), 0)
            orientation.Set(Gf.Quatd(0., Gf.Vec3d(0, 0, 1)), 10)
            if name == 'placement-held':
                interpolation = 'held'
                expected_position = [0., 0., 1.]
            else:
                expected_position = [5., 10., 2.]
                expected_orientation = {'real': 2**-.5, 'imaginary': [0., 0., 2**-.5]}
        elif name == 'geographic-no-unwrapping':
            # This is a source-coordinate interpolation control, not projection.
            from review.fixture_definitions import GEOGRAPHIC
            wkt_for_job = GEOGRAPHIC
            parent.CreateAttribute('crs:wkt', Sdf.ValueTypeNames.Token,
                                   custom=False, variability=Sdf.VariabilityUniform).Set(wkt_for_job)
            p.Clear()
            p.Set((179., 48., 50.), 0)
            p.Set((-179., 48., 150.), 10)
            expected_position = [0., 48., 100.]
        elif name == 'same-crs-independent-anchor':
            child = UsdGeom.Xform.Define(stage, '/Model/Independent').GetPrim()
            marker(child)
            child.GetReferences().AddReference('./crs-library.usda', '/Definitions/ECEF')
            child.CreateAttribute('crs:position', Sdf.ValueTypeNames.Double3, custom=False).Set((20., 40., 60.))
            query = owner = '/Model/Independent'
            expected_position = [20., 40., 60.]
        elif name == 'position-missing':
            p.Clear()
            error = 'Placement position is unavailable'
        elif name == 'orientation-blocked':
            parent.CreateAttribute('crs:orientation', Sdf.ValueTypeNames.Quatd, custom=False).Block()
            error = 'Placement orientation is unavailable'
        elif name == 'position-wrong-type':
            parent.RemoveProperty('crs:position')
            parent.CreateAttribute('crs:position', Sdf.ValueTypeNames.Float3, custom=False).Set((10., 20., 30.))
            # A registered schema can supply its built-in type to CreateAttribute.
            # Deliberately author the invalid declaration in Sdf, then verify it.
            stage.GetRootLayer().GetAttributeAtPath('/Model.crs:position').SetInfo('typeName','float3')
            error = 'Placement position has wrong type'
        elif name == 'position-wrong-variability':
            parent.RemoveProperty('crs:position')
            parent.CreateAttribute('crs:position', Sdf.ValueTypeNames.Double3,
                                   custom=False, variability=Sdf.VariabilityUniform).Set((10., 20., 30.))
            stage.GetRootLayer().GetAttributeAtPath('/Model.crs:position').SetInfo('variability',Sdf.VariabilityUniform)
            error = 'Placement position must be varying'
        elif name == 'nonfinite-scale':
            parent.CreateAttribute('crs:scale', Sdf.ValueTypeNames.Double3, custom=False).Set((1., float('nan'), 1.))
            error = 'Undocumented crs:scale is not an input'
        elif name == 'zero-quaternion':
            parent.CreateAttribute('crs:orientation', Sdf.ValueTypeNames.Quatd, custom=False).Set(Gf.Quatd(0.))
            error = 'Placement orientation is a zero quaternion'
        elif name == 'singular-source-scale':
            parent.CreateAttribute('crs:scale', Sdf.ValueTypeNames.Double3, custom=False).Set((0., -1., 2.))
            error = 'Undocumented crs:scale is not an input'
        stage.GetRootLayer().Save()
        value = {'prim': query, 'success': not bool(error)}
        if error:
            value['error'] = error
        else:
            value.update(binding_prim=owner,
                         wkt=GEOGRAPHIC if name == 'geographic-no-unwrapping' else wkt,
                         position=expected_position, orientation=expected_orientation)
        jobs.append({'name': name, 'stage': str(directory/(name+'.usda')), 'kind': 'placement_values',
                     'load_none': False, 'time': time, 'interpolation': interpolation,
                     'queries': [query], 'expected': [value]})
    return jobs


def origin_jobs(root, directory):
    """Provider points are illustrative anchor origins, not a measurement carrier."""
    import json
    import math
    from pyproj import CRS
    from review.fixture_definitions import GEOGRAPHIC
    jobs = []
    controls = json.loads((Path(root)/'data/partner-controls.json').read_text())
    ecef = ('GEODCRS["WGS 84",DATUM["World Geodetic System 1984",'
            'ELLIPSOID["WGS 84",6378137.0,298.257223563,LENGTHUNIT["metre",1.0]]],'
            'PRIMEM["Greenwich",0.0,ANGLEUNIT["degree",0.0174532925199433]],'
            'CS[Cartesian,3],AXIS["X",geocentricX,ORDER[1],LENGTHUNIT["metre",1.0]],'
            'AXIS["Y",geocentricY,ORDER[2],LENGTHUNIT["metre",1.0]],'
            'AXIS["Z",geocentricZ,ORDER[3],LENGTHUNIT["metre",1.0]]]')

    def author(name, source, target, positions, expected, time=5., tolerance=.002, ordinary=False):
        stage = Usd.Stage.CreateNew(str(directory/(name+'.usda')))
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, .01)
        stage.SetTimeCodesPerSecond(48.)
        definition = stage.DefinePrim('/Definition', 'CoordinateReferenceSystem')
        definition.CreateAttribute('crs:wkt', Sdf.ValueTypeNames.Token, custom=False,
                                   variability=Sdf.VariabilityUniform).Set(normalize(source))
        paths, rows = [], []
        for index, (position, expectation) in enumerate(zip(positions, expected)):
            path = '/Anchor'+str(index)
            prim = UsdGeom.Xform.Define(stage, path).GetPrim()
            marker(prim)
            prim.GetReferences().AddInternalReference('/Definition')
            attr = prim.CreateAttribute('crs:position', Sdf.ValueTypeNames.Double3, custom=False)
            if isinstance(position, dict):
                for moment, value in position.items(): attr.Set(Gf.Vec3d(*value), moment)
            else: attr.Set(Gf.Vec3d(*position))
            if ordinary: UsdGeom.Xformable(prim).AddTranslateOp().Set((1.,2.,3.))
            paths.append(path)
            if isinstance(expectation, str): rows.append({'prim':path,'success':False,'error':expectation})
            else: rows.append({'prim':path,'success':True,'coordinates':expectation})
        stage.GetRootLayer().Save()
        target=normalize(target)
        roles={axis.direction:axis.unit_conversion_factor for axis in CRS.from_wkt(target).axis_info}
        factors=[roles.get('east',roles.get('geocentricX')),roles.get('north',roles.get('geocentricY')),roles.get('up',roles.get('geocentricZ'))]
        jobs.append({'name':name,'kind':'origin_coordinates','stage':str(directory/(name+'.usda')),
                     'queries':paths,'expected':rows,'load_none':False,'time':time,'interpolation':'linear',
                     'output_wkt':target,'output_length_factors':factors,'acceptance_metres':tolerance,
                     'fixture_role':'direct anchor origins only; no geometry or measurement-domain association'})

    for source,target in [('France_01','France_02'),('France_02','France_01'),
                           ('Colorado_02','Colorado_03'),('Colorado_03','Colorado_02')]:
        author('origins-'+source+'-to-'+target,controls[source]['wkt'],controls[target]['wkt'],
               controls[source]['points'],controls[target]['points'])
    for time in [0.,5.,10.]:
        longitude=-1.+time/5.
        angle=math.radians(longitude)
        expected=[6378137.*math.cos(angle),6378137.*math.sin(angle),0.]
        author('origin-source-interpolation-'+str(int(time)),GEOGRAPHIC,ecef,
               [{0.:(-1.,0.,0.),10.:(1.,0.,0.)}],[expected],time=time,tolerance=2e-8)
    author('origin-adjustment-stops',GEOGRAPHIC,ecef,[(0.,0.,0.)],
           ['Ordinary-adjustment frame is unspecified; origin query stopped'],ordinary=True)
    author('origin-invalid-latitude',GEOGRAPHIC,ecef,[(0.,100.,0.)],
           ['Coordinate operation failed; no substitute'])

    # Consumer-selected output takes precedence; otherwise use composed defaultPrim.
    for name,default in [('origin-default-output',True),('origin-no-default-output',False)]:
        author(name,GEOGRAPHIC,ecef,[(0.,0.,10.)],[[0.,0.,10.]] if default else ['No usable output CRS on composed defaultPrim'])
        job=jobs[-1]; stage=Usd.Stage.Open(job['stage'])
        if default: stage.SetDefaultPrim(stage.GetPrimAtPath('/Anchor0'))
        stage.GetRootLayer().Save()
        job['output_wkt']=''
        job['comparison_kind']='exact_source_components'
        job['output_length_factors']=None # Geographic identity is not a length metric.
    for name,path in [('origin-descendant-stops','/Anchor0/Child'),('origin-nested-anchor-stops','/Assembly/Anchor')]:
        author(name,GEOGRAPHIC,ecef,[(0.,0.,0.)],['This origin adapter supports only direct top-level anchors; dependent frame request stopped'])
        job=jobs[-1]; stage=Usd.Stage.Open(job['stage'])
        if name=='origin-descendant-stops': UsdGeom.Xform.Define(stage,path)
        else:
            prim=UsdGeom.Xform.Define(stage,path).GetPrim(); marker(prim)
            prim.GetReferences().AddInternalReference('/Definition')
            prim.CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3,custom=False).Set((0.,0.,0.))
        stage.GetRootLayer().Save(); job['queries']=[path]; job['expected'][0]['prim']=path
    return jobs
