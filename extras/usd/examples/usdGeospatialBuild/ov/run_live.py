"""Executed inside the installed OV runtime against authored USD, not a snapshot."""
import os,sys,asyncio,json,traceback,hashlib
from pathlib import Path
import omni.kit.app,omni.usd

async def main():
    job=json.loads(Path(os.environ['GEOBUILD_OV_JOB']).read_text());sys.path.append(job['python_dependencies']);sys.path.insert(0,job['source']+'/ov')
    import numpy as np
    from pyproj import datadir
    datadir.append_data_dir(job['grids'])
    from pxr import Usd,Gf,Sdf,Tf,Plug
    Plug.Registry().RegisterPlugins(job['source']+'/schema/generated/plugInfo.json')
    import usdrt
    from independent import OVResolver
    app=omni.kit.app.get_app();output={'app_version':app.get_app_version(),'usd_version':list(Usd.GetVersion()),'jobs':[]}
    for cfg in job['jobs']:
        print('OV source job: '+cfg['name'],flush=True)
        context=omni.usd.get_context();ok=await context.open_stage_async(cfg['stage'])
        stage=context.get_stage()
        if stage is None:raise RuntimeError('OV failed to open authored source')
        before={l.identifier:l.ExportToString() for l in stage.GetUsedLayers()};r=OVResolver(stage,cfg['output_wkt']);time=Usd.TimeCode(cfg.get('time',0))
        rt=usdrt.Usd.Stage.Attach(context.get_stage_id());dirty=[True];notices=[0]
        def on_notice(n,s):dirty[0]=True;notices[0]+=1
        notice=Tf.Notice.Register(Usd.Notice.ObjectsChanged,on_notice,stage)
        rec=r.records(time)
        def apply(rec):
            for path,v in rec['measurements'].items():
                ppath=path.split('.')[0];p=rt.DefinePrim(ppath)
                a=p.CreateAttribute('resolved:coordinates',usdrt.Sdf.ValueTypeNames.Double3Array,True);a.Set(usdrt.Vt.Vec3dArray([usdrt.Gf.Vec3d(*q) for q in v]))
                p.CreateAttribute('resolved:valid',usdrt.Sdf.ValueTypeNames.Bool,True).Set(True)
                if not np.allclose(np.array(a.Get()),v,rtol=0,atol=1e-9):raise RuntimeError('Runtime measurement coordinate readback mismatch')
            if r.output.is_geographic:return {'kind':'coordinate queries only; geographic rendering frame undefined','measurement_readback':len(rec['measurements'])}
            matrices={}
            fac=r.factors(r.output);unit=UsdGeom.GetStageMetersPerUnit(stage)
            axes=np.eye(3) if UsdGeom.GetStageUpAxis(stage)=='Z' else np.array([[1,0,0],[0,0,-1],[0,1,0]])
            for path,m in rec['frames'].items():
                m=np.array(m);m[:,:3]=(m[:,:3]*fac/unit)@axes
                p=rt.DefinePrim(path);x=usdrt.Rt.Xformable(p)
                # Actual runtime matrix, never a source USD matrix authoring operation.
                a=x.CreateFabricHierarchyWorldMatrixAttr();a.Set(usdrt.Gf.Matrix4d(*m.ravel().tolist()));matrices[path]=[list(row) for row in a.Get()]
            consumed={}
            for path in rec['geometry']:
                source=stage.GetPrimAtPath(path);rp=rt.DefinePrim(path,source.GetTypeName());raw=np.array(rp.GetAttribute('points').Get(),dtype=float)
                if raw.shape!=np.array(source.GetAttribute('points').Get(time)).shape:raise RuntimeError('Source geometry was not ingested by OV')
                root,_=r.scope(source);local=Gf.Matrix4d(1);q=source
                while q!=root:
                    x=UsdGeom.Xformable(q)
                    if x:
                        local=local*x.GetLocalTransformation(time)
                        if x.GetResetXformStack():break
                    q=q.GetParent()
                matrix=np.array(matrices[str(root.GetPath())]);v=np.column_stack([raw,np.ones(len(raw))])@np.array(local)@matrix
                actual=v[:,:3]@axes.T*unit/fac
                if not np.allclose(actual,rec['geometry'][path],rtol=0,atol=1e-6):raise RuntimeError('OV source geometry + live runtime matrix differs from derived placement')
                consumed[path]={'source_vertices':len(raw),'max_coordinate_readback_error':float(np.linalg.norm(actual-np.array(rec['geometry'][path]),axis=1).max()),'first_resolved_coordinate':actual[0].tolist()}
            return {'matrices':matrices,'measurement_readback':len(rec['measurements']),'geometry_readback':consumed}
        from pxr import UsdGeom
        live=apply(rec)
        state={'records':rec,'live':live,'error':None,'updates':0}
        def refresh(event):
            if not dirty[0]:return
            dirty[0]=False
            try:
                current=r.records(time);state['live']=apply(current);state['records']=current;state['error']=None;state['updates']+=1
                for path in current['frames']:
                    p=rt.DefinePrim(path);a=usdrt.UsdGeom.Imageable(p).CreateVisibilityAttr();a.Set(UsdGeom.Imageable(stage.GetPrimAtPath(path)).GetVisibilityAttr().Get())
            except Exception as e:
                state['records']=None;state['error']=str(e)
                for path in rec['frames']:
                    p=rt.DefinePrim(path);usdrt.UsdGeom.Imageable(p).CreateVisibilityAttr().Set('invisible')
                for path in rec['measurements']:
                    p=rt.DefinePrim(path.split('.')[0]);p.CreateAttribute('resolved:coordinates',usdrt.Sdf.ValueTypeNames.Double3Array,True).Set(usdrt.Vt.Vec3dArray([]));p.CreateAttribute('resolved:valid',usdrt.Sdf.ValueTypeNames.Bool,True).Set(False)
        subscription=app.get_update_event_stream().create_subscription_to_pop(refresh,name='geospatial-source-invalidation')
        for _ in range(4):await app.next_update_async()
        edits=[]
        for p in stage.Traverse():
            a=p.GetAttribute('crs:position')
            if a and a.HasAuthoredValue():
                old=a.Get(time);previous_notices=notices[0];a.Set(Gf.Vec3d(old[0]+10,old[1],old[2]),time)
                await app.next_update_async()
                if notices[0]<=previous_notices:raise RuntimeError('Source placement edit did not issue a USD notice')
                new=state['records'];updated=state['live']
                if state['error'] or new is None:raise RuntimeError('Valid placement edit failed live resolution: '+str(state['error']))
                if np.array_equal(rec['frames'][str(p.GetPath())],new['frames'][str(p.GetPath())]):raise RuntimeError('Live runtime did not recompute placement')
                edits.append({'path':str(p.GetPath()),'before_origin':rec['frames'][str(p.GetPath())][3][:3],'after_origin':new['frames'][str(p.GetPath())][3][:3],'notice_received':True,'runtime_matrix_readback':updated['matrices'][str(p.GetPath())]})
                # Revert the deliberate authoring test; preserve layer contents exactly afterwards.
                for l in stage.GetUsedLayers():
                    if l.identifier in before:l.ImportFromString(before[l.identifier])
                dirty[0]=True
                await app.next_update_async();break
        failures=[]
        if rec['frames'] or rec['measurements']:
            cp=next(p for p in stage.Traverse() if p.GetAttribute('crs:wkt'))
            cp.GetAttribute('crs:wkt').Set('GEODCRS[broken]');dirty[0]=True
            await app.next_update_async()
            if not state['error'] or state['records'] is not None:raise RuntimeError('Invalid source edit retained a successful placement result')
            hidden=all(usdrt.UsdGeom.Imageable(rt.GetPrimAtPath(path)).GetVisibilityAttr().Get()=='invisible' for path in rec['frames'])
            if not hidden:raise RuntimeError('Failed source edit left a visible stale placement')
            cleared=all(not rt.GetPrimAtPath(path.split('.')[0]).GetAttribute('resolved:valid').Get() and len(rt.GetPrimAtPath(path.split('.')[0]).GetAttribute('resolved:coordinates').Get())==0 for path in rec['measurements'])
            if not cleared:raise RuntimeError('Failed source edit retained stale measurement results')
            failures.append({'error_reported':state['error'],'whole_result_rejected':True,'stale_models_hidden':True,'stale_measurements_cleared':True})
            for l in stage.GetUsedLayers():
                if l.identifier in before:l.ImportFromString(before[l.identifier])
            dirty[0]=True
            await app.next_update_async()
            if state['error']:raise RuntimeError('Valid source did not recover after restoring definition')
        requests=[]
        if cfg['name'].startswith('composition-') or cfg['name']=='climate-ecef-t0':
            baseline_time=time;time=Usd.TimeCode(time.GetValue()+1);dirty[0]=True;await app.next_update_async()
            expected=r.records(time)
            if state['error'] or state['records']!=expected:raise RuntimeError('Time request did not update live results')
            requests.append({'changed':'USD time','verified_against_new_request':True});time=baseline_time
            from pyproj import CRS
            baseline_crs=r.output;r.output=CRS.from_epsg(4979) if cfg['name']=='climate-ecef-t0' else CRS.from_epsg(4978) if not baseline_crs.is_geocentric else CRS.from_epsg(32631).to_3d();dirty[0]=True;await app.next_update_async()
            if state['error'] or state['records']!=r.records(time):raise RuntimeError('Output selection did not update live results')
            requests.append({'changed':'requested output CRS','verified_against_new_request':True});r.output=baseline_crs;dirty[0]=True;await app.next_update_async()
        unchanged=all(l.ExportToString()==before[l.identifier] for l in stage.GetUsedLayers() if l.identifier in before)
        if not unchanged:raise RuntimeError('OV resolver changed authored layers')
        subscription=None;notice.Revoke();output['jobs'].append({'name':cfg['name'],'records':rec,'live_runtime':live,'edits':edits,'requests':requests,'failures':failures,'live_updates':state['updates'],'source_unchanged':unchanged,'source_ingested':True})
        print('OV completed: '+cfg['name'],flush=True)
        await context.close_stage_async()
    Path(job['output']).write_text(json.dumps(output)+'\n');app.post_quit(0)

async def guard():
    try:await main()
    except Exception:
        p=os.environ.get('GEOBUILD_OV_ERROR');t=traceback.format_exc();print(t)
        if p:Path(p).write_text(t)
        omni.kit.app.get_app().post_quit(1)
asyncio.ensure_future(guard())
