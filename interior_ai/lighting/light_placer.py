"""Automatically place interior light sources based on room geometry and style."""

from __future__ import annotations
import math
from typing import Optional

from ..types import (
    Vec3, Room, RoomType, LightSource, LightType,
    Color, FloorPlanData, SceneGraph, DesignStyle
)
from ..design_engine.style_profiles import STYLE_PROFILES


class LightPlacer:
    """Place realistic interior light fixtures for a given room and style.

    Lighting layers (per residential best practice):
    1. Ambient / general: recessed downlights at regular grid
    2. Task: pendants over dining, under-cabinet for kitchen
    3. Accent: sconces, picture lights, LED strips
    4. Natural: window area lights / HDRI
    """

    RECESSED_SPACING_M = 1.5
    PENDANT_HEIGHT_ABOVE_TABLE = 0.72

    def __init__(self, style: Optional[DesignStyle] = None):
        self._style_profile = STYLE_PROFILES.get(style) if style else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_for_scene(self, scene: SceneGraph) -> SceneGraph:
        if scene.floor_plan is None:
            return scene
        all_lights: list[LightSource] = []
        for room in scene.floor_plan.rooms:
            all_lights.extend(self.place_for_room(room, scene.floor_plan))
        scene.lights = all_lights
        return scene

    def place_for_room(
        self, room: Room, plan: FloorPlanData
    ) -> list[LightSource]:
        lights = []
        lights.extend(self._ambient_grid(room))
        lights.extend(self._task_lights(room))
        lights.extend(self._accent_lights(room))
        return lights

    # ------------------------------------------------------------------
    # Ambient: recessed downlight grid
    # ------------------------------------------------------------------

    def _ambient_grid(self, room: Room) -> list[LightSource]:
        lights = []
        if not room.polygon:
            return lights
        xs = [p.x for p in room.polygon]
        ys = [p.y for p in room.polygon]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        h = room.ceiling_height or 2.7

        color_temp_k = (
            self._style_profile.preferred_color_temp_k
            if self._style_profile else 2700
        )
        color = self._k_to_color(color_temp_k)

        x = x_min + self.RECESSED_SPACING_M / 2
        idx = 0
        while x < x_max:
            y = y_min + self.RECESSED_SPACING_M / 2
            while y < y_max:
                lights.append(LightSource(
                    id=f"recessed_{room.id}_{idx:03d}",
                    type=LightType.RECESSED,
                    position=Vec3(x, y, h - 0.05),
                    color=color,
                    intensity=2.5,
                    room_id=room.id,
                ))
                idx += 1
                y += self.RECESSED_SPACING_M
            x += self.RECESSED_SPACING_M
        return lights

    # ------------------------------------------------------------------
    # Task: pendants, under-cabinet
    # ------------------------------------------------------------------

    def _task_lights(self, room: Room) -> list[LightSource]:
        lights = []
        centroid = room.centroid
        h = room.ceiling_height or 2.7

        if room.type == RoomType.DINING_ROOM:
            lights.append(LightSource(
                id=f"pendant_{room.id}_0",
                type=LightType.PENDANT,
                position=Vec3(centroid.x, centroid.y,
                               h - self.PENDANT_HEIGHT_ABOVE_TABLE),
                color=self._k_to_color(2700),
                intensity=4.0,
                room_id=room.id,
            ))
        elif room.type == RoomType.KITCHEN:
            lights.append(LightSource(
                id=f"undercabinet_{room.id}_0",
                type=LightType.RECESSED,
                position=Vec3(centroid.x, centroid.y, 1.2),
                color=self._k_to_color(3500),
                intensity=3.0,
                room_id=room.id,
            ))
        return lights

    # ------------------------------------------------------------------
    # Accent: sconces, indirect
    # ------------------------------------------------------------------

    def _accent_lights(self, room: Room) -> list[LightSource]:
        lights = []
        use_indirect = (
            self._style_profile.use_indirect_lighting
            if self._style_profile else False
        )
        if not use_indirect:
            return lights
        centroid = room.centroid
        h = room.ceiling_height or 2.7
        # Cove / indirect strip at 2.1 m
        for i, angle in enumerate([0, 90, 180, 270]):
            rad = math.radians(angle)
            ox = centroid.x + math.cos(rad) * 1.5
            oy = centroid.y + math.sin(rad) * 1.5
            lights.append(LightSource(
                id=f"sconce_{room.id}_{i}",
                type=LightType.INDIRECT,
                position=Vec3(ox, oy, 2.1),
                color=self._k_to_color(2400),
                intensity=0.8,
                room_id=room.id,
            ))
        return lights

    # ------------------------------------------------------------------
    # Colour temperature → RGB
    # ------------------------------------------------------------------

    def _k_to_color(self, kelvin: int) -> Color:
        """Approximate correlated colour temperature to sRGB."""
        temp = kelvin / 100.0
        if temp <= 66:
            r = 1.0
            g = max(0.0, min(1.0, (99.4708025861 * math.log(temp) - 161.1195681661) / 255))
        else:
            r = max(0.0, min(1.0, (329.698727466 * (temp - 60) ** -0.1332047592) / 255))
            g = max(0.0, min(1.0, (288.1221695283 * (temp - 60) ** -0.0755148492) / 255))
        if temp >= 66:
            b = 1.0
        elif temp <= 19:
            b = 0.0
        else:
            b = max(0.0, min(1.0, (138.5177312231 * math.log(temp - 10) - 305.0447927307) / 255))
        return Color(r=r, g=g, b=b)


# Avoid circular import
from ..types import RoomType
