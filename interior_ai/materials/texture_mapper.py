"""Map material names and palette colors onto SceneGraph elements."""

from __future__ import annotations
from pathlib import Path

from ..types import SceneGraph, Material, MaterialType, Color, DesignStyle
from .material_library import MaterialLibrary


class TextureMapper:
    """Apply materials from the library to all scene elements.

    Assignment logic:
    - Floors → style-derived wood/stone material
    - Walls → style-derived paint colour
    - Furniture → category-specific fabric/wood per style profile
    - Metals → style accent metal finish
    """

    def __init__(self, assets_root: str | Path = "./assets"):
        self._lib = MaterialLibrary()
        self._assets_root = Path(assets_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_style(self, scene: SceneGraph) -> SceneGraph:
        """Apply style-consistent materials to all scene elements."""
        style = scene.style
        if style is None:
            style = DesignStyle.MODERN_ORGANIC

        from ..design_engine.style_profiles import STYLE_PROFILES
        profile = STYLE_PROFILES.get(style)
        if profile is None:
            return scene

        # Floor material
        floor_mat = self._lib.get_style_floor(style.value)
        scene.materials["floor"] = floor_mat

        # Wall material
        wall_mat = Material(
            name="wall_paint",
            type=MaterialType.MATTE_PAINT,
            base_color=Color.from_hex(profile.wall_color_hex),
            roughness=0.95,
        )
        scene.materials["wall_paint"] = wall_mat

        # Ceiling
        ceiling_mat = Material(
            name="ceiling_white",
            type=MaterialType.MATTE_PAINT,
            base_color=Color.from_hex(profile.trim_color_hex),
            roughness=0.95,
        )
        scene.materials["ceiling_white"] = ceiling_mat

        # Primary furniture fabric
        primary_type = profile.primary_materials[0] if profile.primary_materials else MaterialType.LINEN
        sofa_mat = self._pick_fabric(primary_type, profile.palette.primary if profile.palette else None)
        scene.materials["sofa_fabric"] = sofa_mat
        scene.materials["chair_fabric"] = sofa_mat

        # Accent metal
        metal_mat = self._lib.get(profile.metal_finish) or self._lib.get("brushed_brass")
        if metal_mat:
            scene.materials["metal_accent"] = metal_mat
            scene.materials["lamp_metal"] = metal_mat

        # Wood surfaces
        wood_mat = floor_mat
        scene.materials["wood_surface"] = wood_mat
        scene.materials["wood_leg"] = wood_mat
        scene.materials["wood_cabinet"] = wood_mat

        # Rug
        rug_mat = self._pick_fabric(MaterialType.LINEN, profile.palette.secondary if profile.palette else None)
        rug_mat.name = "rug_fabric"
        scene.materials["rug_fabric"] = rug_mat

        return scene

    def apply_palette(self, scene: SceneGraph, palette) -> SceneGraph:
        """Tint scene materials to match a user-extracted palette."""
        if palette is None:
            return scene
        if "wall_paint" in scene.materials:
            scene.materials["wall_paint"].base_color = palette.neutral
        if "sofa_fabric" in scene.materials:
            scene.materials["sofa_fabric"].base_color = palette.primary
        if "rug_fabric" in scene.materials:
            scene.materials["rug_fabric"].base_color = palette.secondary
        if "metal_accent" in scene.materials:
            scene.materials["metal_accent"].base_color = palette.accent
        return scene

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_fabric(self, mtype: MaterialType, tint: Color | None) -> Material:
        fabric_map = {
            MaterialType.BOUCLE: self._lib.get("cream_boucle"),
            MaterialType.LINEN: self._lib.get("warm_linen"),
            MaterialType.VELVET: self._lib.get("sage_velvet"),
            MaterialType.LEATHER: self._lib.get("cognac_leather"),
        }
        mat = fabric_map.get(mtype) or self._lib.get("warm_linen")
        if mat and tint:
            import copy
            mat = copy.copy(mat)
            mat.base_color = tint
        return mat or Material(
            name="fabric_default",
            type=MaterialType.LINEN,
            base_color=tint or Color(0.85, 0.80, 0.72),
        )
