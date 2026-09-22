"""Read-only composed-scene resolution under an explicit experimental profile.

Every spelling and policy in Experiment is a candidate, not an approved schema.
The result is shared by headless queries, export and the native Hydra adapter.
"""
from dataclasses import dataclass, asdict
import hashlib
import math
from functools import lru_cache
from pyproj import CRS
import numpy as np
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt

from geobuild.engine import TransformError
from geobuild.operations import ProjOperations, parse


class SceneError(ValueError):
    pass


@dataclass(frozen=True)
class Experiment:
    carrier: str = "attribute"
    placement: str = "affine"
    units: str = "scene_conventions"
    target: str = "consumer_override"
    geographic_output: str = "reject"
    empty_binding: str = "error"
    project_placement: str = "explicit_on_anchor"
    dependency: str = "layer"
    offset_basis: str = "coordinate_linearization"

    def __post_init__(self):
        choices = {"carrier": ("attribute", "translate"), "placement": ("affine", "per_vertex"),
                   "units": ("scene_conventions", "author_conformed"),
                   "target": ("consumer_override", "scene_locked"),
                   "geographic_output": ("reject", "per_vertex"),
                   "empty_binding": ("error", "inherit"),
                   "project_placement": ("explicit_on_anchor", "ancestor_after_position"),
                   "dependency": ("layer", "default_prim"),
                   "offset_basis": ("coordinate_linearization", "cartesian_tangent")}
        for key, value in asdict(self).items():
            if value not in choices[key]:
                raise ValueError("Unknown experimental choice: " + key)


def definition(stage, path, wkt):
    prim = stage.DefinePrim(path, "GeospatialCRS")
    prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.String).Set(wkt)
    return prim


def bind(prim, target):
    prim.CreateRelationship("crs:binding").SetTargets([target])


def position(prim, value, time=Usd.TimeCode.Default(), carrier="attribute"):
    if carrier == "attribute":
        prim.CreateAttribute("geo:position", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*value), time)
    else:
        prim.CreateAttribute("geo:isAnchor", Sdf.ValueTypeNames.Bool).Set(True)
        xf = UsdGeom.Xformable(prim)
        ops = [op for op in xf.GetOrderedXformOps() if op.GetOpName() == "xformOp:translate:geoPosition"]
        op = ops[0] if ops else xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble, "geoPosition")
        op.Set(Gf.Vec3d(*value), time)


def declare(stage, target_wkt, roots=("/World",), mode="layer"):
    data = {"required": True, "roots": Vt.StringArray(roots), "targetWkt": target_wkt}
    if mode == "layer":
        metadata = dict(stage.GetRootLayer().customLayerData)
        metadata["geospatialBuild"] = data
        stage.GetRootLayer().customLayerData = metadata
    else:
        prim = stage.GetDefaultPrim()
        if not prim:
            raise SceneError("Default-prim dependency candidate requires a default prim")
        prim.SetCustomDataByKey("geospatialBuild", data)


def dependency(stage, mode="layer"):
    # Deliberately no traversal: this is the consumer's cheap preflight query.
    if mode == "layer":
        return dict(stage.GetRootLayer().customLayerData.get("geospatialBuild", {}))
    prim = stage.GetDefaultPrim()
    return dict(prim.GetCustomDataByKey("geospatialBuild") or {}) if prim else {}


def _anchor(prim, experiment):
    return bool(prim.GetAttribute("geo:position")) if experiment.carrier == "attribute" else bool(prim.GetAttribute("geo:isAnchor").Get())


def _binding(prim, experiment):
    while prim and not prim.IsPseudoRoot():
        relationship = prim.GetRelationship("crs:binding")
        if relationship:
            targets = relationship.GetForwardedTargets()
            if not targets and experiment.empty_binding == "inherit":
                prim = prim.GetParent()
                continue
            if len(targets) != 1 or not targets[0].IsPrimPath():
                raise SceneError("CRS binding must resolve to one definition: " + str(prim.GetPath()))
            crs = prim.GetStage().GetPrimAtPath(targets[0])
            if not crs or crs.GetTypeName() != "GeospatialCRS":
                raise SceneError("Binding names no CRS definition: " + str(targets[0]))
            wkt = crs.GetAttribute("crs:wkt").Get()
            parse(wkt)
            return wkt, str(crs.GetPath())
        prim = prim.GetParent()
    raise SceneError("Position has no CRS binding")


def _time(time):
    return time if isinstance(time, Usd.TimeCode) else Usd.TimeCode(time)


def _position(prim, time, experiment):
    name = "geo:position" if experiment.carrier == "attribute" else "xformOp:translate:geoPosition"
    value = prim.GetAttribute(name).Get(time)
    if value is None or len(value) != 3 or not all(math.isfinite(v) for v in value):
        raise SceneError("Missing or non-finite native position: " + str(prim.GetPath()))
    return np.asarray(value, dtype=np.float64)


def _local(prim, time, experiment):
    transform = UsdGeom.Xformable(prim)
    result = Gf.Matrix4d(1)
    if transform:
        for op in transform.GetOrderedXformOps():
            if experiment.carrier == "translate" and _anchor(prim, experiment) and op.GetOpName() == "xformOp:translate:geoPosition":
                continue
            result = op.GetOpTransform(time) * result
    return result


def _relative(prim, anchor, time, experiment):
    result = Gf.Matrix4d(1)
    while prim and not prim.IsPseudoRoot():
        result = result * _local(prim, time, experiment)
        if prim == anchor:
            break
        xf = UsdGeom.Xformable(prim)
        if xf and xf.GetResetXformStack():
            # Candidate: reset offsets within the CRS frame, preserving its position.
            break
        prim = prim.GetParent()
    return np.array(result, dtype=np.float64)


def geometry(prim, time):
    point_based = UsdGeom.PointBased(prim)
    result = {"type": prim.GetTypeName()}
    if point_based:
        if prim.GetTypeName() not in ('Mesh','BasisCurves','Points'):
            raise SceneError('No geometry evaluator registered for '+prim.GetTypeName())
        points = point_based.GetPointsAttr().Get(time)
        points = np.asarray(points if points is not None else [], dtype=np.float64).reshape((-1, 3))
        widths=prim.GetAttribute('widths')
        if widths and widths.Get(time):
            result['widths']=list(widths.Get(time))
        if prim.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(prim)
            result.update(counts=list(mesh.GetFaceVertexCountsAttr().Get(time) or []),
                          indices=list(mesh.GetFaceVertexIndicesAttr().Get(time) or []))
            if sum(result['counts']) != len(result['indices']) or any(i<0 or i>=len(points) for i in result['indices']):
                raise SceneError('Malformed mesh topology: '+str(prim.GetPath()))
        elif prim.IsA(UsdGeom.BasisCurves):
            curves = UsdGeom.BasisCurves(prim)
            if curves.GetTypeAttr().Get(time) != 'linear':
                raise SceneError('This candidate requires explicitly evaluated linear curve segments')
            result.update(counts=list(curves.GetCurveVertexCountsAttr().Get(time) or []))
            if sum(result['counts']) != len(points) or any(n<2 for n in result['counts']):
                raise SceneError('Malformed curve topology: '+str(prim.GetPath()))
    elif prim.IsA(UsdGeom.Cube):
        half = float(UsdGeom.Cube(prim).GetSizeAttr().Get(time)) / 2
        points = np.array([(x, y, z) for x in (-half, half) for y in (-half, half) for z in (-half, half)])
        result.update(type="Mesh", counts=[4] * 6, indices=[0,1,3,2,4,6,7,5,0,4,5,1,2,3,7,6,0,2,6,4,1,5,7,3])
    else:
        if UsdGeom.Gprim(prim):
            raise SceneError('No geometry evaluator registered for ' + prim.GetTypeName())
        points = np.empty((0, 3))
    return points, result


def _homogeneous(points, matrix):
    values = np.column_stack((points, np.ones(len(points)))) @ matrix
    return values[:, :3]


@lru_cache(maxsize=128)
def _geocentric(wkt):
    value=parse(wkt).geodetic_crs.to_json_dict()
    for key in ('id','bbox','area','scope'):
        value.pop(key,None)
    value['type']='GeodeticCRS'
    value['coordinate_system']={'subtype':'Cartesian','axis':[
        {'name':'Geocentric '+axis,'abbreviation':axis,'direction':'geocentric'+axis,'unit':'metre'}
        for axis in 'XYZ']}
    return CRS.from_json_dict(value).to_wkt()


@dataclass
class ResolvedScene:
    target_wkt: str
    time: float | None
    revision: int
    experiment: dict
    prims: dict
    operations: list
    diagnostics: list

    def world_points(self, path):
        prim = self.prims[str(path)]
        return _homogeneous(np.asarray(prim["points"]).reshape((-1, 3)), np.asarray(prim["matrix"]))

    def world_position(self, path):
        return tuple(self.prims[str(path)]["matrix"][3][:3])

    def bounds(self, path="/"):
        arrays = [self.world_points(p) for p, prim in self.prims.items()
                  if (p == path or p.startswith(path.rstrip("/") + "/")) and len(prim["points"])]
        if not arrays:
            raise SceneError("No geometry under requested bound")
        points = np.vstack(arrays)
        return tuple(points.min(axis=0)), tuple(points.max(axis=0))

    def relative_placement(self, path, relative_to):
        if parse(self.target_wkt).is_geographic:
            raise SceneError("Geographic output has no single Euclidean relative-placement matrix; select a Cartesian output")
        return np.asarray(self.prims[str(path)]["matrix"]) @ np.linalg.inv(self.prims[str(relative_to)]["matrix"])

    def snapshot(self):
        return asdict(self)


class SceneResolver:
    def __init__(self, stage, engine=None, experiment=None):
        self.stage = stage
        self.engine = engine or ProjOperations()
        self.experiment = experiment or Experiment()
        self.revision = 0
        self._cache = {}
        self._notice = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._changed, stage)

    def _changed(self, notice, sender):
        self.revision += 1
        self._cache.clear()

    def close(self):
        self._notice.Revoke()

    def validate(self):
        diagnostics = []
        declaration = dependency(self.stage, self.experiment.dependency)
        roots = list(declaration.get("roots", []))
        anchors = []
        for prim in self.stage.Traverse(Usd.TraverseInstanceProxies()):
            if prim.GetRelationship('crs:binding') and not _anchor(prim,self.experiment):
                parent=prim.GetParent()
                while parent and not parent.IsPseudoRoot():
                    if _anchor(parent,self.experiment):
                        diagnostics.append({'severity':'error','path':str(prim.GetPath()),
                            'message':'A CRS override inside an offset chain requires an explicit native position'})
                        break
                    parent=parent.GetParent()
            if _anchor(prim, self.experiment):
                path = str(prim.GetPath())
                anchors.append(path)
                try:
                    _binding(prim, self.experiment)
                except (ValueError, TypeError) as exc:
                    diagnostics.append({"severity": "error", "path": path, "message": str(exc)})
                parent = prim.GetParent()
                while parent and not parent.IsPseudoRoot():
                    if _anchor(parent, self.experiment):
                        diagnostics.append({"severity": "warning", "path": path, "message": "Nested absolute position cuts ancestor placement"})
                        break
                    parent = parent.GetParent()
                if not any(Sdf.Path(path).HasPrefix(Sdf.Path(root)) for root in roots):
                    diagnostics.append({"severity": "error", "path": path, "message": "Position is outside declared dependency coverage"})
            if UsdGeom.Gprim(prim) and any(prim.GetPath().HasPrefix(Sdf.Path(root)) for root in roots):
                ancestor = prim
                while ancestor and not ancestor.IsPseudoRoot() and not _anchor(ancestor, self.experiment):
                    ancestor = ancestor.GetParent()
                if not ancestor or ancestor.IsPseudoRoot():
                    diagnostics.append({"severity": "error", "path": str(prim.GetPath()), "message": "Participating geometry is outside any CRS position"})
        if anchors and not declaration.get("required"):
            diagnostics.append({"severity": "error", "path": "/", "message": "Missing dependency declaration"})
        if declaration.get("required") and not anchors:
            diagnostics.append({"severity": "error", "path": "/", "message": "Stale dependency declaration with no authored positions"})
        return diagnostics

    def resolve(self, time=Usd.TimeCode.Default(), target_wkt=None):
        time = _time(time)
        exp = self.experiment
        baked = self.stage.GetRootLayer().customLayerData.get("geospatialBuildResolved")
        if baked:
            source = baked["targetWkt"]
            output = target_wkt or source
            prims, operations = {}, []
            cache = UsdGeom.XformCache(time)
            for prim in self.stage.Traverse(Usd.TraverseInstanceProxies()):
                if not UsdGeom.Xformable(prim):
                    continue
                points, shape = geometry(prim, time)
                matrix = np.array(cache.GetLocalToWorldTransform(prim))
                if parse(output) != parse(source):
                    world = _homogeneous(points, matrix)
                    values = np.vstack((matrix[3,:3], world))
                    converted = self.engine.convert(source, output, values)
                    operations.append(converted.provenance)
                    matrix = np.eye(4)
                    matrix[3,:3] = converted.coordinates[0]
                    points = np.array(converted.coordinates[1:]).reshape((-1,3)) - matrix[3,:3]
                prims[str(prim.GetPath())] = {**shape, "points": points.tolist(), "matrix": matrix.tolist(),
                    "coordinate_epoch": None, "already_resolved": True}
            return ResolvedScene(output, None if time.IsDefault() else time.GetValue(), self.revision,
                                 asdict(exp), prims, operations, [])
        declaration = dependency(self.stage, exp.dependency)
        scene_target = declaration.get("targetWkt")
        if exp.target == "scene_locked" and target_wkt and scene_target and parse(target_wkt) != parse(scene_target):
            raise SceneError("Consumer target conflicts with scene-locked candidate")
        target_wkt = target_wkt or scene_target
        if not target_wkt:
            raise SceneError("Resolution requires an explicit scene or consumer output CRS")
        target = parse(target_wkt)
        if target.is_geographic and exp.geographic_output != "per_vertex":
            raise SceneError("Geographic scene output rejected by this candidate; coordinate reporting remains available")
        time_value = None if time.IsDefault() else time.GetValue()
        key = time_value, target_wkt
        if key in self._cache:
            return self._cache[key]
        diagnostics = self.validate()
        errors = [d for d in diagnostics if d["severity"] == "error"]
        if errors:
            raise SceneError("Authored validation failed: " + "; ".join(d["path"] + ": " + d["message"] for d in errors))
        prims, operations, kernels, instance_inputs = {}, {}, {}, {}
        scene_meters = UsdGeom.GetStageMetersPerUnit(self.stage)
        up_axis = UsdGeom.GetStageUpAxis(self.stage)
        for prim in self.stage.Traverse(Usd.TraverseInstanceProxies()):
            ancestor = prim
            while ancestor and not ancestor.IsPseudoRoot() and not _anchor(ancestor, exp):
                ancestor = ancestor.GetParent()
            if not ancestor or ancestor.IsPseudoRoot():
                continue
            anchor_path = str(ancestor.GetPath())
            if anchor_path not in kernels:
                source_wkt, crs_path = _binding(ancestor, exp)
                source = parse(source_wkt)
                native = _position(ancestor, time, exp)
                epoch = ancestor.GetAttribute("geo:coordinateEpoch").Get()
                project = ancestor.GetRelationship("geo:projectBinding")
                project_wkt = None
                project_matrix = np.eye(4)
                if project:
                    targets = project.GetForwardedTargets()
                    if len(targets) != 1:
                        raise SceneError("Project placement needs one project CRS")
                    definition_prim = self.stage.GetPrimAtPath(targets[0])
                    project_wkt = definition_prim.GetAttribute("crs:wkt").Get() if definition_prim else None
                    if not project_wkt:
                        raise SceneError("Project placement names no definition")
                    parse(project_wkt)
                    authored = ancestor.GetAttribute("geo:projectTransform").Get(time)
                    if authored is None:
                        raise SceneError("Project placement needs its explicit transform")
                    project_matrix = np.array(authored, dtype=np.float64)
                axis_map = np.eye(3)
                if exp.units == "scene_conventions" and up_axis == UsdGeom.Tokens.y:
                    axis_map = np.array([[1,0,0],[0,0,1],[0,-1,0]], dtype=float)
                metres = scene_meters if exp.units == "scene_conventions" else 1.0
                if source.is_geographic:
                    angular = source.axis_info[0].unit_conversion_factor
                    lat = native[1] * angular
                    e = source.ellipsoid
                    f = 1 / e.inverse_flattening
                    e2 = f * (2 - f)
                    n = e.semi_major_metre / math.sqrt(1 - e2 * math.sin(lat)**2)
                    m = e.semi_major_metre * (1 - e2) / (1 - e2 * math.sin(lat)**2)**1.5
                    if abs(math.cos(lat)) < 1e-12:
                        raise SceneError("Geographic east basis is singular at a pole; use a Cartesian position or an explicit frame")
                    height = native[2] * source.axis_info[2].unit_conversion_factor
                    factors = np.array([1 / angular / ((n + height) * math.cos(lat)),
                                        1 / angular / (m + height), 1 / source.axis_info[2].unit_conversion_factor])
                else:
                    factors = np.array([1 / a.unit_conversion_factor for a in source.axis_info])

                tangent_wkt, tangent_origin, tangent_basis = None, None, None
                if source.is_geographic and exp.offset_basis=='cartesian_tangent':
                    tangent_wkt=_geocentric(source_wkt)
                    converted=self.engine.convert(source_wkt,tangent_wkt,[native],epoch=epoch)
                    operations[str(converted.provenance)]=converted.provenance
                    tangent_origin=np.array(converted.coordinates[0])
                    lon,latitude=native[:2]*source.axis_info[0].unit_conversion_factor
                    sl,cl,sp,cp=math.sin(lon),math.cos(lon),math.sin(latitude),math.cos(latitude)
                    tangent_basis=np.array([[-sl,cl,0],[-sp*cl,-sp*sl,cp],[cp*cl,cp*sl,sp]])

                def convert(offsets, source_wkt=source_wkt, native=native, axis_map=axis_map, metres=metres,
                            factors=factors, epoch=epoch, project_wkt=project_wkt, project_matrix=project_matrix,
                            tangent_wkt=tangent_wkt,tangent_origin=tangent_origin,tangent_basis=tangent_basis):
                    coordinates = native + (np.asarray(offsets) @ axis_map) * metres * factors
                    operation_source=source_wkt
                    if tangent_wkt:
                        coordinates=tangent_origin+((np.asarray(offsets)@axis_map)*metres)@tangent_basis
                        operation_source=tangent_wkt
                    if project_wkt:
                        intermediate = self.engine.convert(operation_source, project_wkt, coordinates, epoch=epoch)
                        operations[str(intermediate.provenance)] = intermediate.provenance
                        coordinates = _homogeneous(np.asarray(intermediate.coordinates), project_matrix)
                        converted = self.engine.convert(project_wkt, target_wkt, coordinates, epoch=epoch)
                    else:
                        converted = self.engine.convert(operation_source, target_wkt, coordinates, epoch=epoch)
                    operations[str(converted.provenance)] = converted.provenance
                    return np.asarray(converted.coordinates, dtype=np.float64)

                origin = convert([[0, 0, 0]])[0]
                step = .25 / metres
                samples = convert(np.vstack((np.eye(3) * step, -np.eye(3) * step)))
                basis = (samples[:3] - samples[3:]) / (2 * step)
                matrix = np.eye(4)
                matrix[:3, :3], matrix[3, :3] = basis, origin
                kernels[anchor_path] = convert, matrix, source_wkt, epoch
            convert, anchor_matrix, source_wkt, epoch = kernels[anchor_path]
            local = _relative(prim, ancestor, time, exp)
            points, shape = geometry(prim, time)
            instance_inputs[str(prim.GetPath())] = points.copy(), local.copy()
            local_to_output = local @ anchor_matrix
            if exp.project_placement == "ancestor_after_position":
                parent = ancestor.GetParent()
                if parent and not parent.IsPseudoRoot():
                    local_to_output = local_to_output @ np.array(UsdGeom.XformCache(time).GetLocalToWorldTransform(parent))
            residual = 0.0
            footprint = 0.0
            if len(points):
                offsets = _homogeneous(points, local)
                exact = convert(offsets)
                affine = _homogeneous(points, local_to_output)
                unit_factors = np.array([a.unit_conversion_factor for a in target.axis_info])
                if not target.is_geographic:
                    residual = float(np.linalg.norm((exact - affine) * unit_factors, axis=1).max())
                footprint = float(np.linalg.norm(offsets * scene_meters, axis=1).max())
                if exp.placement == "per_vertex" or target.is_geographic:
                    # Retain high precision through a double placement plus small local points.
                    local_to_output = np.eye(4)
                    local_to_output[3, :3] = convert([local[3, :3]])[0]
                    points = exact - local_to_output[3, :3]
                allowed = ancestor.GetAttribute("geo:maxErrorMetres").Get()
                if allowed is not None and (not math.isfinite(allowed) or allowed < 0):
                    raise SceneError("Distance budget must be finite and nonnegative")
                if allowed is not None and exp.placement == "affine" and residual > allowed:
                    raise SceneError(f"Placement exceeds the authored distance budget on {prim.GetPath()}: {residual} > {allowed}")
            path = str(prim.GetPath())
            prims[path] = {**shape, "matrix": local_to_output.tolist(), "points": points.tolist(),
                           "anchor": anchor_path, "source_wkt": source_wkt, "coordinate_epoch": epoch,
                           "affine_vertex_error_metres": residual, "sampled_extent_metres": footprint,
                           "bound_scope": "all authored vertices at this evaluation; not a continuous surface bound",
                           "instance_proxy": prim.IsInstanceProxy()}
        # Expand point instances into resolved instance records for every consumer.
        # Prototype geometry is ordinary authored USD, not geospatial implementation.
        prototype_paths = set()
        for prim in self.stage.Traverse():
            if not prim.IsA(UsdGeom.PointInstancer) or str(prim.GetPath()) not in prims:
                continue
            instancer = UsdGeom.PointInstancer(prim)
            prototypes = instancer.GetPrototypesRel().GetTargets()
            prototype_paths.update(str(p) for p in prototypes)
            indices = instancer.GetProtoIndicesAttr().Get(time)
            transforms = instancer.ComputeInstanceTransformsAtTime(time, time,
                UsdGeom.PointInstancer.ExcludeProtoXform, UsdGeom.PointInstancer.IgnoreMask)
            mask = instancer.ComputeMaskAtTime(time)
            base = np.array(prims[str(prim.GetPath())]['matrix'])
            for index, (prototype, transform) in enumerate(zip(indices, transforms)):
                if mask and not mask[index]:
                    continue
                root = str(prototypes[prototype])
                prototype_paths.add(root)
                for path, item in list(prims.items()):
                    if path != root and not path.startswith(root + '/'):
                        continue
                    if item.get('anchor') != prims[str(prim.GetPath())].get('anchor'):
                        raise SceneError('Point-instance prototype has an independent absolute position')
                    original_points, original_local=instance_inputs[path]
                    instancer_local=instance_inputs[str(prim.GetPath())][1]
                    local=original_local @ np.linalg.inv(instancer_local) @ np.array(transform) @ instancer_local
                    convert,anchor_matrix,_,_=kernels[item['anchor']]
                    matrix=local @ anchor_matrix
                    points=original_points
                    if len(points):
                        exact=convert(_homogeneous(points,local))
                        affine=_homogeneous(points,matrix)
                        factors=np.array([a.unit_conversion_factor for a in target.axis_info])
                        error=float(np.linalg.norm((exact-affine)*factors,axis=1).max()) if not target.is_geographic else 0
                        anchor_prim=self.stage.GetPrimAtPath(item['anchor'])
                        budget=anchor_prim.GetAttribute('geo:maxErrorMetres').Get()
                        if budget is not None and exp.placement=='affine' and error>budget:
                            raise SceneError('Instance placement exceeds the authored distance budget')
                        if exp.placement=='per_vertex' or target.is_geographic:
                            matrix=np.eye(4)
                            matrix[3,:3]=convert([local[3,:3]])[0]
                            points=exact-matrix[3,:3]
                    prims[str(prim.GetPath()) + f'/instance_{index}' + path[len(root):]] = {
                        **item, 'matrix': matrix.tolist(), 'points':points.tolist(),
                        'point_instance': index, 'prototype': root}
        for path in list(prims):
            if any(path == root or path.startswith(root + '/') for root in prototype_paths):
                del prims[path]
        result = ResolvedScene(target_wkt, time_value, self.revision, asdict(exp), prims,
                               list(operations.values()), diagnostics)
        self._cache[key] = result
        return result

    def coordinates(self, path, target_wkt, time=Usd.TimeCode.Default(), output_wkt=None):
        result = self.resolve(time, output_wkt)
        record = result.prims[str(path)]
        return self.engine.convert(result.target_wkt, target_wkt, [result.world_position(path)],
                                   epoch=record["coordinate_epoch"])


def export_resolved(results, destination):
    """Explicit baking, with output CRS and sample schedule. Source stage is untouched."""
    if not results or len({r.target_wkt for r in results}) != 1:
        raise SceneError("Export needs samples in one output CRS")
    stage = Usd.Stage.CreateNew(str(destination))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.GetRootLayer().customLayerData = {"geospatialBuildResolved": {
        "targetWkt": results[0].target_wkt,
        "times": Vt.DoubleArray([r.time for r in results if r.time is not None]),
        "sampling": "explicit evaluation at listed times; baked interpolation is not native-CRS interpolation",
        "requiresResolution": False}}
    for result in results:
        time = Usd.TimeCode.Default() if result.time is None else Usd.TimeCode(result.time)
        for path, item in result.prims.items():
            prim = stage.DefinePrim(path, item["type"] if item["type"] in ("Mesh", "BasisCurves", "Points") else "Xform")
            xf = UsdGeom.Xformable(prim)
            ops = xf.GetOrderedXformOps()
            op = ops[0] if ops else xf.AddTransformOp()
            xf.SetResetXformStack(True)
            op.Set(Gf.Matrix4d(*np.asarray(item["matrix"]).reshape(-1)), time)
            if item["points"]:
                if prim.IsA(UsdGeom.Mesh):
                    mesh = UsdGeom.Mesh(prim)
                    mesh.GetFaceVertexCountsAttr().Set(item.get("counts", []))
                    mesh.GetFaceVertexIndicesAttr().Set(item.get("indices", []))
                    mesh.GetSubdivisionSchemeAttr().Set("none")
                elif prim.IsA(UsdGeom.BasisCurves):
                    curves = UsdGeom.BasisCurves(prim)
                    curves.GetCurveVertexCountsAttr().Set(item.get("counts", []))
                    curves.GetTypeAttr().Set("linear")
                    curves.GetWrapAttr().Set("nonperiodic")
                UsdGeom.PointBased(prim).GetPointsAttr().Set([Gf.Vec3f(*p) for p in item["points"]], time)
    stage.GetRootLayer().Save()
    return stage
