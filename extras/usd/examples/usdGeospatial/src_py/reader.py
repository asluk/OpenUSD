#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""USD model queries: points, scene charts, vectors, bounds and occurrences.

Start at Reader.points for the usual query. placement.ModelMap owns transform
ordering; crs.Engine owns coordinate conversions. These callable interfaces
are implementation choices, not proposed USD standard APIs.
"""

import numpy as np
from pxr import Usd, UsdGeom
from common import Failure, require, finite
from crs import Engine, as_crs, geocentric
from math_util import stage_basis, apply_matrix
from placement import ModelMap, definition, direct, controlling, check_roles


class Reader:
    def __init__(self, stage):
        self.stage = stage
        self.engine = Engine()

    def output(self, requested):
        if requested is not None:
            return as_crs(requested)
        default_prim = self.stage.GetDefaultPrim()
        require(bool(default_prim), "no output context")
        require(
            direct(default_prim)
            or default_prim.GetTypeName() == "CoordinateReferenceSystem",
            "no default output CRS",
        )
        return definition(default_prim, model=False)

    def points(self, prim, points, output=None, time=None):
        """Resolve model-local points into the requested CRS at composed USD time.

        The controlling binding chooses placement. Ordinary baked geometry has
        a typed Cartesian context and follows the ordinary USD world transform.
        """
        time_code = Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)
        output = self.output(output)
        resolved_prim = (
            prim.GetPrim()
            if hasattr(prim, "GetPrim")
            else prim if hasattr(prim, "GetPath") else self.stage.GetPrimAtPath(prim)
        )
        require(bool(resolved_prim), "missing prim")
        check_roles(resolved_prim)
        # An ordinary explicit bake has a typed Cartesian context, not an implicit reset.
        ancestor = resolved_prim
        context = None
        while ancestor and not ancestor.IsPseudoRoot():
            if direct(ancestor):
                break
            if ancestor.GetTypeName() == "CoordinateReferenceSystem":
                context = ancestor
                break
            ancestor = ancestor.GetParent()
        if context:
            context_crs = definition(context, False)
            require(
                not context_crs.is_geographic, "ordinary bake requires Cartesian CRS"
            )
            local_to_world = UsdGeom.XformCache(time_code).GetLocalToWorldTransform(
                resolved_prim
            )
            world = apply_matrix(points, local_to_world) @ stage_basis(self.stage).T
            units = np.array([a.unit_conversion_factor for a in context_crs.axis_info])
            return self.engine.convert(world / units, context_crs, output)
        anchor = controlling(resolved_prim)
        check_roles(anchor)
        require(
            anchor.GetTypeName() != "GeospatialDataSource",
            "model query on measurement carrier",
        )
        # Detect invalid input fields anywhere between the geometry and its anchor.
        ancestor = resolved_prim
        while ancestor != anchor:
            check_roles(ancestor)
            ancestor = ancestor.GetParent()
        descendant_transform, reset = UsdGeom.XformCache(
            time_code
        ).ComputeRelativeTransform(resolved_prim, anchor)
        return ModelMap(anchor, time_code, self.engine).forward(
            points, output, descendant_transform, reset
        )

    def scene_points(self, prim, points, output=None, time=None, origin=(0, 0, 0)):
        """Return Cartesian scene coordinates plus the CRS defining their chart."""
        output = self.output(output)
        chart = geocentric(output) if output.is_geographic else output
        resolved_points = self.points(prim, points, chart, time)
        units = np.array([a.unit_conversion_factor for a in chart.axis_info])
        return (resolved_points - finite(origin)) * units @ np.linalg.inv(
            stage_basis(self.stage)
        ).T, chart

    def derivative(self, prim, point, output=None, time=None):
        # Numerical differentiation is an implementation method, not a source field.
        location = finite(point)
        step = 0.01
        return np.array(
            [
                (
                    self.scene_points(
                        prim, [location + np.eye(3)[axis] * step], output, time
                    )[0][0]
                    - self.scene_points(
                        prim, [location - np.eye(3)[axis] * step], output, time
                    )[0][0]
                )
                / (2 * step)
                for axis in range(3)
            ]
        ).T

    def relative_positions(self, from_prim, to_prim, output=None, time=None):
        output_crs = self.output(output)
        from_position = self.points(from_prim, [(0, 0, 0)], output_crs, time)[0]
        to_position = self.points(to_prim, [(0, 0, 0)], output_crs, time)[0]
        return {
            "from": from_position,
            "to": to_position,
            "difference": from_position - to_position,
            "coordinateCRS": output_crs.to_wkt(),
            "meaning": "coordinate component difference; angular components are not a metric displacement",
        }

    def bounds(self, prim, points, output=None, time=None, continuous=False):
        require(
            not continuous,
            "continuous-domain bound not certified by this implementation; finite probes are insufficient",
        )
        resolved_points, chart = self.scene_points(prim, points, output, time)
        return {
            "min": resolved_points.min(axis=0),
            "max": resolved_points.max(axis=0),
            "chart": chart.to_wkt(),
            "coverage": "supplied finite points and their straight polygonal hull only",
        }

    def vectors(self, prim, points, vectors, role, output=None, time=None):
        """Transport vectors by the local Jacobian; normals by its inverse transpose."""
        locations = finite(points)
        source_vectors = finite(vectors)
        step = 0.01
        jacobian = np.stack(
            [
                (
                    self.scene_points(
                        prim, locations + np.eye(3)[axis] * step, output, time
                    )[0]
                    - self.scene_points(
                        prim, locations - np.eye(3)[axis] * step, output, time
                    )[0]
                )
                / (2 * step)
                for axis in range(3)
            ],
            axis=2,
        )
        if role == "normal":
            require(
                np.all(np.abs(np.linalg.det(jacobian)) > 1e-15),
                "singular normal transport",
            )
            transported = np.linalg.solve(
                jacobian.transpose(0, 2, 1), source_vectors[..., None]
            )[..., 0]
            transported /= np.linalg.norm(transported, axis=1)[:, None]
        elif role == "vector":
            transported = np.einsum("nij,nj->ni", jacobian, source_vectors)
        else:
            raise Failure("unrecognized semantic vector role")
        return finite(transported)

    def instance_points(
        self, instancer, index, prototype_prim, points, output=None, time=None
    ):
        """Resolve one occurrence, preserving independently placed prototypes."""
        time_code = Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)
        output_crs = self.output(output)
        point_instancer = UsdGeom.PointInstancer(instancer)
        instance_ids = point_instancer.GetIdsAttr().Get(time_code)
        mask = point_instancer.ComputeMaskAtTime(time_code)
        require(not mask or mask[index], "masked point instance")
        prototype_binding = None
        targets = point_instancer.GetPrototypesRel().GetTargets()
        prototype_index = point_instancer.GetProtoIndicesAttr().Get(time_code)[index]
        prototype_root = self.stage.GetPrimAtPath(targets[prototype_index])
        ancestor = prototype_prim
        while ancestor and ancestor.GetPath().HasPrefix(prototype_root.GetPath()):
            if direct(ancestor):
                prototype_binding = ancestor
                break
            if ancestor == prototype_root:
                break
            ancestor = ancestor.GetParent()
        matrices = point_instancer.ComputeInstanceTransformsAtTime(
            time_code,
            time_code,
            UsdGeom.PointInstancer.ExcludeProtoXform,
            UsdGeom.PointInstancer.IgnoreMask,
        )
        instance_transform = np.asarray(matrices[index])
        anchor = controlling(instancer)
        instancer_placement = ModelMap(anchor, time_code, self.engine)
        instancer_relative, reset = UsdGeom.XformCache(
            time_code
        ).ComputeRelativeTransform(instancer, anchor)
        if prototype_binding:
            # Occurrence context walks inside prototype, then instancer ancestry.
            parent = prototype_binding.GetParent()
            while (
                parent
                and parent.GetPath().HasPrefix(prototype_root.GetPath())
                and not direct(parent)
            ):
                parent = parent.GetParent()
            working_crs = (
                definition(parent)
                if parent
                and parent.GetPath().HasPrefix(prototype_root.GetPath())
                and direct(parent)
                else definition(anchor)
            )
            prototype_placement = ModelMap(
                prototype_binding, time_code, self.engine, working_crs
            )
            descendant_transform, prototype_reset = UsdGeom.XformCache(
                time_code
            ).ComputeRelativeTransform(prototype_prim, prototype_binding)
            comparison_crs = geocentric(instancer_placement.source)
            placed = prototype_placement.forward(
                points, comparison_crs, descendant_transform, prototype_reset
            )
            if np.array_equal(instance_transform, np.eye(4)):
                return self.engine.convert(placed, comparison_crs, output_crs)
            instancer_local = instancer_placement.inverse(
                placed, comparison_crs, instancer_relative, reset
            )
            return instancer_placement.forward(
                apply_matrix(instancer_local, instance_transform),
                output_crs,
                instancer_relative,
                reset,
            )
        descendant_transform, _ = UsdGeom.XformCache(
            time_code
        ).ComputeRelativeTransform(prototype_prim, prototype_root)
        prototype_transform = UsdGeom.Xformable(prototype_root).GetLocalTransformation(
            time_code
        )
        return instancer_placement.forward(
            apply_matrix(
                points,
                np.asarray(descendant_transform)
                @ np.asarray(prototype_transform)
                @ instance_transform,
            ),
            output_crs,
            instancer_relative,
            reset,
        )
