from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class Cube:
    """
    Primitive object for composing scenes.

    This object is intended for purely as a 'front-end' for users to interact
    with for composing `Scene`s.
    """

    faces: np.ndarray
    facecolor: tuple[float, float, float] | None = None
    linewidth: float = 0.1
    edgecolor: str = "black"
    alpha: float = 0.0

    def __init__(
        self,
        base_vector: np.ndarray,
        scale: float = 1.0,
        facecolor: tuple[float, float, float] | None = None,
        linewidth: float = 0.1,
        edgecolor: str = "black",
        alpha: float = 0.0,
    ) -> None:
        # Check base_vector is 3D.
        is_3d = base_vector.flatten().shape == (3,)
        if not is_3d:
            raise ValueError(
                "Cube objects are three-dimensional, the base vector should be "
                "3D."
            )

        height_basis_vector = np.array([0, 1, 0])
        width_basis_vector = np.array([1, 0, 0])
        depth_basis_vector = np.array([0, 0, 1])

        points = np.array(
            [
                base_vector,
                scale * height_basis_vector,
                scale * width_basis_vector,
                scale * depth_basis_vector,
            ]
        ).reshape((4, 3))

        full_points = self._construct_points(points)

        self.faces = self._construct_faces(full_points)
        self.facecolor = facecolor
        self.linewidth = linewidth
        self.edgecolor = edgecolor
        self.alpha = alpha

    def points(self) -> np.ndarray:
        return np.array([self.faces[0], self.faces[-1]]).reshape((8, 3))

    def get_visual_metadata(self) -> dict[str, Any]:
        return {
            "facecolor": self.facecolor,
            "linewidth": self.linewidth,
            "edgecolor": self.edgecolor,
            "alpha": self.alpha,
        }

    def get_bounding_box(self) -> np.ndarray:
        """
        Get the bounding box around the cube's `points`.

        The output is a 3x2 matrix, with rows in WHD order (xs, ys, zs)
        corresponding to the minimum and maximum per dimension respectively.
        """
        points = np.array([self.faces[0], self.faces[-1]]).reshape((8, 3))
        x_min = np.min(points[:, 0])
        x_max = np.max(points[:, 0])
        y_min = np.min(points[:, 1])
        y_max = np.max(points[:, 1])
        z_min = np.min(points[:, 2])
        z_max = np.max(points[:, 2])

        max_range = (
            np.array([x_max - x_min, y_max - y_min, z_max - z_min]).max() / 2.0
        )

        mid_x = (x_max + x_min) * 0.5
        mid_y = (y_max + y_min) * 0.5
        mid_z = (z_max + z_min) * 0.5

        return np.array(
            [
                [mid_x - max_range, mid_x + max_range],
                [mid_y - max_range, mid_y + max_range],
                [mid_z - max_range, mid_z + max_range],
            ]
        ).reshape((3, 2))

    def _construct_points(self, points: np.ndarray) -> np.ndarray:
        """
        Construct the full set of points from a partial set of points.
        """
        # Shorthand convention is to have the 'bottom-left-front' point as
        # the base, with points defining height/width/depth of the cube
        # after (using the left-hand rule).
        # NB: in the 'xyz' axes, we have width-height-depth (WHD) for the
        # coordinates.
        base, h, w, d = points
        # Note: the ordering of points matters.
        full_points = np.array(
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
                # top-left-back
                base + h + w + d,
                # top-right-front
                base + h + w,
            ]
        )

        return full_points.reshape((8, 3))

    def _construct_faces(self, points: np.ndarray) -> np.ndarray:
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


class CompositeCube:
    faces: np.ndarray
    facecolor: tuple[float, float, float] | None = None
    linewidth: float = 0.1
    edgecolor: str = "black"
    alpha: float = 0.0

    def __init__(
        self,
        base_vector: np.ndarray,
        h: float,
        w: float,
        d: float,
        facecolor: tuple[float, float, float] | None = None,
        linewidth: float = 0.1,
        edgecolor: str = "black",
        alpha: float = 0.0,
    ) -> None:
        # Check base_vector is 3D.
        is_3d = base_vector.flatten().shape == (3,)
        if not is_3d:
            raise ValueError(
                "Cube objects are three-dimensional, the base vector should be "
                "3D."
            )

        height_basis_vector = np.array([0, 1, 0])
        width_basis_vector = np.array([1, 0, 0])
        depth_basis_vector = np.array([0, 0, 1])

        # For now we assume that composites are built out of unit cubes.
        # This could be generalised to arbitrary cubes but for now this will do.
        points = np.array(
            [
                base_vector,
                height_basis_vector,
                width_basis_vector,
                depth_basis_vector,
            ]
        ).reshape((4, 3))

        full_points = self._construct_points(points, h, w, d)

        self.faces = self._construct_faces(full_points)
        self.facecolor = facecolor
        self.linewidth = linewidth
        self.edgecolor = edgecolor
        self.alpha = alpha

    def points(self) -> np.ndarray:
        # TODO: Figure out the relevant points that define the bounds of the
        # entire object.
        return np.array([])

    def get_visual_metadata(self) -> dict[str, Any]:
        return {
            "facecolor": self.facecolor,
            "linewidth": self.linewidth,
            "edgecolor": self.edgecolor,
            "alpha": self.alpha,
        }

    def _construct_points(
        self,
        cube_points: np.ndarray,
        composite_h: float,
        composite_w: float,
        composite_d: float,
    ) -> np.ndarray:
        """
        Construct the full set of points from a partial set of points.
        """
        # Shorthand convention is to have the 'bottom-left-front' point as
        # the base, with points defining height/width/depth of the cube
        # after (using the left-hand rule).
        # NB: in the 'xyz' axes, we have width-height-depth (WHD) for the
        # coordinates.
        base, cube_h, cube_w, cube_d = cube_points
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
                # top-left-back
                base + cube_h + cube_w + cube_d,
                # top-right-front
                base + cube_h + cube_w,
            ]
        )

        all_cube_points = all_cube_points.reshape((8, 3))

        all_cubes_all_points = np.array([])

        return all_cubes_all_points.reshape(
            (composite_h, composite_w, composite_d, 8, 3)
        )

    def _construct_faces(self, points: np.ndarray) -> np.ndarray:
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
