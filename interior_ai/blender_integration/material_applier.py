"""Apply PBR materials to SceneGraph elements before Blender export."""

from __future__ import annotations
from ..types import SceneGraph, Material
from ..materials.material_library import MaterialLibrary


class BlenderMaterialApplier:
    """Ensure all scene elements have valid material assignments."""

    def __init__(self):
        self._lib = MaterialLibrary()

    def apply(self, scene: SceneGraph) -> SceneGraph:
        """Fill any missing material slots with sensible defaults."""
        required = {
            "floor": "light_oak",
            "wall_paint": "warm_white",
            "ceiling_white": "warm_white",
            "sofa_fabric": "cream_boucle",
            "chair_fabric": "warm_linen",
            "wood_surface": "light_oak",
            "wood_leg": "walnut",
            "wood_cabinet": "walnut",
            "metal_leg": "brushed_nickel",
            "metal_accent": "brushed_brass",
            "lamp_metal": "brushed_brass",
            "lamp_shade": "ivory_linen",
            "rug_fabric": "warm_linen",
            "glass": "clear_glass",
            "headboard_fabric": "cream_boucle",
            "mattress": "ivory_linen",
            "bed_frame": "light_oak",
            "stair_wood": "walnut",
        }
        for slot, lib_name in required.items():
            if slot not in scene.materials:
                mat = self._lib.get(lib_name)
                if mat:
                    scene.materials[slot] = mat
        return scene
