"""Build a complete Blender-ready scene dict from a SceneGraph."""

from __future__ import annotations

from ..types import SceneGraph, DesignStyle
from ..materials.texture_mapper import TextureMapper
from ..lighting.light_placer import LightPlacer
from ..lighting.hdri_manager import HDRIManager


class BlenderSceneBuilder:
    """Prepare and enrich a SceneGraph for Blender rendering.

    Applies:
    - Style-consistent materials via TextureMapper
    - Palette tinting from inspiration images
    - Auto-lighting via LightPlacer
    - Best-fit HDRI selection
    - Camera positioning
    """

    def __init__(self, assets_root: str = "./assets"):
        self._texture_mapper = TextureMapper(assets_root)
        self._hdri_manager = HDRIManager(f"{assets_root}/hdri")

    def prepare(self, scene: SceneGraph, spec=None) -> SceneGraph:
        """Enrich scene with materials, lights, and HDRI before rendering."""
        # Apply style materials
        scene = self._texture_mapper.apply_style(scene)

        # Tint with palette if available
        if spec and spec.palette:
            scene = self._texture_mapper.apply_palette(scene, spec.palette)
        elif spec and spec.inspiration_image_paths:
            from ..materials.palette_extractor import PaletteExtractor
            try:
                palette = PaletteExtractor().from_images(spec.inspiration_image_paths)
                scene = self._texture_mapper.apply_palette(scene, palette)
            except Exception:
                pass

        # Place lights if none set
        if not scene.lights and scene.floor_plan:
            style = scene.style or DesignStyle.MODERN_ORGANIC
            placer = LightPlacer(style=style)
            scene = placer.place_for_scene(scene)

        # Select HDRI
        if scene.hdri_path is None:
            style_name = scene.style.value if scene.style else "modern_organic"
            hdri_id = self._hdri_manager.best_for_style(style_name)
            if spec and spec.natural_language_prompt:
                hdri_id = self._hdri_manager.best_for_prompt(spec.natural_language_prompt)
            hdri_path = self._hdri_manager.resolve(hdri_id)
            if hdri_path:
                scene.hdri_path = str(hdri_path)

        return scene
