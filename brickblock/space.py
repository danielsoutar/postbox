# TODO: Get isort working so we can sort these imports
from dataclasses import dataclass
from typing import Any

import itertools
import math
import matplotlib.pyplot as plt

# This import registers the 3D projection, but is otherwise unused.
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from brickblock.index import SpaceIndex, TemporalIndex
from brickblock.objects import Cube, Cuboid, CompositeCube


# TODO: Decide if we want to use classes for this, what details need adding to
# make these transforms useful, etc.
# TODO: Add docstrings
class SpaceStateChange:
    ...


@dataclass
class Addition(SpaceStateChange):
    timestep_id: int
    name: str | None


@dataclass
class Mutation(SpaceStateChange):
    subject: dict[str, Any]
    name: str | None = None
    coordinate: np.ndarray | None = None
    timestep_id: int | None = None
    scene_id: int | None = None


@dataclass
class Transform(SpaceStateChange):
    transform: np.ndarray
    transform_name: str
    name: str | None = None
    coordinate: np.ndarray | None = None
    timestep_id: int | None = None
    scene_id: int | None = None

    def __eq__(self, __value: object) -> bool:
        vals_except_coordinate_match = (
            np.array_equal(self.transform, __value.transform)
            and self.transform_name == __value.transform_name
            and self.name == __value.name
            and self.timestep_id == __value.timestep_id
            and self.scene_id == __value.scene_id
        )
        coordinates_match = (
            np.array_equal(self.coordinate, __value.coordinate)
            if self.coordinate is not None
            else __value.coordinate is None
        )
        return vals_except_coordinate_match and coordinates_match


@dataclass
class Deletion(SpaceStateChange):
    timestep_id: int
    name: str | None


class VisualisationBackend:
    def __init__(self, space_transform: np.ndarray) -> None:
        self.figure_not_initialised = True
        # We represent the transform from input points to matplotlib points
        # (assumed in XZY order).
        # TODO: Check this is the correct terminology.
        self.basis = space_transform

    def _initialise_figure_and_ax(self) -> None:
        # Have a function for initialising the figure separately from __init__,
        # as this avoids empty figures appearing in tests unless render() is
        # explicitly called.
        self.fig = plt.figure(figsize=(10, 7))
        self.fig.subplots_adjust(
            left=0, bottom=0, right=1, top=1, wspace=0.0, hspace=0.0
        )
        self.ax = self.fig.add_subplot(111, projection="3d")
        # Remove everything except the objects to display.
        self.ax.set_axis_off()
        self.figure_not_initialised = False

    def _convert_basis(self, coordinate: np.ndarray) -> np.ndarray:
        return np.dot(coordinate, self.basis)

    def _materialise_vertices_for_primitive(
        self, base: np.ndarray, shape: np.ndarray
    ) -> np.ndarray:
        w = shape[0] * np.array([1, 0, 0])
        h = shape[1] * np.array([0, 0, 1])
        d = shape[2] * np.array([0, 1, 0])
        # Shorthand convention is to have the 'bottom-left-front' point as
        # the base, with points defining width/height/depth of the cube
        # after (using the left-hand rule).
        # Note: the ordering of points matters.
        points = np.array(
            [
                # bottom-left-front
                base,
                # bottom-left-back
                base + d,
                # bottom-right-back
                base + w + d,
                # bottom-right-front
                base + w,
                # top-left-front
                base + h,
                # top-left-back
                base + h + d,
                # top-right-back
                base + h + w + d,
                # top-right-front
                base + h + w,
            ]
        )

        return np.array(
            [
                (points[0], points[1], points[2], points[3]),  # bottom
                (points[0], points[4], points[7], points[3]),  # front face
                (points[0], points[1], points[5], points[4]),  # left face
                (points[3], points[7], points[6], points[2]),  # right face
                (points[1], points[5], points[6], points[2]),  # back face
                (points[4], points[5], points[6], points[7]),  # top
            ]
        ).reshape((6, 4, 3))

    def _materialise_vertices_for_composite(
        self, base: np.ndarray, shape: np.ndarray
    ) -> np.ndarray:
        cube_w = np.array([1, 0, 0])
        cube_h = np.array([0, 0, 1])
        cube_d = np.array([0, 1, 0])
        width_basis_vector = cube_w
        height_basis_vector = cube_h
        depth_basis_vector = cube_d
        # Shorthand convention is to have the 'bottom-left-front' point as
        # the base, with points defining width/height/depth of the cube
        # after (using the left-hand rule).
        # Note: the ordering of points matters.
        all_cube_points = np.array(
            [
                # bottom-left-front
                base,
                # bottom-left-back
                base + cube_d,
                # bottom-right-back
                base + cube_w + cube_d,
                # bottom-right-front
                base + cube_w,
                # top-left-front
                base + cube_h,
                # top-left-back
                base + cube_h + cube_d,
                # top-right-back
                base + cube_h + cube_w + cube_d,
                # top-right-front
                base + cube_h + cube_w,
            ]
        )

        composite_ranges = list(map(range, map(int, shape)))
        all_cubes_all_points = np.array(
            [
                all_cube_points
                + (w * width_basis_vector)
                + (h * height_basis_vector)
                + (d * depth_basis_vector)
                for (w, h, d) in itertools.product(*composite_ranges)
            ]
        )

        num_cubes = int(math.prod(shape))
        ps = all_cubes_all_points.reshape((num_cubes, 8, 3))

        all_cube_faces = np.array(
            [
                [
                    (ps[i][0], ps[i][1], ps[i][2], ps[i][3]),  # bottom
                    (ps[i][0], ps[i][4], ps[i][7], ps[i][3]),  # front face
                    (ps[i][0], ps[i][1], ps[i][5], ps[i][4]),  # left face
                    (ps[i][3], ps[i][7], ps[i][6], ps[i][2]),  # right face
                    (ps[i][1], ps[i][5], ps[i][6], ps[i][2]),  # back face
                    (ps[i][4], ps[i][5], ps[i][6], ps[i][7]),  # top
                ]
                for i in range(num_cubes)
            ]
        )

        return all_cube_faces.reshape((num_cubes, 6, 4, 3))

    def populate_with_primitive(
        self,
        primitive_id: int,
        base_coordinate: np.ndarray,
        shape: np.ndarray,
        visual_properties: dict[str, Any],
    ) -> None:
        """
        Add the primitive with `primitive_id` with `base_coordinate`, `shape`,
        and `visual_properties` to the output of this backend.

        All input data is assumed to be in space-compatible format, and will be
        transformed to the native format of this backend (e.g. coordinates will
        be mapped to XZY - WHD order).

        # Args
            primitive_id: The ID of the primitive to add.
            base_coordinate: The base coordinate of the primitive.
            shape: The shape to apply, in WHD order.
            visual_properties: Object containing the properties to apply, and
                their values.
        """
        # Currently unused.
        _ = primitive_id

        if self.figure_not_initialised:
            self._initialise_figure_and_ax()

        materialised_vertices = self._materialise_vertices_for_primitive(
            self._convert_basis(base_coordinate), shape
        )

        matplotlib_like_cube = Poly3DCollection(
            materialised_vertices, **visual_properties
        )
        self.ax.add_collection3d(matplotlib_like_cube)

    def populate_with_composite(
        self,
        composite_id: slice,
        base_coordinate: np.ndarray,
        shape: np.ndarray,
        visual_properties: dict[str, Any],
    ) -> None:
        """
        Add the composite with `composite_id` with `base_coordinate`, `shape`,
        and `visual_properties` to the output of this backend.

        All input data is assumed to be in space-compatible format, and will be
        transformed to the native format of this backend (e.g. coordinates will
        be mapped to XZY - WHD order).

        # Args
            composite_id: The IDs of all the primitives to add.
            base_coordinate: The base coordinate of the composite.
            shape: The shape to apply, in WHD order.
            visual_properties: Object containing the properties to apply, and
                their values. Note that the values may be lists, in which case
                each entry corresponds to its respective primitive, or scalars,
                in which case it applies to all primitives.
        """
        # Currently not used.
        _ = shape

        if self.figure_not_initialised:
            self._initialise_figure_and_ax()

        materialised_vertices = self._materialise_vertices_for_composite(
            self._convert_basis(base_coordinate), shape
        )

        for primitive_id in range(composite_id.start, composite_id.stop):
            id_offset = primitive_id - composite_id.start
            primitive_visual_properties = {
                k: visual_properties[k][id_offset]
                for k in visual_properties.keys()
            }
            matplotlib_like_cube = Poly3DCollection(
                materialised_vertices[id_offset], **primitive_visual_properties
            )
            self.ax.add_collection3d(matplotlib_like_cube)

    def mutate_primitive(
        self, primitive_id: int, visual_properties: dict[str, Any]
    ) -> None:
        """
        Mutate the visual properties of the primitive with `primitive_id` in the
        output of this backend, with `visual_properties`.

        # Args
            primitive_id: The ID of the primitive to mutate.
            visual_properties: Object containing the properties to update, and
                their values.
        """
        if self.figure_not_initialised:
            self._initialise_figure_and_ax()

        self.ax.collections[primitive_id].set(**visual_properties)

    def mutate_composite(
        self,
        composite_id: slice,
        visual_properties: dict[str, Any],
    ) -> None:
        """
        Mutate the visual properties of the composite with `composite_id` in the
        output of this backend, with `visual_properties`.

        # Args
            composite_id: The ID of the composite to mutate.
            visual_properties: Object containing the properties to update, and
                their values.
        """
        if self.figure_not_initialised:
            self._initialise_figure_and_ax()

        for primitive_id in range(composite_id.start, composite_id.stop):
            primitive_visual_properties = {
                k: visual_properties[k][primitive_id]
                for k in visual_properties.keys()
            }
            self.ax.collections[primitive_id].set(**primitive_visual_properties)

    def transform_primitive(
        self,
        primitive_id: int,
        transform_name: str,
        vertices: np.ndarray,
        shape: np.ndarray,
    ) -> None:
        """
        Transform the primitive with `primitive_id` in the output of this
        backend according to `transform_name`, with `vertices` and `shape`.

        # Args
            primitive_id: The ID of the primitive to transform.
            transform_name: The type of transform to apply.
            vertices: The (potentially) updated vertices to apply.
            shape: The (potentially) updated shape to apply, in WHD order.
        """
        if self.figure_not_initialised:
            self._initialise_figure_and_ax()

        if transform_name == "translation":
            _ = shape
            self.ax.collections[primitive_id].set_verts(vertices)
        if transform_name == "reflection":
            _ = shape
            self.ax.collections[primitive_id].set_verts(vertices)
        if transform_name == "scale":
            _ = shape
            self.ax.collections[primitive_id].set_verts(vertices)

    def transform_composite(
        self,
        composite_id: slice,
        transform_name: str,
        vertices: np.ndarray,
        shape: np.ndarray,
    ) -> None:
        """
        Transform the composite with `composite_id` in the output of this
        backend according to `transform_name`, with `vertices` and `shape`.

        # Args
            composite_id: The ID of the composite to transform.
            transform_name: The type of transform to apply.
            vertices: The (potentially) updated vertices to apply.
            shape: The (potentially) updated shape to apply, in WHD order.
        """
        if self.figure_not_initialised:
            self._initialise_figure_and_ax()

        for primitive_id in range(composite_id.start, composite_id.stop):
            id_offset = primitive_id - composite_id.start
            if transform_name == "translation":
                _ = shape
                self.ax.collections[primitive_id].set_verts(vertices[id_offset])
            if transform_name == "reflection":
                _ = shape
                self.ax.collections[primitive_id].set_verts(vertices[id_offset])
            if transform_name == "scale":
                raise ValueError(
                    "Scaling for composites is not supported in this backend."
                )


class Space:
    """
    Representation of a 3D coordinate space, which tracks its state over time.

    Any added objects are stored in a variety of formats, such as by coordinate
    data, by name, and various IDs. This facilitates multiple ways of querying
    them within a space.

    The space is the object that abstracts over a visualisation backend, like
    matplotlib.

    # Attributes
        dims: The dimensions of the space. This is stored for potential use with
            the camera when rendering a scene.
        mean: The mean point of the space. This is stored for potential use with
            the camera when rendering a scene.
        total: The total value per dimension of all objects. This is stored for
            potential use with the camera when rendering a scene.
        num_objs: The total number of objects in the space. Distinct primitives
            and composites each count as one object.
        primitive_counter: The total number of primitives in the space. A
            composite object can comprise of multiple primitives.
        time_step: The number of individual transforms done to the space.
        scene_counter: The number of scenes to render.
        cuboid_coordinates: The dense coordinate info for each primitive in the
            space. This has shape Nx6x4x3, where N is the number of primitives.
            Objects are stored in order of insertion.
        cuboid_visual_metadata: The visual properties for each primitive in the
            space. Objects are stored in order of insertion.
        cuboid_index: A hierarchial index of the objects inserted into the
            space.
        cuboid_names: A mapping between names and objects/primitives.
        changelog: A high-level description of each transform done to the space.
    """

    # TODO: Clarify dimensions for things being WHD or XYZ (or a mix).
    dims: np.ndarray
    mean: np.ndarray
    total: np.ndarray
    num_objs: int
    primitive_counter: int
    time_step: int
    tracked_time_step: int
    scene_counter: int
    # TODO: Should these be classes?
    cuboid_coordinates: np.ndarray
    cuboid_shapes: np.ndarray
    cuboid_visual_metadata: dict[str, list]
    cuboid_index: TemporalIndex
    cuboid_names: dict[str, tuple[list[int], list[slice]]]
    # TODO: Document the changelog structure (mutations are stored as primitives
    # then composites per updated field).
    changelog: list[SpaceStateChange]
    dimensions: dict[str, int]
    basis: np.ndarray
    visualisation_backend: VisualisationBackend

    def __init__(self) -> None:
        self.dims = np.zeros((3, 2))
        self.mean = np.zeros((3, 1))
        self.total = np.zeros((3, 1))
        self.num_objs = 0
        self.primitive_counter = 0
        self.object_counter = 0
        self.tracked_time_step = 0
        self.time_step = 0
        self.scene_counter = 0
        self.cuboid_coordinates = np.zeros((10, 6, 4, 3))
        self.base_coordinates = np.zeros((10, 3))
        self.old_cuboid_shapes = np.zeros((10, 3))
        self.cuboid_shapes = np.zeros((10, 3))
        self.old_cuboid_visual_metadata = {}
        self.cuboid_visual_metadata = {}
        self.old_cuboid_index = SpaceIndex()
        self.cuboid_index = TemporalIndex()
        self.composite_index = TemporalIndex()
        self.old_cuboid_names = {}
        self.cuboid_names = {}
        self.changelog = []
        # The default mapping is W -> x-axis, H -> z-axis, D -> y-axis.
        # TODO: Decouple from this fixed basis - should swap height/depth.
        self.dimensions = {"width": 0, "height": 2, "depth": 1}
        # We represent the transform from user-provided points (assumed in XYZ
        # order) to matplotlib points (assumed in XZY order).
        # TODO: Check this is the correct terminology.
        self.basis = np.zeros((3, 3))
        self.basis[self.dimensions["width"], 0] = 1
        self.basis[self.dimensions["height"], 1] = 1
        self.basis[self.dimensions["depth"], 2] = 1
        self.visualisation_backend = VisualisationBackend(self.basis)

    def _convert_basis(self, coordinate: np.ndarray) -> np.ndarray:
        return np.dot(coordinate, self.basis)

    def add_cube(self, cube: Cube) -> None:
        """
        Add a Cube primitive to the space.
        """
        old_primitive_id, primitive_id = self._add_cuboid_primitive(cube)
        self._old_add_name(cube.name, [[old_primitive_id], None])
        self._add_name(cube.name, [[primitive_id], None])
        self.num_objs += 1
        self.changelog.append(Addition(self.time_step, None))
        self.time_step += 1
        self._update_bounds(slice(old_primitive_id, old_primitive_id + 1))

    def add_cuboid(self, cuboid: Cuboid) -> None:
        """
        Add a Cuboid primitive to the space.
        """
        old_primitive_id, primitive_id = self._add_cuboid_primitive(cuboid)
        self._old_add_name(cuboid.name, [[old_primitive_id], None])
        self._add_name(cuboid.name, [[primitive_id], None])
        self.num_objs += 1
        self.changelog.append(Addition(self.time_step, None))
        self.time_step += 1
        self._update_bounds(slice(old_primitive_id, old_primitive_id + 1))

    def add_composite(self, composite: CompositeCube) -> None:
        """
        Add a CompositeCube object to the space.
        """
        old_composite_id, composite_id = self._add_cuboid_composite(composite)
        self._old_add_name(composite.name, [None, [old_composite_id]])
        self._add_name(composite.name, [None, [composite_id]])
        self.num_objs += 1
        self.changelog.append(Addition(self.time_step, None))
        self.time_step += 1
        self._update_bounds(old_composite_id)

    def _add_cuboid_primitive(self, cuboid: Cube | Cuboid) -> int:
        """
        Add a primitive to the space by updating the various indices and data
        structures, and return its ID.

        # Args
            cuboid: Primitive Cube/Cuboid to add to the space's various data
            structures.
        """
        cuboid_bounding_box = cuboid.bounding_box()
        cuboid_mean = np.mean(cuboid.points(), axis=0).reshape((3, 1))

        # Update the bounding box - via total, mean, and dims.
        self.total += cuboid_mean

        self.mean = self.total / (self.num_objs + 1)

        if self.primitive_counter == 0:
            dim = cuboid_bounding_box
        else:
            # Since there are multiple objects, ensure the resulting dimensions
            # of the surrounding box are the extrema of the objects within.
            dim = np.array(
                [
                    [
                        min(self.dims[i][0], cuboid_bounding_box[i][0]),
                        max(self.dims[i][1], cuboid_bounding_box[i][1]),
                    ]
                    for i in range(len(cuboid_bounding_box))
                ]
            ).reshape((3, 2))

        self.dims = dim

        # Update the coordinate data, resizing if necessary.
        current_no_of_entries = self.cuboid_coordinates.shape[0]
        if self.primitive_counter >= current_no_of_entries:
            # refcheck set to False since this avoids issues with the debugger
            # referencing the array!
            self.cuboid_coordinates.resize(
                (2 * current_no_of_entries, *self.cuboid_coordinates.shape[1:]),
                refcheck=False,
            )
        current_no_of_entries = self.base_coordinates.shape[0]
        if self.object_counter >= current_no_of_entries:
            # refcheck set to False since this avoids issues with the debugger
            # referencing the array!
            self.base_coordinates.resize(
                (2 * current_no_of_entries, self.base_coordinates.shape[1]),
                refcheck=False,
            )
            # Repeat this for the shape array as well.
            self.cuboid_shapes.resize(
                (2 * current_no_of_entries, self.cuboid_shapes.shape[1]),
                refcheck=False,
            )

        # Add shape data for this cuboid.
        self.old_cuboid_shapes[self.primitive_counter] = cuboid.shape()
        self.cuboid_shapes[self.object_counter] = cuboid.shape()

        self.cuboid_coordinates[self.primitive_counter] = cuboid.faces
        self.base_coordinates[self.object_counter] = cuboid.faces[0][0]

        # Update the visual metadata store.
        for key, value in cuboid.visual_metadata().items():
            if key in self.old_cuboid_visual_metadata.keys():
                self.old_cuboid_visual_metadata[key].append(value)
                self.cuboid_visual_metadata[key].append(value)
            else:
                self.old_cuboid_visual_metadata[key] = [value]
                self.cuboid_visual_metadata[key] = [value]

        self.old_cuboid_index.add_primitive_to_index(
            self.primitive_counter, self.time_step, self.scene_counter
        )
        self.cuboid_index.add_item_to_index(
            self.object_counter, self.time_step, self.scene_counter
        )

        # Update the primitive_counter.
        old_primitive_id = self.primitive_counter
        primitive_id = self.object_counter
        self.primitive_counter += 1
        self.object_counter += 1

        return old_primitive_id, primitive_id

    def _add_cuboid_composite(self, composite: CompositeCube) -> int:
        num_cubes = composite.faces.shape[0]

        # Update bounding box
        flattened_faces = composite.faces.reshape((-1, 3))
        self.total += np.mean(flattened_faces, axis=0).reshape((3, 1))

        # We only add one to the denominator because we added a single object.
        self.mean = self.total / (self.num_objs + 1)

        composite_points = np.array(
            [composite.faces[0][0], composite.faces[-1][-1]]
        ).reshape((8, 3))

        mins = [np.min(composite_points[:, i]) for i in range(3)]
        maxes = [np.max(composite_points[:, i]) for i in range(3)]

        composite_extrema = np.empty((3, 2))
        for i, (min_dim, max_dim) in enumerate(zip(mins, maxes)):
            composite_extrema[i] = min_dim, max_dim

        if self.primitive_counter == 0:
            dim = composite_extrema
        else:
            # Since there are multiple objects, ensure the resulting dimensions
            # of the surrounding box are the extrema of the objects within.
            dim = np.array(
                [
                    [
                        min(self.dims[i][0], composite_extrema[i][0]),
                        max(self.dims[i][1], composite_extrema[i][1]),
                    ]
                    for i in range(len(composite_extrema))
                ]
            ).reshape((3, 2))

        self.dims = dim

        # Update coordinate array
        current_no_of_entries = self.cuboid_coordinates.shape[0]
        if (self.primitive_counter + num_cubes) >= current_no_of_entries:
            # Ensure that at most one allocation is needed to encompass this
            # composite.
            while (2 * current_no_of_entries) < num_cubes:
                current_no_of_entries *= 2

            # refcheck set to False since this avoids issues with the debugger
            # referencing the array!
            self.cuboid_coordinates.resize(
                (2 * current_no_of_entries, *self.cuboid_coordinates.shape[1:]),
                refcheck=False,
            )
            # Repeat this for the shape array as well.
            self.old_cuboid_shapes.resize(
                (2 * current_no_of_entries, self.old_cuboid_shapes.shape[1]),
                refcheck=False,
            )
        current_no_of_entries = self.base_coordinates.shape[0]
        if self.object_counter >= current_no_of_entries:
            # refcheck set to False since this avoids issues with the debugger
            # referencing the array!
            self.base_coordinates.resize(
                (2 * current_no_of_entries, self.base_coordinates.shape[1]),
                refcheck=False,
            )
            # Repeat this for the shape array as well.
            self.cuboid_shapes.resize(
                (2 * current_no_of_entries, self.cuboid_shapes.shape[1]),
                refcheck=False,
            )

        base = self.primitive_counter
        offset = base + num_cubes
        # Add shape data for this composite.
        self.old_cuboid_shapes[base:offset] = composite.shape()
        self.cuboid_shapes[self.object_counter] = composite.shape()

        self.cuboid_coordinates[base:offset] = composite.faces
        base_coordinate = composite.faces[0][0][0]
        self.base_coordinates[self.object_counter] = base_coordinate

        # Update visual metadata store
        for key, value in composite.visual_metadata().items():
            if key in self.old_cuboid_visual_metadata.keys():
                self.old_cuboid_visual_metadata[key].extend([value] * num_cubes)
                self.cuboid_visual_metadata[key].append(value)
            else:
                self.old_cuboid_visual_metadata[key] = [value] * num_cubes
                self.cuboid_visual_metadata[key] = [value]

        primitive_ids = slice(base, offset)

        # Add to index
        self.old_cuboid_index.add_composite_to_index(
            primitive_ids, self.time_step, self.scene_counter
        )
        self.composite_index.add_item_to_index(
            self.object_counter, self.time_step, self.scene_counter
        )

        # TODO: Consider how to implement 'styles'.
        if composite.style == "classic":
            raise NotImplementedError("Currently, styles are not supported.")
            ...

        composite_id = self.object_counter
        self.primitive_counter += num_cubes
        self.object_counter += 1

        return primitive_ids, composite_id

    def _add_name(
        self,
        name: str | None,
        object_ids: tuple[list[int] | None, list[int] | None],
    ) -> None:
        """
        Add an entry for `name` for the given `object_ids`, if specified.

        It is an error to add an entry for a name that already exists.

        # Args
            name: An optional name that references each ID in `object_ids`.
            object_ids: The primitive/composite ID(s) to name. Can contain both
                primitives and composites. There must be at least one valid ID.
        """
        if name is not None:
            if name in self.cuboid_names.keys():
                raise Exception(
                    f"There already exists an object with name {name}."
                )
            if object_ids[0] is None and object_ids[1] is None:
                raise Exception(
                    "The entity to name has no IDs associated with it."
                )
            self.cuboid_names[name] = object_ids

    def _old_add_name(
        self,
        name: str | None,
        object_ids: tuple[list[int] | None, list[slice] | None],
    ) -> None:
        """
        Add an entry for `name` for the given `object_ids`, if specified.

        It is an error to add an entry for a name that already exists.

        # Args
            name: An optional name that references each ID in `object_ids`.
            object_ids: The primitive/composite ID(s) to name. Can contain both
                primitives and composites, each composite is assumed to be
                non-empty. There must be at least one valid ID.
        """
        if name is not None:
            if name in self.old_cuboid_names.keys():
                raise Exception(
                    f"There already exists an object with name {name}."
                )
            if object_ids[0] is None and object_ids[1] is None:
                raise Exception(
                    "The entity to name has no IDs associated with it."
                )
            self.old_cuboid_names[name] = object_ids

    def _update_bounds(self, primitive_ids: slice) -> None:
        """
        Update the bounding box of the space, based on the primitives given by
        `primitive_ids`.

        Whether one or more primitives are given, the space will update its
        bounds over the extrema in both cases.

        The bounds of the space are updated regardless of whether or not the
        provided primitives are visible.

        # Args
            primitive_ids: The primitives for which coordinate data is used to
                update the bounding box of this space.
        """
        N = primitive_ids.stop - primitive_ids.start
        primitives = self.cuboid_coordinates[primitive_ids].reshape(
            (N * 6 * 4, 3)
        )
        given_mins = np.min(primitives, axis=0)
        given_maxes = np.max(primitives, axis=0)

        self.dims[:, 0] = np.minimum(self.dims[:, 0], given_mins.T)
        self.dims[:, 1] = np.maximum(self.dims[:, 1], given_maxes.T)

    # TODO: Decide how deletion should be implemented. Masking columns seem the
    # most logical, but this could be an issue for memory consumption. On the
    # other hand, 'actual deletion' would involve potentially expensive memory
    # shuffling and storing of the data in the changelog, which largely
    # nullifies the memory savings anyway.
    # Moreover, should you even be worrying about deletion? Masking is what you
    # really want in virtually all cases. Deletion should actually be quite rare
    # unless a user does something dumb or adds crazy numbers of objects.

    # TODO: Should `mutate_all`/`create_all_by_offset` be supported?

    def mutate_by_coordinate(self, coordinate: np.ndarray, **kwargs) -> None:
        """
        Mutate the visual metadata of all objects - composite or primitive, with
        base vectors equal to `coordinate` - with the named arguments in
        `kwargs`.

        Both an empty selection (i.e. no objects match with the coordinate) or
        empty kwargs (i.e. no visual updates to perform) are treated as no-ops.

        Primitives that are part of composites are not included - that is, if
        `coordinate` intersects with a composite on any point other than its
        base vector, none of its primitives will be updated.

        Note that the base vector is defined as the bottom-left-front-most point
        of an object, primitive or composite.

        # Args
            coordinate: The coordinate which is compared to the base vector of
                all objects in the space.
            kwargs: Sequence of named arguments that contain updated visual
                property values.
        """
        primitives_to_update, composites_to_update = self._select_by_coordinate(
            coordinate
        )
        non_zero_selection = (
            len(primitives_to_update) > 0 or len(composites_to_update) > 0
        )

        non_empty_kwargs = len(kwargs) > 0

        if not (non_zero_selection and non_empty_kwargs):
            return None

        previous_state = self._mutate_by_ids(
            primitives_to_update, composites_to_update, **kwargs
        )
        self.changelog.append(
            Mutation(subject=previous_state, coordinate=coordinate)
        )

    def mutate_by_name(self, name: str, **kwargs) -> None:
        """
        Mutate the visual metadata of the object - composite or primitive, that
        has its name equal to `name` - with the named arguments in `kwargs`.

        Both an empty selection (i.e. no objects match with the name) or empty
        kwargs (i.e. no visual updates to perform) are treated as no-ops.

        # Args
            name: The name of the object in the space to update.
            kwargs: Sequence of named arguments that contain updated visual
                property values.
        """
        primitives_to_update, composites_to_update = self._select_by_name(name)
        non_zero_selection = (
            len(primitives_to_update) > 0 or len(composites_to_update) > 0
        )

        non_empty_kwargs = len(kwargs) > 0

        if not (non_zero_selection and non_empty_kwargs):
            return None

        previous_state = self._mutate_by_ids(
            primitives_to_update, composites_to_update, **kwargs
        )
        self.changelog.append(Mutation(subject=previous_state, name=name))

    def mutate_by_timestep(self, timestep: int, **kwargs) -> None:
        """
        Mutate the visual metadata of the object - composite or primitive, that
        was referenced at timestep `timestep` - with the named arguments in
        `kwargs`.

        Both an empty selection (i.e. no objects match with the timestep) or
        empty kwargs (i.e. no visual updates to perform) are treated as no-ops.

        # Args
            timestep: The timestep of all the objects in the space to update.
            kwargs: Sequence of named arguments that contain updated visual
                property values.
        """
        primitives_to_update, composites_to_update = self._select_by_timestep(
            timestep
        )
        non_zero_selection = (
            len(primitives_to_update) > 0 or len(composites_to_update) > 0
        )

        non_empty_kwargs = len(kwargs) > 0

        if not (non_zero_selection and non_empty_kwargs):
            return None

        previous_state = self._mutate_by_ids(
            primitives_to_update, composites_to_update, **kwargs
        )
        self.changelog.append(
            Mutation(subject=previous_state, timestep_id=timestep)
        )

    def mutate_by_scene(self, scene: int, **kwargs) -> None:
        """
        Mutate the visual metadata of the object - composite or primitive, that
        was referenced in scene `scene` - with the named arguments in `kwargs`.

        Both an empty selection (i.e. no objects match with the scene) or
        empty kwargs (i.e. no visual updates to perform) are treated as no-ops.

        # Args
            scene: The scene of all the objects in the space to update.
            kwargs: Sequence of named arguments that contain updated visual
                property values.
        """
        primitives_to_update, composites_to_update = self._select_by_scene(
            scene
        )
        non_zero_selection = (
            len(primitives_to_update) > 0 or len(composites_to_update) > 0
        )

        non_empty_kwargs = len(kwargs) > 0

        if not (non_zero_selection and non_empty_kwargs):
            return None

        previous_state = self._mutate_by_ids(
            primitives_to_update, composites_to_update, **kwargs
        )
        self.changelog.append(Mutation(subject=previous_state, scene_id=scene))

    def _old_mutate_by_ids(
        self, primitive_ids: list[int], composite_ids: list[slice], **kwargs
    ) -> dict[str, Any]:
        """
        Mutate the visual metadata of all primitives and composites (given by
        `primitive_ids` and `composite_ids` respectively) with the named
        arguments in `kwargs`, and return the previous version of the metadata.

        There is assumed to be at least one primitive or composite to update,
        and `kwargs` is assumed to be non-empty.

        # Args
            primitive_ids: The IDs of all the primitives in the space to update.
            composite_ids: The IDs of all the composites in the space to update.
            kwargs: Sequence of named arguments that contain updated visual
                property values.
        """
        before_mutation_kwargs = {}
        for key in kwargs.keys():
            if key not in self.old_cuboid_visual_metadata.keys():
                raise KeyError(
                    "The provided key doesn't match any valid visual property."
                )
            before_mutation_kwargs[key] = []
            for primitive_id in primitive_ids:
                old_val = self.old_cuboid_visual_metadata[key][primitive_id]
                before_mutation_kwargs[key].append(old_val)
                self.old_cuboid_visual_metadata[key][primitive_id] = kwargs[key]
            for composite_id in composite_ids:
                N = composite_id.stop - composite_id.start
                old_val = self.old_cuboid_visual_metadata[key][
                    composite_id.start
                ]
                before_mutation_kwargs[key].append(old_val)
                broadcast_val = [kwargs[key]] * N
                self.old_cuboid_visual_metadata[key][
                    composite_id
                ] = broadcast_val

        for primitive_id in primitive_ids:
            self.old_cuboid_index.add_primitive_to_index(
                primitive_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )
        for composite_id in composite_ids:
            self.old_cuboid_index.add_composite_to_index(
                composite_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )

        self.time_step += 1
        return before_mutation_kwargs

    def _mutate_by_ids(
        self, primitive_ids: list[int], composite_ids: list[int], **kwargs
    ) -> dict[str, Any]:
        """
        Mutate the visual metadata of all primitives and composites (given by
        `primitive_ids` and `composite_ids` respectively) with the named
        arguments in `kwargs`, and return the previous version of the metadata.

        There is assumed to be at least one primitive or composite to update,
        and `kwargs` is assumed to be non-empty.

        # Args
            primitive_ids: The IDs of all the primitives in the space to update.
            composite_ids: The IDs of all the composites in the space to update.
            kwargs: Sequence of named arguments that contain updated visual
                property values.
        """
        before_mutation_kwargs = {}
        for key in kwargs.keys():
            if key not in self.cuboid_visual_metadata.keys():
                raise KeyError(
                    "The provided key doesn't match any valid visual property."
                )
            before_mutation_kwargs[key] = []
            for primitive_id in primitive_ids:
                old_val = self.cuboid_visual_metadata[key][primitive_id]
                before_mutation_kwargs[key].append(old_val)
                self.cuboid_visual_metadata[key][primitive_id] = kwargs[key]
            for composite_id in composite_ids:
                old_val = self.cuboid_visual_metadata[key][composite_id]
                before_mutation_kwargs[key].append(old_val)
                self.cuboid_visual_metadata[key][composite_id] = kwargs[key]

        for primitive_id in primitive_ids:
            self.cuboid_index.add_item_to_index(
                primitive_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )
        for composite_id in composite_ids:
            self.composite_index.add_item_to_index(
                composite_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )

        self.time_step += 1
        return before_mutation_kwargs

    def transform_by_coordinate(
        self,
        coordinate: np.ndarray,
        translate: np.ndarray | None = None,
        reflect: np.ndarray | None = None,
        scale: np.ndarray | None = None,
    ) -> None:
        """
        Transform the spatial data of all objects - composite or primitive, with
        base vectors equal to `coordinate` - by one of the transform vectors.

        Note that, since affine transformations are in general not commutative,
        only one transform can be set.

        Both an empty selection (i.e. no objects match with the coordinate) or a
        zero transform vector are treated as no-ops.

        Primitives that are part of composites are not included - that is, if
        `coordinate` intersects with a composite on any point other than its
        base vector, none of its primitives will be updated.

        Note that the base vector is defined as the bottom-left-front-most point
        of an object, primitive or composite.

        # Args
            coordinate: The coordinate which is compared to the base vector of
                all objects in the space.
            translate: The vector by which to shift selected objects by.
            reflect: The vector by which to reflect selected objects by, with
                respect to the axes of the space. A vector that does not contain
                exclusively 1s and -1s is a no-op, as well as vectors of all 1s.
            scale: The vector by which to scale selected objects by, with
                respect to the origin (distances from the origin will also be
                scaled). Only positive scaling is supported, and only primitives
                can be scaled. All other cases are no-ops.
        """
        primitive_ids, composite_ids = self._select_by_coordinate(coordinate)
        transform_kwargs = self._transform_by_ids(
            primitive_ids, composite_ids, translate, reflect, scale
        )
        if transform_kwargs is not None:
            self.changelog.append(
                Transform(coordinate=coordinate, **transform_kwargs)
            )
            self.time_step += 1

    def transform_by_name(
        self,
        name: str,
        translate: np.ndarray | None = None,
        reflect: np.ndarray | None = None,
        scale: np.ndarray | None = None,
    ) -> None:
        """
        Transform the spatial data of all objects - composite or primitive, that
        that has its name equal to `name` - by one of the transform vectors.

        Note that, since affine transformations are in general not commutative,
        only one transform can be set.

        Both an empty selection (i.e. no objects match with the coordinate) or a
        zero transform vector are treated as no-ops.

        # Args
            name: The name of the object in the space to update.
            translate: The vector by which to shift selected objects by.
            reflect: The vector by which to reflect selected objects by, with
                respect to the axes of the space. A vector that does not contain
                exclusively 1s and -1s is a no-op, as well as vectors of all 1s.
            scale: The vector by which to scale selected objects by, with
                respect to the origin (distances from the origin will also be
                scaled). Only positive scaling is supported, and only primitives
                can be scaled. All other cases are no-ops.
        """
        primitive_ids, composite_ids = self._select_by_name(name)
        transform_kwargs = self._transform_by_ids(
            primitive_ids, composite_ids, translate, reflect, scale
        )
        if transform_kwargs is not None:
            self.changelog.append(Transform(name=name, **transform_kwargs))
            self.time_step += 1

    def transform_by_timestep(
        self,
        timestep: int,
        translate: np.ndarray | None = None,
        reflect: np.ndarray | None = None,
        scale: np.ndarray | None = None,
    ) -> None:
        """
        Transform the spatial data of all objects - composite or primitive, that
        was referenced at timestep `timestep` - by one of the transform vectors.

        Note that, since affine transformations are in general not commutative,
        only one transform can be set.

        Both an empty selection (i.e. no objects match with the coordinate) or a
        zero transform vector are treated as no-ops.

        # Args
            timestep: The timestep of all the objects in the space to update.
            translate: The vector by which to shift selected objects by.
            reflect: The vector by which to reflect selected objects by, with
                respect to the axes of the space. A vector that does not contain
                exclusively 1s and -1s is a no-op, as well as vectors of all 1s.
            scale: The vector by which to scale selected objects by, with
                respect to the origin (distances from the origin will also be
                scaled). Only positive scaling is supported, and only primitives
                can be scaled. All other cases are no-ops.
        """
        primitive_ids, composite_ids = self._select_by_timestep(timestep)
        transform_kwargs = self._transform_by_ids(
            primitive_ids, composite_ids, translate, reflect, scale
        )
        if transform_kwargs is not None:
            self.changelog.append(
                Transform(timestep_id=timestep, **transform_kwargs)
            )
            self.time_step += 1

    def transform_by_scene(
        self,
        scene: int,
        translate: np.ndarray | None = None,
        reflect: np.ndarray | None = None,
        scale: np.ndarray | None = None,
    ) -> None:
        """
        Transform the spatial data of all objects - composite or primitive, that
        was referenced at scene `scene` - by one of the transform vectors.

        Objects that are referenced multiple times (i.e. over several timesteps)
        will only be transformed once.

        Note that, since affine transformations are in general not commutative,
        only one transform can be set.

        Both an empty selection (i.e. no objects match with the coordinate) or a
        zero transform vector are treated as no-ops.

        # Args
            scene: The scene of all the objects in the space to update.
            translate: The vector by which to shift selected objects by. A zero
                vector is a no-op.
            reflect: The vector by which to reflect selected objects by, with
                respect to the axes of the space. A vector that does not contain
                exclusively 1s and -1s is a no-op, as well as vectors of all 1s.
            scale: The vector by which to scale selected objects by, with
                respect to the origin (distances from the origin will also be
                scaled). Only positive scaling is supported, and only primitives
                can be scaled. All other cases are no-ops.
        """
        primitive_ids, composite_ids = self._select_by_scene(scene)

        transform_kwargs = self._transform_by_ids(
            primitive_ids, composite_ids, translate, reflect, scale
        )
        if transform_kwargs is not None:
            self.changelog.append(Transform(scene_id=scene, **transform_kwargs))
            self.time_step += 1

    def _old_transform_by_ids(
        self,
        primitive_ids: list[int],
        composite_ids: list[slice],
        translate: np.ndarray | None = None,
        reflect: np.ndarray | None = None,
        scale: np.ndarray | None = None,
    ) -> dict[str, Any] | None:
        non_zero_selection = len(primitive_ids) > 0 or len(composite_ids) > 0

        exactly_one_set = (
            sum([a is not None for a in [translate, reflect, scale]]) == 1
        )
        if not exactly_one_set:
            raise ValueError(
                "Exactly one transform argument can be set when transforming "
                "objects."
            )

        if translate is not None:
            val = translate
            coord_func = lambda obj: obj + translate  # noqa: E731
            shape_func = None
            kwargs = {"transform": -translate, "transform_name": "translation"}
        if reflect is not None:
            # This muddled logic stems from allowing an arbitrary vector.
            # Instead it would be better if only valid inputs could be passed.
            unique_elements = np.unique(reflect)
            allowed_elements = np.array([-1, 1])
            if not set(unique_elements).issubset(set(allowed_elements)):
                raise ValueError("Reflection may only contain 1s and -1s.")
            degenerate_reflection = np.array([1])
            val = reflect
            if np.array_equal(unique_elements, degenerate_reflection):
                val = np.zeros(reflect.shape)
            coord_func = lambda obj: obj * reflect  # noqa: E731
            shape_func = lambda shp: shp * reflect  # noqa: E731
            kwargs = {"transform": reflect, "transform_name": "reflection"}
        if scale is not None:
            # TODO: Change/remove coordinate buffer to allow scaling composites.
            if len(composite_ids) > 0:
                raise ValueError("Scale may only be applied to primitives.")
            if any([v <= 0 for v in scale]):
                raise ValueError("Scale may only contain positive values.")
            val = scale
            coord_func = lambda obj: obj * scale  # noqa: E731
            shape_func = lambda shp: shp * scale  # noqa: E731
            kwargs = {"transform": 1 / scale, "transform_name": "scale"}

        non_zero_transform = np.any(val)

        if not (non_zero_selection and non_zero_transform):
            return None

        if coord_func is not None:
            self.cuboid_coordinates[primitive_ids] = coord_func(
                self.cuboid_coordinates[primitive_ids]
            )
            for composite_id in composite_ids:
                composite = self.cuboid_coordinates[composite_id]
                self.cuboid_coordinates[composite_id] = coord_func(composite)
        if shape_func is not None:
            self.old_cuboid_shapes[primitive_ids] = shape_func(
                self.old_cuboid_shapes[primitive_ids]
            )
            for composite_id in composite_ids:
                shapes = self.old_cuboid_shapes[composite_id]
                self.old_cuboid_shapes[composite_id] = shape_func(shapes)

        for primitive_id in primitive_ids:
            self.old_cuboid_index.add_primitive_to_index(
                primitive_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )
        for composite_id in composite_ids:
            self.old_cuboid_index.add_composite_to_index(
                composite_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )

        return kwargs

    def _transform_by_ids(
        self,
        primitive_ids: list[int],
        composite_ids: list[int],
        translate: np.ndarray | None = None,
        reflect: np.ndarray | None = None,
        scale: np.ndarray | None = None,
    ) -> dict[str, Any] | None:
        non_zero_selection = len(primitive_ids) > 0 or len(composite_ids) > 0

        exactly_one_set = (
            sum([a is not None for a in [translate, reflect, scale]]) == 1
        )
        if not exactly_one_set:
            raise ValueError(
                "Exactly one transform argument can be set when transforming "
                "objects."
            )

        if translate is not None:
            val = translate
            coord_func = lambda obj: obj + translate  # noqa: E731
            shape_func = None
            kwargs = {"transform": -translate, "transform_name": "translation"}
        if reflect is not None:
            # This muddled logic stems from allowing an arbitrary vector.
            # Instead it would be better if only valid inputs could be passed.
            unique_elements = np.unique(reflect)
            allowed_elements = np.array([-1, 1])
            if not set(unique_elements).issubset(set(allowed_elements)):
                raise ValueError("Reflection may only contain 1s and -1s.")
            degenerate_reflection = np.array([1])
            val = reflect
            if np.array_equal(unique_elements, degenerate_reflection):
                val = np.zeros(reflect.shape)
            coord_func = lambda obj: obj * reflect  # noqa: E731
            shape_func = lambda shp: shp * reflect  # noqa: E731
            kwargs = {"transform": reflect, "transform_name": "reflection"}
        if scale is not None:
            # TODO: Change/remove coordinate buffer to allow scaling composites.
            if len(composite_ids) > 0:
                raise ValueError("Scale may only be applied to primitives.")
            if any([v <= 0 for v in scale]):
                raise ValueError("Scale may only contain positive values.")
            val = scale
            coord_func = lambda obj: obj * scale  # noqa: E731
            shape_func = lambda shp: shp * scale  # noqa: E731
            kwargs = {"transform": 1 / scale, "transform_name": "scale"}

        non_zero_transform = np.any(val)

        if not (non_zero_selection and non_zero_transform):
            return None

        if coord_func is not None:
            joined_ids = primitive_ids + composite_ids
            self.base_coordinates[joined_ids] = coord_func(
                self.base_coordinates[joined_ids]
            )
        if shape_func is not None:
            joined_ids = primitive_ids + composite_ids
            self.cuboid_shapes[joined_ids] = shape_func(
                self.cuboid_shapes[joined_ids]
            )

        for primitive_id in primitive_ids:
            self.cuboid_index.add_item_to_index(
                primitive_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )
        for composite_id in composite_ids:
            self.composite_index.add_item_to_index(
                composite_id,
                timestep_id=self.time_step,
                scene_id=self.scene_counter,
            )

        return kwargs

    # TODO: Consider whether to support `create_by_offset`, which implies
    # creating an object with certain attributes, but its position is dictated
    # by other objects. How would this work?

    def clone_by_offset(
        self,
        offset: np.ndarray,
        coordinate: np.ndarray | None = None,
        name: str | None = None,
        timestep: int | None = None,
        scene: int | None = None,
        **kwargs,
    ) -> None:
        """
        Create a duplicate of an object (or objects) selected by any one of
        `coordinate`, `name`, `timestep`, or `scene`, shifted by `offset`.

        The offset is done with respect to the base vectors of the objects.

        Exactly one of `coordinate`, `name`, `timestep`, or `scene` must be set.
        The selection can refer to multiple objects - in this case, a duplicate
        is made for each object in the selection. An empty selection is a no-op.

        Note that all objects created will be treated as having been created at
        the same timestep.

        The remaining args are used to override the inherited visual properties
        of the created objects. These will apply to all created objects - if a
        single value is given, then this is broadcast to all objects. Otherwise
        a list with the same number of created objects is given and will be
        applied in order of insertion.

        # Args
            offset: Offset by base vector, in XYZ coordinate form.
            coordinate: Optional selection, where all objects with equal base
                vectors will be selected.
            name: Optional selection, where the object with that name will be
                selected.
            timestep: Optional selection, where all objects created in that
                timestep will be selected.
            scene: Optional selection, where all objects created in that scene
                will be selected.
            kwargs: Optional visual property arguments - can be a dict with
                scalar or list of values.
        """
        exactly_one_set = (
            sum([a is not None for a in [coordinate, name, timestep, scene]])
            == 1
        )
        if not exactly_one_set:
            raise ValueError(
                "Exactly one selection argument can be set when creating "
                "objects."
            )

        if coordinate is not None:
            val, func = coordinate, self._old_select_by_coordinate
        if name is not None:
            val, func = name, self._old_select_by_name
        if timestep is not None:
            val, func = timestep, self._old_select_by_timestep
        if scene is not None:
            val, func = scene, self._old_select_by_scene

        primitive_ids, composite_ids = func(val)

        if len(primitive_ids) == 0 and len(composite_ids) == 0:
            return None

        # Interleave the kwargs with the IDs to support the iterable case.
        total_number_of_ids = len(primitive_ids) + len(composite_ids)
        interleaved_kwargs = []
        for i in range(total_number_of_ids):
            kwargs_for_id = {}
            for key in kwargs.keys():
                if key not in self.old_cuboid_visual_metadata.keys():
                    raise KeyError(
                        "The provided key doesn't match any valid visual "
                        "property."
                    )
                if isinstance(kwargs[key], list):
                    kwargs_for_id[key] = kwargs[key][i]
                else:
                    kwargs_for_id[key] = kwargs[key]
            interleaved_kwargs.append(kwargs_for_id)

        new_primitive_ids = []
        for primitive, vis_met_data in zip(primitive_ids, interleaved_kwargs):
            visual_metadata = {
                key: self.old_cuboid_visual_metadata[key][primitive]
                for key in self.old_cuboid_visual_metadata.keys()
            }
            # Take the visual metadata, with the user-provided ones taking
            # precedence.
            visual_metadata = visual_metadata | vis_met_data
            # We use a Cuboid for handling both Cubes and Cuboids.
            # Swap the axes around here - otherwise you will get double-swapping
            # of the dimensions.
            transformed_base = self._convert_basis(
                self.cuboid_coordinates[primitive][0][0]
            )
            cuboid = Cuboid(
                transformed_base + offset,
                *self.old_cuboid_shapes[primitive],
                **visual_metadata,
                name=None,
            )
            new_old_primitive_id, new_primitive_id = self._add_cuboid_primitive(
                cuboid
            )
            new_primitive_ids.append(new_old_primitive_id)
            self.num_objs += 1

        new_composite_ids = []
        for composite, vis_met_data in zip(composite_ids, interleaved_kwargs):
            start = composite.start
            visual_metadata = {
                key: self.old_cuboid_visual_metadata[key][start]
                for key in self.old_cuboid_visual_metadata.keys()
            }
            # Take the visual metadata, with the user-provided ones taking
            # precedence.
            visual_metadata = visual_metadata | vis_met_data
            # Swap the axes around here - otherwise you will get double-swapping
            # of the dimensions.
            transformed_base = self._convert_basis(
                self.cuboid_coordinates[start][0][0]
            )
            shape = tuple(int(val) for val in self.old_cuboid_shapes[start])
            new_old_composite_id, new_composite_id = self._add_cuboid_composite(
                CompositeCube(
                    transformed_base + offset,
                    *shape,
                    **visual_metadata,
                    name=None,
                )
            )
            new_composite_ids.append(new_old_composite_id)
            self.num_objs += 1

        if len(new_primitive_ids) > 0:
            min_id = new_primitive_ids[0]
        else:
            min_id = new_composite_ids[0].start

        if len(new_composite_ids) == 0:
            max_id = new_primitive_ids[-1]
        else:
            max_id = new_composite_ids[-1].stop - 1

        self.changelog.append(Addition(self.time_step, None))
        self.time_step += 1
        self._update_bounds(slice(min_id, max_id + 1))

    def _old_select_by_coordinate(
        self, coordinate: np.ndarray
    ) -> tuple[list[int], list[slice]]:
        if coordinate.shape != (3,):
            raise ValueError(
                "Coordinates are three-dimensional, the input vector should be "
                "3D."
            )

        # Map the coordinate to the correct representation.
        # TODO: Decouple the user from a fixed basis.
        coordinate = self._convert_basis(coordinate)

        # First gather the IDs of primitive entries that match the coordinate.
        matching_base_vectors = []
        primitives_to_update, composites_to_update = [], []

        for idx in range(self.primitive_counter):
            primitive = self.cuboid_coordinates[idx]
            if np.array_equal(primitive[0, 0], coordinate):
                matching_base_vectors.append(idx)

        # You can assume all indices are either landing on the first primitive
        # of a composite (a match) or a distinct primitive, since otherwise
        # you don't consider it a match anyway. That means you can just compare
        # against the first value of the slices in the composite buffer.

        primitive_id = next(self.old_cuboid_index.primitives(), None)
        composite_slice = next(self.old_cuboid_index.composites(), None)

        # For each index, check if it's a primitive or composite. If it is,
        # add it to the relevant output buffer/increment the relevant iterator.
        # If the relevant iterator is exhausted, use a default of None.
        for idx in matching_base_vectors:
            if primitive_id is not None and primitive_id == idx:
                primitives_to_update.append(primitive_id)
                primitive_id = next(self.old_cuboid_index.primitives(), None)
            if composite_slice is not None and composite_slice.start == idx:
                composites_to_update.append(composite_slice)
                composite_slice = next(self.old_cuboid_index.composites(), None)

        return primitives_to_update, composites_to_update

    def _select_by_coordinate(
        self, coordinate: np.ndarray
    ) -> tuple[list[int], list[int]]:
        if coordinate.shape != (3,):
            raise ValueError(
                "Coordinates are three-dimensional, the input vector should be "
                "3D."
            )

        # Map the coordinate to the correct representation.
        # TODO: Decouple the user from a fixed basis.
        coordinate = self._convert_basis(coordinate)

        # First gather the IDs of primitive entries that match the coordinate.
        matching_base_vectors = []
        primitives_to_update, composites_to_update = [], []

        for idx in range(self.object_counter):
            base_coordinate = self.base_coordinates[idx]
            if np.array_equal(base_coordinate, coordinate):
                matching_base_vectors.append(idx)

        primitive_id = next(self.cuboid_index.items(), None)
        composite_id = next(self.composite_index.items(), None)

        # For each index, check if it's a primitive or composite. If it is,
        # add it to the relevant output buffer/increment the relevant iterator.
        # If the relevant iterator is exhausted, use a default of None.
        for idx in matching_base_vectors:
            if primitive_id is not None and primitive_id == idx:
                primitives_to_update.append(primitive_id)
                primitive_id = next(self.cuboid_index.items(), None)
            if composite_id is not None and composite_id == idx:
                composites_to_update.append(composite_id)
                composite_id = next(self.composite_index.items(), None)

        return primitives_to_update, composites_to_update

    def _old_select_by_name(self, name: str) -> tuple[list[int], list[slice]]:
        if name not in self.old_cuboid_names.keys():
            raise ValueError("The provided name does not exist in this space.")

        primitive_ids, composite_ids = self.old_cuboid_names[name]

        primitive_ids = primitive_ids if primitive_ids is not None else []
        composite_ids = composite_ids if composite_ids is not None else []

        return primitive_ids, composite_ids

    def _select_by_name(self, name: str) -> tuple[list[int], list[int]]:
        if name not in self.cuboid_names.keys():
            raise ValueError("The provided name does not exist in this space.")

        primitive_ids, composite_ids = self.cuboid_names[name]

        primitive_ids = primitive_ids if primitive_ids is not None else []
        composite_ids = composite_ids if composite_ids is not None else []

        return primitive_ids, composite_ids

    def _old_select_by_timestep(
        self, timestep: int
    ) -> tuple[list[int], list[slice]]:
        if (timestep < 0) or (timestep > self.time_step):
            raise ValueError("The provided timestep is invalid in this space.")

        primitive_ids = self.old_cuboid_index.get_primitives_by_timestep(
            timestep
        )
        composite_ids = self.old_cuboid_index.get_composites_by_timestep(
            timestep
        )

        # TODO: Update outputs to ensure they only contain distinct values.
        # TODO: Check whether this is an issue for timesteps.

        return primitive_ids, composite_ids

    def _select_by_timestep(self, timestep: int) -> tuple[list[int], list[int]]:
        if (timestep < 0) or (timestep > self.time_step):
            raise ValueError("The provided timestep is invalid in this space.")

        primitive_ids = self.cuboid_index.get_items_by_timestep(timestep)
        composite_ids = self.composite_index.get_items_by_timestep(timestep)

        # TODO: Update outputs to ensure they only contain distinct values.
        # TODO: Check whether this is an issue for timesteps.

        return primitive_ids, composite_ids

    def _old_select_by_scene(self, scene: int) -> tuple[list[int], list[slice]]:
        if (scene < 0) or (scene > self.scene_counter):
            raise ValueError("The provided scene ID is invalid in this space.")

        primitive_ids = self.old_cuboid_index.get_primitives_by_scene(scene)
        composite_ids = self.old_cuboid_index.get_composites_by_scene(scene)

        # TODO: Update outputs to ensure they only contain distinct values.
        primitive_ids = sorted(list(set(primitive_ids)))
        # This is nasty, and is due to slices not being hashable. Having
        # composite_ids as tuples or ints is worth considering.
        composite_ids = sorted(
            list(
                slice(t[0], t[1])
                for t in set(
                    [(c_id.start, c_id.stop) for c_id in composite_ids]
                )
            )
        )

        return primitive_ids, composite_ids

    def _select_by_scene(self, scene: int) -> tuple[list[int], list[int]]:
        if (scene < 0) or (scene > self.scene_counter):
            raise ValueError("The provided scene ID is invalid in this space.")

        primitive_ids = self.cuboid_index.get_items_by_scene(scene)
        composite_ids = self.composite_index.get_items_by_scene(scene)

        # TODO: This could ideally be more efficient.
        primitive_ids = sorted(list(set(primitive_ids)))
        composite_ids = sorted(list(set(composite_ids)))

        return primitive_ids, composite_ids

    def snapshot(self) -> None:
        """
        Store the current state of the space as a scene, used for rendering.

        Note that valid scenes must have 1+ transforms - i.e. adding,
        deleting, or mutating an object, must be present in a scene.
        """
        scene = self.scene_counter + 1
        referenced_cuboids = self.cuboid_index.current_scene_is_valid(scene)
        referenced_composites = self.composite_index.current_scene_is_valid(
            scene
        )
        if not (referenced_cuboids or referenced_composites):
            raise Exception(
                "A snapshot must include at least one addition, mutation, or "
                "deletion in the given scene."
            )
        self.scene_counter += 1

    # TODO: Decide whether passing the Axes or having it be fully constructed by
    # brickblock is a good idea - memory management could be a problem.
    # TODO: It seems controlling the azimuth and elevation parameters (which are
    # handily configurable!) is what you need for adjusting the camera.
    # TODO: plt.show shows each figure generated by render(), rather than only
    # the last one (though it shows the last one first). Can this be fixed?
    # (Yes - you are being an idiot).
    def render(self) -> tuple[plt.Figure, plt.Axes]:
        """
        Render every scene in the space with a matplotlib Axes, and return the
        figure-axes pair.
        """
        # TODO: This logic really belongs in a `stream()` function. The render
        # method should just get all primitive_ids and then render everything
        # from the coordinates and visual_metadata.

        # We start from where the time step was last tracked.
        time_slice = slice(self.tracked_time_step, len(self.changelog))
        time_range = range(self.tracked_time_step, len(self.changelog))
        for timestep, operation in zip(time_range, self.changelog[time_slice]):
            primitives = self.old_cuboid_index.get_primitives_by_timestep(
                timestep
            )
            composites = self.old_cuboid_index.get_composites_by_timestep(
                timestep
            )
            if isinstance(operation, Addition):
                for primitive in primitives:
                    # Change of basis to WHD/XYZ format for the base point.
                    base_coordinate = self._convert_basis(
                        self.cuboid_coordinates[primitive][0][0]
                    )
                    shape = self.old_cuboid_shapes[primitive]
                    visual_properties = {
                        k: self.old_cuboid_visual_metadata[k][primitive]
                        for k in self.old_cuboid_visual_metadata.keys()
                    }
                    self.visualisation_backend.populate_with_primitive(
                        primitive, base_coordinate, shape, visual_properties
                    )
                for composite in composites:
                    base_coordinate = self._convert_basis(
                        self.cuboid_coordinates[composite][0][0][0]
                    )
                    shape = self.old_cuboid_shapes[composite][0]
                    visual_properties = {
                        k: self.old_cuboid_visual_metadata[k][composite]
                        for k in self.old_cuboid_visual_metadata.keys()
                    }
                    self.visualisation_backend.populate_with_composite(
                        composite, base_coordinate, shape, visual_properties
                    )
            elif isinstance(operation, Mutation):
                # Only need to fetch data for properties that were updated.
                for primitive in primitives:
                    metadata = {
                        k: self.old_cuboid_visual_metadata[k][primitive]
                        for k in operation.subject.keys()
                    }
                    self.visualisation_backend.mutate_primitive(
                        primitive, metadata
                    )
                for composite in composites:
                    metadata = {
                        k: self.old_cuboid_visual_metadata[k][composite]
                        for k in operation.subject.keys()
                    }
                    self.visualisation_backend.mutate_composite(
                        composite, metadata
                    )
            elif isinstance(operation, Transform):
                for primitive in primitives:
                    vertices = self.cuboid_coordinates[primitive]
                    shape = self.old_cuboid_shapes[primitive]
                    self.visualisation_backend.transform_primitive(
                        primitive, operation.transform_name, vertices, shape
                    )
                for composite in composites:
                    vertices = self.cuboid_coordinates[composite]
                    shape = self.old_cuboid_shapes[composite]
                    self.visualisation_backend.transform_composite(
                        composite, operation.transform_name, vertices, shape
                    )
            else:
                raise Exception(
                    "Invalid/unsupported operation encountered when rendering."
                )

        # Now move the tracked time step to the current time step.
        self.tracked_time_step = self.time_step

        # Use the space's bounds to update the camera and view.
        # This is very janky but at least ensures everything is in view.
        # One way this could be fixed would be to reorient everything so that
        # aiming at the origin actually works. Essentially you take the
        # difference between the center of the bounding box of the space, and
        # the origin, and shift everything by the negative difference.
        # The problem with this solution is a) it involves a transform over
        # everything and b) would mean the user cannot turn on the axes to debug
        # things as effectively. Potentially this could be explained in some
        # docs though.
        max_val = max(list(self.dims.flatten()))

        fig, ax = self.visualisation_backend.fig, self.visualisation_backend.ax

        ax.set_xlim(-max_val, max_val)
        ax.set_ylim(-max_val, max_val)
        ax.set_zlim(-max_val, max_val)

        return fig, ax
