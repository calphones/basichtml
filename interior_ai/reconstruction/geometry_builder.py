"""Extrude 2D floor plan geometry into a 3D architectural shell."""

from __future__ import annotations
from dataclasses import dataclass, field
import math
import numpy as np

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

from ..types import (
    Vec2, Vec3, WallSegment, Opening, OpeningType,
    StaircaseElement, Room, FloorPlanData
)


@dataclass
class Mesh3D:
    """Lightweight mesh container: vertex positions + face indices."""
    vertices: np.ndarray        # (N, 3) float32
    faces: np.ndarray           # (M, 3) int32
    name: str = ""
    material_name: str = "default"


@dataclass
class ArchitecturalShell:
    """Complete 3D building shell extracted from floor plan."""
    walls: list[Mesh3D] = field(default_factory=list)
    floors: list[Mesh3D] = field(default_factory=list)
    ceilings: list[Mesh3D] = field(default_factory=list)
    stairs: list[Mesh3D] = field(default_factory=list)
    openings: list[Mesh3D] = field(default_factory=list)


class GeometryBuilder:
    """Convert FloorPlanData into a 3D ArchitecturalShell.

    Each wall becomes a box mesh with opening cutouts.
    Floors and ceilings are generated from room polygons.
    Staircases are built step-by-step from detected parameters.
    """

    def __init__(self, default_ceiling_height: float = 2.74):
        self.ceiling_height = default_ceiling_height

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, floor_plan: FloorPlanData) -> ArchitecturalShell:
        shell = ArchitecturalShell()
        opening_index: dict[str, list[Opening]] = {}
        for op in floor_plan.openings:
            opening_index.setdefault(op.wall_id, []).append(op)

        for wall in floor_plan.walls:
            openings = opening_index.get(wall.id, [])
            mesh = self._build_wall(wall, openings)
            shell.walls.append(mesh)

        for room in floor_plan.rooms:
            shell.floors.append(self._build_floor(room))
            shell.ceilings.append(self._build_ceiling(room))

        for stair in floor_plan.stairs:
            shell.stairs.extend(self._build_staircase(stair))

        return shell

    # ------------------------------------------------------------------
    # Wall geometry
    # ------------------------------------------------------------------

    def _build_wall(self, wall: WallSegment, openings: list[Opening]) -> Mesh3D:
        """Build a wall box with rectangular cutouts for doors and windows."""
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        length = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        h = wall.height if wall.height else self.ceiling_height
        t = wall.thickness

        # Build quads for each wall panel section between openings
        verts: list[np.ndarray] = []
        faces: list[tuple] = []

        # Sort openings by position along wall
        sorted_ops = sorted(openings, key=lambda o: o.position_along_wall)
        cursor = 0.0
        v_offset = 0

        def add_solid_panel(x0: float, x1: float, z0: float, z1: float):
            nonlocal v_offset
            if x1 <= x0:
                return
            corners = np.array([
                [x0, 0, z0], [x1, 0, z0],
                [x1, 0, z1], [x0, 0, z1],
                [x0, t, z0], [x1, t, z0],
                [x1, t, z1], [x0, t, z1],
            ])
            verts.append(corners)
            quad_faces = [
                (0, 1, 2), (0, 2, 3),   # front
                (4, 6, 5), (4, 7, 6),   # back
                (0, 4, 5), (0, 5, 1),   # bottom
                (3, 2, 6), (3, 6, 7),   # top
                (0, 3, 7), (0, 7, 4),   # left
                (1, 5, 6), (1, 6, 2),   # right
            ]
            faces.extend([(f[0]+v_offset, f[1]+v_offset, f[2]+v_offset) for f in quad_faces])
            v_offset += 8

        for op in sorted_ops:
            op_start = op.position_along_wall * length
            op_end = op_start + op.width
            sill = op.sill_height
            op_height = op.height

            # Solid section before opening
            add_solid_panel(cursor, op_start, 0, h)

            # Panel below sill (for windows)
            if sill > 0:
                add_solid_panel(op_start, op_end, 0, sill)

            # Panel above opening (lintel)
            add_solid_panel(op_start, op_end, sill + op_height, h)

            cursor = op_end

        # Remaining wall after last opening
        add_solid_panel(cursor, length, 0, h)

        if not verts:
            all_verts = np.zeros((0, 3), dtype=np.float32)
            all_faces = np.zeros((0, 3), dtype=np.int32)
        else:
            all_verts = np.vstack(verts).astype(np.float32)
            all_faces = np.array(faces, dtype=np.int32)

        # Rotate and translate into world space
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        rot = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
        if len(all_verts):
            all_verts = (rot @ all_verts.T).T
            all_verts[:, 0] += wall.start.x
            all_verts[:, 1] += wall.start.y

        return Mesh3D(
            vertices=all_verts,
            faces=all_faces,
            name=f"wall_{wall.id}",
            material_name="wall_paint",
        )

    # ------------------------------------------------------------------
    # Floor / ceiling
    # ------------------------------------------------------------------

    def _build_floor(self, room: Room) -> Mesh3D:
        return self._extrude_polygon(room.polygon, z=0.0, name=f"floor_{room.id}",
                                      material="hardwood_floor")

    def _build_ceiling(self, room: Room) -> Mesh3D:
        h = room.ceiling_height if room.ceiling_height else self.ceiling_height
        return self._extrude_polygon(room.polygon, z=h, name=f"ceiling_{room.id}",
                                      material="ceiling_white", flip=True)

    def _extrude_polygon(
        self, polygon: list[Vec2], z: float,
        name: str, material: str, flip: bool = False
    ) -> Mesh3D:
        if len(polygon) < 3:
            return Mesh3D(np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int32), name)
        verts = np.array([[p.x, p.y, z] for p in polygon], dtype=np.float32)
        n = len(verts)
        # Fan triangulation from centroid
        cx, cy = verts[:, 0].mean(), verts[:, 1].mean()
        center = np.array([[cx, cy, z]], dtype=np.float32)
        all_verts = np.vstack([verts, center])
        ci = n
        faces = []
        for i in range(n):
            j = (i + 1) % n
            if flip:
                faces.append((ci, j, i))
            else:
                faces.append((ci, i, j))
        return Mesh3D(
            vertices=all_verts,
            faces=np.array(faces, dtype=np.int32),
            name=name,
            material_name=material,
        )

    # ------------------------------------------------------------------
    # Staircase geometry
    # ------------------------------------------------------------------

    def _build_staircase(self, stair: StaircaseElement) -> list[Mesh3D]:
        """Build individual stair step boxes."""
        meshes = []
        ox, oy = stair.position.x, stair.position.y
        angle = math.radians(stair.direction_degrees)
        cos_a, sin_a = math.cos(angle), math.sin(angle)

        for i in range(stair.step_count):
            run = stair.run_per_step
            rise = stair.rise_per_step
            w = stair.width
            z0 = i * rise
            z1 = (i + 1) * rise
            x0 = i * run
            x1 = (i + 1) * run

            corners = np.array([
                [x0, 0, z0], [x1, 0, z0], [x1, w, z0], [x0, w, z0],
                [x0, 0, z1], [x1, 0, z1], [x1, w, z1], [x0, w, z1],
            ], dtype=np.float32)
            faces = np.array([
                [0, 1, 2], [0, 2, 3],
                [4, 6, 5], [4, 7, 6],
                [0, 4, 5], [0, 5, 1],
                [3, 2, 6], [3, 6, 7],
                [0, 3, 7], [0, 7, 4],
                [1, 5, 6], [1, 6, 2],
            ], dtype=np.int32)

            # Rotate and translate
            rot = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
            corners = (rot @ corners.T).T
            corners[:, 0] += ox
            corners[:, 1] += oy

            meshes.append(Mesh3D(
                vertices=corners,
                faces=faces,
                name=f"stair_step_{i:03d}",
                material_name="stair_wood",
            ))
        return meshes
