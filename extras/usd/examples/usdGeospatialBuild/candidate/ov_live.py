"""Actual Omniverse geometry writeback; shares the Python interpretation/PROJ.

Runtime-only point/matrix writes never become additional authored source facts.
"""
import os,sys,json,asyncio,traceback
from pathlib import Path
import omni.kit.app,omni.usd

async def main():
    config=json.loads(Path(os.environ['GEOBUILD_OV_JOB']).read_text())
    for p in config['python_paths']:sys.path.append(p)
    sys.path.insert(0,config['source'])
    import numpy as np,usdrt
    from pxr import Usd,UsdGeom,Gf,Sdf,Tf,Plug
    Plug.Registry().RegisterPlugins(config['source']+'/schema/generated/plugInfo.json')
    from pyproj import datadir,network
    datadir.append_data_dir(config['grids']);network.set_network_enabled(False)
    from candidate.execution import execute_python
    from candidate.runtime import Runtime,factors
    app=omni.kit.app.get_app();out={'jobs':[],'implementation':'shared candidate Python runtime and PROJ; separate live geometry sink','app_version':app.get_app_version()}
    for job in config['jobs']:
        context=omni.usd.get_context();await context.open_stage_async(job['stage']);stage=context.get_stage()
        if stage is None:raise RuntimeError('Live source stage did not open')
        protected=[(l,l.permissionToEdit) for l in stage.GetUsedLayers() if l!=stage.GetSessionLayer()]
        for layer,_ in protected:layer.SetPermissionToEdit(False)
        before={l.identifier:l.ExportToString() for l in stage.GetUsedLayers()}
        rt=usdrt.Usd.Stage.Attach(context.get_stage_id());dirty=[True];state={};notices=[0]
        def on_change(n,s):dirty[0]=True;notices[0]+=1
        notice=Tf.Notice.Register(Usd.Notice.ObjectsChanged,on_change,stage)
        def apply(record):
            r=Runtime(stage,job['output_wkt'],job['time']);readback={}
            for path,values in record['geometry'].items():
                coordinates=np.array(values);center=coordinates[0];local=r.stage_coordinates(coordinates,center)
                source_path=record.get('geometry_sources',{}).get(path,path);source=stage.GetPrimAtPath(source_path);rp=rt.GetPrimAtPath(path)
                if not rp:
                    prototype=rt.GetPrimAtPath(source_path)
                    if not prototype or not prototype.GetAttribute('points'):raise RuntimeError('Instance prototype was not ingested')
                    rp=rt.DefinePrim(path,source.GetTypeName())
                    for name in ['points','faceVertexCounts','faceVertexIndices','curveVertexCounts','widths']:
                        original=prototype.GetAttribute(name)
                        if original:rp.CreateAttribute(name,original.GetTypeName(),True).Set(original.Get())
                attribute=rp.GetAttribute('points')
                if not attribute or len(attribute.Get())!=len(source.GetAttribute('points').Get(Usd.TimeCode(job['time']))):raise RuntimeError('Live source geometry was not ingested')
                attribute.Set(usdrt.Vt.Vec3fArray([usdrt.Gf.Vec3f(*map(float,p)) for p in local]))
                matrix=np.eye(4);matrix[3,:3]=(center*factors(r.output))@r.B.T/r.unit
                x=usdrt.Rt.Xformable(rp);world=x.CreateFabricHierarchyWorldMatrixAttr();world.Set(usdrt.Gf.Matrix4d(*matrix.ravel().tolist()))
                raw=np.array(attribute.Get(),float);m=np.array(world.Get(),float)
                actual=(np.c_[raw,np.ones(len(raw))]@m)[:,:3]@r.B*r.unit/factors(r.output)
                error=float(np.max(np.linalg.norm((actual-coordinates)*factors(r.output),axis=1)))
                if error>.001:raise RuntimeError(f'Live geometry readback exceeded 1mm: {path} {error}')
                usdrt.UsdGeom.Imageable(rp).CreateVisibilityAttr().Set('inherited')
                readback[path]={'vertices':len(raw),'max_metric_error':error,'first_native_coordinate':actual[0].tolist()}
            return readback
        def refresh(event):
            if not dirty[0]:return
            dirty[0]=False
            try:
                record=execute_python(job,stage);state.update(record=record,readback=apply(record),error=None)
            except Exception as e:
                for path in state.get('readback',{}):usdrt.UsdGeom.Imageable(rt.GetPrimAtPath(path)).CreateVisibilityAttr().Set('invisible')
                state.update(record=None,error=str(e))
        sub=app.get_update_event_stream().create_subscription_to_pop(refresh,name='candidate-geometry-refresh')
        for _ in range(3):await app.next_update_async()
        if state.get('error') or not state.get('record'):raise RuntimeError('Initial live resolve failed: '+str(state.get('error')))
        original=state['record'];readback=state['readback'];edit_checks=[]
        anchors=[p for p in stage.Traverse() if p.GetAttribute('crs:position').HasAuthoredValue()]
        if job.get('geometry') and anchors:
            # Session edits exercise notice/update recovery; source layer files remain unchanged.
            anchor=next((p for p in anchors if any(path.startswith(str(p.GetPath())+'/') or path==str(p.GetPath()) for path in original['geometry'])),anchors[0])
            with Usd.EditContext(stage,stage.GetSessionLayer()):
                a=anchor.GetAttribute('crs:position');value=a.Get(Usd.TimeCode(job['time']));a.Set(Gf.Vec3d(value[0]+10,value[1],value[2]),Usd.TimeCode(job['time']))
            await app.next_update_async()
            if state.get('error') or not state.get('record') or state['record']['geometry']==original['geometry']:raise RuntimeError('Source edit did not update runtime geometry')
            edit_checks.append({'kind':'source placement edit','notice_received':notices[0]>0,'geometry_changed':True,'readback_verified':True})
            stage.GetSessionLayer().ImportFromString(before[stage.GetSessionLayer().identifier]);dirty[0]=True;await app.next_update_async()
            with Usd.EditContext(stage,stage.GetSessionLayer()):anchor.GetAttribute('crs:wkt').Set('GEODCRS[broken]')
            await app.next_update_async()
            if state.get('record') is not None or not state.get('error'):raise RuntimeError('Invalid definition retained a successful result')
            hidden=all(usdrt.UsdGeom.Imageable(rt.GetPrimAtPath(path)).GetVisibilityAttr().Get()=='invisible' for path in readback)
            if not hidden:raise RuntimeError('Failed resolution left stale live geometry visible')
            edit_checks.append({'kind':'invalid definition','whole_result_rejected':True,'stale_geometry_hidden':True})
            stage.GetSessionLayer().ImportFromString(before[stage.GetSessionLayer().identifier]);dirty[0]=True;await app.next_update_async()
            if state.get('error'):raise RuntimeError('Source recovery failed')
            edit_checks.append({'kind':'valid definition restored','recovered':True})
        after={l.identifier:l.ExportToString() for l in stage.GetUsedLayers()}
        if after!=before:
            import difflib
            differences=[]
            for identifier in set(before)|set(after):
                if before.get(identifier)!=after.get(identifier):
                    differences.extend(difflib.unified_diff(before.get(identifier,'').splitlines(),after.get(identifier,'').splitlines(),fromfile=identifier+' before',tofile=identifier+' after'))
            Path(config['output']).with_suffix('.source-diff.txt').write_text('\n'.join(differences),encoding='utf-8')
            raise RuntimeError('Live candidate changed source USD layers: '+job['name'])
        out['jobs'].append({'name':job['name'],'records':original,'geometry_writeback':readback,'edit_checks':edit_checks,'source_unchanged':True})
        for layer,permission in protected:layer.SetPermissionToEdit(permission)
        print('Live candidate complete: '+job['name'],flush=True);sub=None;notice.Revoke();await context.close_stage_async()
    Path(config['output']).write_text(json.dumps(out),encoding='utf-8');app.post_quit(0)

async def guard():
    try:await main()
    except Exception:
        error=traceback.format_exc();Path(os.environ['GEOBUILD_OV_ERROR']).write_text(error);print(error);omni.kit.app.get_app().post_quit(1)
asyncio.ensure_future(guard())
