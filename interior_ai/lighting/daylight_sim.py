"""Simulate natural daylight from window openings."""

from __future__ import annotations
import math
from typing import Optional

from ..types import (
    Vec3, LightSource, LightType, Color,
    FloorPlanData, Opening, OpeningType, WallSegment
)


class DaylightSimulator:
    """Create physically-based daylight area lights from window geometry.

    Each window becomes:
    - An area light positioned just outside the glass plane (exterior side)
    - Colour temperature matching time-of-day setting
    - Intensity proportional to window area

    Works with Blender's area light type for accurate falloff.
    """

    BASE_INTENSITY_PER_SQ_M = 300.0   # lux-equivalent per m² of window glass

    def __init__(self, time_of_day: str = "midday"):
        self._tod = time_of_day

    def simulate(self, plan: FloorPlanData) -> list[LightSource]:
        """Generate daylight LightSources for all window openings."""
        lights = []
        for i, opening in enumerate(plan.openings):
            if opening.type != OpeningType.WINDOW:
                continue
            wall = self._find_wall(opening.wall_id, plan.walls)
            if wall is None:
                continue
            pos, normal = self._window_position(opening, wall)
            area = opening.width * opening.height
            intensity = area * self.BASE_INTENSITY_PER_SQ_M * self._tod_multiplier()
            lights.append(LightSource(
                id=f"daylight_{i:03d}",
                type=LightType.NATURAL,
                position=pos,
                color=self._tod_color(),
                intensity=intensity,
            ))
        return lights

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_wall(self, wall_id: str, walls: list[WallSegment]) -> Optional[WallSegment]:
        for w in walls:
            if w.id == wall_id:
                return w
        return None

    def _window_position(
        self, opening: Opening, wall: WallSegment
    ) -> tuple[Vec3, tuple[float, float]]:
        t = opening.position_along_wall
        wx = wall.start.x + t * (wall.end.x - wall.start.x)
        wy = wall.start.y + t * (wall.end.y - wall.start.y)
        wz = opening.sill_height + opening.height / 2

        # Normal vector (perpendicular to wall, pointing outward)
        dx = wall.end.x - wall.start.x
        dy = wall.end.y - wall.start.y
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length  # 90° rotation

        # Place light 0.1 m outside the wall
        pos = Vec3(wx + nx * 0.1, wy + ny * 0.1, wz)
        return pos, (nx, ny)

    def _tod_multiplier(self) -> float:
        return {
            "morning": 0.6,
            "midday": 1.0,
            "afternoon": 0.85,
            "golden_hour": 0.7,
            "evening": 0.3,
            "night": 0.0,
        }.get(self._tod, 1.0)

    def _tod_color(self) -> Color:
        return {
            "morning":     Color(0.98, 0.94, 0.88),
            "midday":      Color(1.00, 0.99, 0.96),
            "afternoon":   Color(1.00, 0.96, 0.88),
            "golden_hour": Color(1.00, 0.85, 0.60),
            "evening":     Color(0.95, 0.78, 0.60),
            "night":       Color(0.40, 0.45, 0.60),
        }.get(self._tod, Color(1.0, 0.99, 0.96))
