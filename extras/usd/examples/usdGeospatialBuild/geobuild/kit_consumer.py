"""Run inside Kit: resolved geometry in Fabric, leaving authored USD untouched."""
import json
import os
from pathlib import Path
import traceback


def main():
    import omni.usd
    import omni.kit.app
    import usdrt
    context=omni.usd.get_context()
    context.new_stage()
    authored=context.get_stage()
    before=authored.GetRootLayer().ExportToString()
    stage=usdrt.Usd.Stage.Attach(context.get_stage_id())
    frames=json.loads(Path(os.environ['GEO_KIT_INPUT']).read_text(encoding='utf-8'))['frames']
    output=[]
    previous=set()
    for frame in frames:
        current=set(frame['prims'])
        for path in previous-current:
            stage.RemovePrim(path)
        values={}
        for path,item in frame['prims'].items():
            prim=stage.DefinePrim(path,item['type'] if item['type'] in ('Mesh','BasisCurves','Points') else 'Xform')
            matrix=item['matrix']
            # Fold the full linear part, including shear, into small local points;
            # preserve the large placement separately in Fabric's double position.
            points=[tuple(sum(p[k]*matrix[k][j] for k in range(3)) for j in range(3)) for p in item['points']]
            prim.CreateAttribute('points',usdrt.Sdf.ValueTypeNames.Point3fArray).Set(usdrt.Vt.Vec3fArray([usdrt.Gf.Vec3f(*p) for p in points]))
            xform=usdrt.Rt.Xformable(prim)
            xform.CreateWorldPositionAttr(usdrt.Gf.Vec3d(*matrix[3][:3]))
            xform.CreateWorldOrientationAttr(usdrt.Gf.Quatf(1))
            xform.CreateWorldScaleAttr(usdrt.Gf.Vec3f(1))
            if item['type']=='Mesh':
                prim.CreateAttribute('faceVertexCounts',usdrt.Sdf.ValueTypeNames.IntArray).Set(usdrt.Vt.IntArray(item.get('counts',[])))
                prim.CreateAttribute('faceVertexIndices',usdrt.Sdf.ValueTypeNames.IntArray).Set(usdrt.Vt.IntArray(item.get('indices',[])))
            if item['type']=='BasisCurves':
                prim.CreateAttribute('curveVertexCounts',usdrt.Sdf.ValueTypeNames.IntArray).Set(usdrt.Vt.IntArray(item.get('counts',[])))
                prim.CreateAttribute('type',usdrt.Sdf.ValueTypeNames.Token).Set('linear')
            actual=prim.GetAttribute('points').Get()
            origin=xform.GetWorldPositionAttr().Get()
            if len(actual)!=len(points):
                raise RuntimeError('Fabric rejected a point array on '+path)
            if points:
                lo=usdrt.Gf.Vec3d(*(min(p[j] for p in actual)+origin[j] for j in range(3)))
                hi=usdrt.Gf.Vec3d(*(max(p[j] for p in actual)+origin[j] for j in range(3)))
                usdrt.Rt.Boundable(prim).CreateWorldExtentAttr(usdrt.Gf.Range3d(lo,hi))
            values[path]={'world_points':[[float(p[j])+float(origin[j]) for j in range(3)] for p in actual],
                          'origin':list(origin)}
        output.append({'prims':values,'removed':sorted(previous-current)})
        previous=current
    assert authored.GetRootLayer().ExportToString()==before, 'Fabric adapter modified authored USD'
    extensions=omni.kit.app.get_app().get_extension_manager().get_extensions()
    enabled=[e['id'] for e in extensions if e.get('enabled')]
    assert not any('geospatial' in name.lower() for name in enabled)
    return {'frames':output,'authored_unchanged':True,'kit_version':omni.kit.app.get_app().get_build_version(),
            'consumer':'USDRT Fabric world placement','enabled_extensions':enabled}


if __name__=='__main__':
    import omni.kit.app
    code=0
    try:
        result=main()
    except Exception:
        code=1
        result={'error':traceback.format_exc()}
    Path(os.environ['GEO_KIT_OUTPUT']).write_text(json.dumps(result),encoding='utf-8')
    omni.kit.app.get_app().post_quit(code)
