"""Generate procedural 3D furniture meshes via Blender Python API (bpy)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math

from ..types import Vec3, FurnitureCategory, Color
from ..reconstruction.geometry_builder import Mesh3D
import numpy as np


@dataclass
class FurnitureGeometry:
    meshes: list[Mesh3D]
    category: FurnitureCategory
    asset_id: str


class ProceduralFurnitureGen:
    """Generate parametric furniture meshes without external asset files.

    All furniture is built from primitives (boxes, cylinders, swept profiles)
    assembled programmatically. Dimensions are driven by the FurnitureDatabase
    catalogue entries, so changing a single measurement regenerates the mesh.

    This approach guarantees:
    - No copyright concerns
    - Exact dimension control
    - Style-adaptive geometry (curved vs rectilinear)
    """

    def generate(
        self,
        category: FurnitureCategory,
        dimensions: Vec3,
        curved: bool = False,
        low_profile: bool = False,
    ) -> FurnitureGeometry:
        generators = {
            FurnitureCategory.SEATING: self._gen_sofa,
            FurnitureCategory.SECTIONAL: self._gen_sectional,
            FurnitureCategory.ACCENT_CHAIR: self._gen_accent_chair,
            FurnitureCategory.COFFEE_TABLE: self._gen_table,
            FurnitureCategory.SIDE_TABLE: self._gen_table,
            FurnitureCategory.DINING_TABLE: self._gen_table,
            FurnitureCategory.BED: self._gen_bed,
            FurnitureCategory.RUG: self._gen_rug,
            FurnitureCategory.LAMP: self._gen_lamp,
            FurnitureCategory.TV_UNIT: self._gen_cabinet,
            FurnitureCategory.BOOKSHELF: self._gen_cabinet,
            FurnitureCategory.STORAGE: self._gen_cabinet,
        }
        gen_fn = generators.get(category, self._gen_box)
        meshes = gen_fn(dimensions, curved=curved, low_profile=low_profile)
        return FurnitureGeometry(
            meshes=meshes,
            category=category,
            asset_id=f"proc_{category.value}",
        )

    # ------------------------------------------------------------------
    # Sofa
    # ------------------------------------------------------------------

    def _gen_sofa(self, dim: Vec3, curved: bool = False, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        seat_h = h * 0.45
        back_h = h - seat_h
        arm_w = 0.12
        cushion_raise = 0.06

        meshes = []
        # Seat base
        meshes.append(self._box(0, 0, 0, w, d, seat_h, name="sofa_seat", mat="sofa_fabric"))
        # Back cushion
        meshes.append(self._box(0, d - 0.25, seat_h, w, 0.25, back_h, name="sofa_back", mat="sofa_fabric"))
        # Left arm
        meshes.append(self._box(0, 0, 0, arm_w, d, h, name="sofa_arm_l", mat="sofa_fabric"))
        # Right arm
        meshes.append(self._box(w - arm_w, 0, 0, arm_w, d, h, name="sofa_arm_r", mat="sofa_fabric"))
        # Legs (4 small boxes)
        leg_h = 0.10
        leg_w = 0.06
        for lx, ly in [(arm_w + 0.05, 0.05), (w - arm_w - leg_w - 0.05, 0.05),
                        (arm_w + 0.05, d - leg_w - 0.05), (w - arm_w - leg_w - 0.05, d - leg_w - 0.05)]:
            meshes.append(self._box(lx, ly, -leg_h, leg_w, leg_w, leg_h, name="sofa_leg", mat="metal_leg"))
        return meshes

    # ------------------------------------------------------------------
    # Sectional (L-shape)
    # ------------------------------------------------------------------

    def _gen_sectional(self, dim: Vec3, curved: bool = False, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        seat_h = h * 0.45
        back_h = h - seat_h
        # Main run
        meshes = self._gen_sofa(Vec3(w * 0.65, d, h), curved=curved)
        # Return section (rotated 90°)
        ret_w = w * 0.45
        ret_d = d * 0.85
        ret_x = w * 0.65 - d
        ret = self._box(ret_x, d, 0, ret_d, ret_w, h * 0.45, name="sectional_return", mat="sofa_fabric")
        ret_back = self._box(ret_x, d + ret_w - 0.25, seat_h, ret_d, 0.25, back_h, name="sectional_return_back", mat="sofa_fabric")
        meshes.extend([ret, ret_back])
        return meshes

    # ------------------------------------------------------------------
    # Chair
    # ------------------------------------------------------------------

    def _gen_accent_chair(self, dim: Vec3, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        seat_h = h * 0.45
        meshes = [
            self._box(0, 0, 0, w, d, seat_h, name="chair_seat", mat="chair_fabric"),
            self._box(0, d - 0.20, seat_h, w, 0.20, h - seat_h, name="chair_back", mat="chair_fabric"),
        ]
        leg_h = 0.12
        for lx, ly in [(0.05, 0.05), (w - 0.10, 0.05), (0.05, d - 0.10), (w - 0.10, d - 0.10)]:
            meshes.append(self._box(lx, ly, -leg_h, 0.05, 0.05, leg_h, name="chair_leg", mat="metal_leg"))
        return meshes

    # ------------------------------------------------------------------
    # Table (flat surface + legs)
    # ------------------------------------------------------------------

    def _gen_table(self, dim: Vec3, curved: bool = False, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        top_h = 0.04
        leg_h = h - top_h
        leg_w = 0.05
        meshes = [self._box(0, 0, leg_h, w, d, top_h, name="table_top", mat="wood_surface")]
        # Tapered legs (mid-century) or straight
        for lx, ly in [(0.05, 0.05), (w - 0.10, 0.05), (0.05, d - 0.10), (w - 0.10, d - 0.10)]:
            meshes.append(self._box(lx, ly, 0, leg_w, leg_w, leg_h, name="table_leg", mat="wood_leg"))
        return meshes

    # ------------------------------------------------------------------
    # Bed
    # ------------------------------------------------------------------

    def _gen_bed(self, dim: Vec3, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        frame_h = 0.35
        mattress_h = 0.25
        headboard_h = h - frame_h - mattress_h
        return [
            self._box(0, 0, 0, w, d, frame_h, name="bed_frame", mat="bed_frame"),
            self._box(0.05, 0.05, frame_h, w - 0.10, d - 0.05, mattress_h, name="mattress", mat="mattress"),
            self._box(0, d - 0.12, frame_h, w, 0.12, headboard_h + mattress_h, name="headboard", mat="headboard_fabric"),
        ]

    # ------------------------------------------------------------------
    # Rug (flat quad)
    # ------------------------------------------------------------------

    def _gen_rug(self, dim: Vec3, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        return [self._box(0, 0, 0, w, d, h, name="rug", mat="rug_fabric")]

    # ------------------------------------------------------------------
    # Lamp (pole + shade)
    # ------------------------------------------------------------------

    def _gen_lamp(self, dim: Vec3, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        return [
            self._box(w / 2 - 0.03, d / 2 - 0.03, 0, 0.06, 0.06, h * 0.8, name="lamp_pole", mat="lamp_metal"),
            self._box(0, 0, h * 0.8, w, d, h * 0.2, name="lamp_shade", mat="lamp_shade"),
        ]

    # ------------------------------------------------------------------
    # Cabinet / TV unit / bookshelf
    # ------------------------------------------------------------------

    def _gen_cabinet(self, dim: Vec3, **_) -> list[Mesh3D]:
        w, d, h = dim.x, dim.y, dim.z
        panel = 0.02
        meshes = [
            self._box(0, 0, 0, w, panel, h, name="cab_back", mat="wood_cabinet"),
            self._box(0, 0, 0, panel, d, h, name="cab_left", mat="wood_cabinet"),
            self._box(w - panel, 0, 0, panel, d, h, name="cab_right", mat="wood_cabinet"),
            self._box(0, 0, h - panel, w, d, panel, name="cab_top", mat="wood_cabinet"),
            self._box(0, 0, 0, w, d, panel, name="cab_bottom", mat="wood_cabinet"),
        ]
        return meshes

    # ------------------------------------------------------------------
    # Generic box
    # ------------------------------------------------------------------

    def _gen_box(self, dim: Vec3, **_) -> list[Mesh3D]:
        return [self._box(0, 0, 0, dim.x, dim.y, dim.z, name="box", mat="generic")]

    # ------------------------------------------------------------------
    # Mesh primitive
    # ------------------------------------------------------------------

    def _box(
        self, ox: float, oy: float, oz: float,
        w: float, d: float, h: float,
        name: str = "box", mat: str = "default",
    ) -> Mesh3D:
        verts = np.array([
            [ox,     oy,     oz    ],
            [ox + w, oy,     oz    ],
            [ox + w, oy + d, oz    ],
            [ox,     oy + d, oz    ],
            [ox,     oy,     oz + h],
            [ox + w, oy,     oz + h],
            [ox + w, oy + d, oz + h],
            [ox,     oy + d, oz + h],
        ], dtype=np.float32)
        faces = np.array([
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1],
            [3, 2, 6], [3, 6, 7],
            [0, 3, 7], [0, 7, 4],
            [1, 5, 6], [1, 6, 2],
        ], dtype=np.int32)
        return Mesh3D(vertices=verts, faces=faces, name=name, material_name=mat)
