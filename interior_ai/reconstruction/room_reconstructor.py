"""High-level pipeline: combine floor plan + photos into a SceneGraph."""

from __future__ import annotations
from pathlib import Path
import numpy as np

from ..types import (
    Vec3, SceneGraph, FloorPlanData, DesignSpec,
    LightSource, LightType, Color
)
from .geometry_builder import GeometryBuilder, ArchitecturalShell
from .depth_estimator import DepthEstimator
from ..input_parser.image_parser import ImageParser
from ..input_parser.inspiration_parser import InspirationParser


class RoomReconstructor:
    """Orchestrate all reconstruction steps into a single SceneGraph.

    Accepts:
    - parsed FloorPlanData
    - optional room photo paths
    - optional inspiration image paths
    - DesignSpec (style, palette preferences)

    Produces a SceneGraph ready for the design engine and renderer.
    """

    def __init__(
        self,
        depth_model_path: str | Path | None = None,
        ceiling_height: float = 2.74,
    ):
        self._geometry = GeometryBuilder(default_ceiling_height=ceiling_height)
        self._depth = DepthEstimator(model_path=depth_model_path)
        self._img_parser = ImageParser()
        self._insp_parser = InspirationParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reconstruct(
        self,
        floor_plan: FloorPlanData,
        room_photos: list[str | Path] | None = None,
        spec: DesignSpec | None = None,
    ) -> SceneGraph:
        shell = self._geometry.build(floor_plan)
        scene = SceneGraph(floor_plan=floor_plan)

        # Extract palette from inspiration images if provided
        if spec and spec.inspiration_image_paths:
            palette = self._extract_palette(spec.inspiration_image_paths[0])
            if spec.palette is None:
                spec.palette = palette

        if spec:
            scene.style = spec.style

        # Analyse room photos for depth / additional context
        if room_photos:
            self._integrate_room_photos(scene, room_photos)

        # Add default natural lighting
        scene.lights = self._default_lights(floor_plan)
        scene.camera_position = self._default_camera(floor_plan)
        scene.camera_target = Vec3(0, 0, 1.2)
        scene.metadata["shell"] = shell

        return scene

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_palette(self, image_path: str | Path):
        try:
            return self._insp_parser.extract_palette(image_path)
        except Exception:
            return None

    def _integrate_room_photos(
        self, scene: SceneGraph, photos: list[str | Path]
    ) -> None:
        for photo_path in photos:
            try:
                img = self._img_parser.load(photo_path)
                preprocessed = self._img_parser.preprocess_room_photo(img)
                depth = self._depth.estimate(preprocessed)
                scene.metadata[f"depth_{Path(photo_path).stem}"] = depth
            except Exception:
                continue

    def _default_lights(self, floor_plan: FloorPlanData) -> list[LightSource]:
        lights = []
        # Natural daylight from windows
        for i, opening in enumerate(floor_plan.openings):
            from ..types import OpeningType
            if opening.type != OpeningType.WINDOW:
                continue
            wall = next((w for w in floor_plan.walls if w.id == opening.wall_id), None)
            if wall is None:
                continue
            t = opening.position_along_wall
            wx = wall.start.x + t * (wall.end.x - wall.start.x)
            wy = wall.start.y + t * (wall.end.y - wall.start.y)
            lights.append(LightSource(
                id=f"daylight_{i}",
                type=LightType.NATURAL,
                position=Vec3(wx, wy, 2.0),
                color=Color(1.0, 0.98, 0.92),
                intensity=5.0,
            ))
        # Fallback: single overhead if no windows found
        if not lights:
            cx = float(np.mean([w.start.x for w in floor_plan.walls])) if floor_plan.walls else 0.0
            cy = float(np.mean([w.start.y for w in floor_plan.walls])) if floor_plan.walls else 0.0
            lights.append(LightSource(
                id="overhead_0",
                type=LightType.RECESSED,
                position=Vec3(cx, cy, 2.7),
                intensity=3.0,
            ))
        return lights

    def _default_camera(self, floor_plan: FloorPlanData) -> Vec3:
        if not floor_plan.rooms:
            return Vec3(0, -5, 1.6)
        living = next(
            (r for r in floor_plan.rooms
             if r.type.value == "living_room"),
            floor_plan.rooms[0],
        )
        c = living.centroid
        # Position camera at one wall, 1.6 m height (eye level)
        return Vec3(c.x, c.y - 3.0, 1.6)
