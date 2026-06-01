"""Compute camera positions for various render modes."""

from __future__ import annotations
import math
from typing import Optional

from ..types import Vec3, Room, RoomType, SceneGraph, FloorPlanData


class CameraController:
    """Generate camera positions for standard interior photography angles."""

    EYE_HEIGHT_M = 1.6
    WALKTHROUGH_FOV = 90.0
    STILL_FOV = 50.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def eye_level(self, room: Room, look_toward: Optional[Vec3] = None) -> tuple[Vec3, Vec3]:
        """Standard eye-level shot from slightly inside the room entrance."""
        c = room.centroid
        bbox = self._room_bbox(room)
        if bbox is None:
            return Vec3(c.x, c.y - 3.0, self.EYE_HEIGHT_M), Vec3(c.x, c.y, 1.2)
        cam_y = bbox.min_y + 0.5
        target_y = (bbox.min_y + bbox.max_y) / 2
        pos = Vec3(c.x, cam_y, self.EYE_HEIGHT_M)
        target = look_toward or Vec3(c.x, target_y, 1.2)
        return pos, target

    def top_down(self, plan: FloorPlanData) -> tuple[Vec3, Vec3]:
        """Orthographic top-down for floor plan layout view."""
        if not plan.rooms:
            return Vec3(0, 0, 10), Vec3(0, 0, 0)
        all_x = [p.x for r in plan.rooms for p in r.polygon]
        all_y = [p.y for r in plan.rooms for p in r.polygon]
        cx = (min(all_x) + max(all_x)) / 2
        cy = (min(all_y) + max(all_y)) / 2
        spread = max(max(all_x) - min(all_x), max(all_y) - min(all_y))
        height = spread * 1.2
        return Vec3(cx, cy, height), Vec3(cx, cy, 0)

    def three_quarter(self, room: Room) -> tuple[Vec3, Vec3]:
        """45° elevated three-quarter view (common in design visualisation)."""
        c = room.centroid
        bbox = self._room_bbox(room)
        if bbox is None:
            return Vec3(c.x - 3, c.y - 3, 3.5), Vec3(c.x, c.y, 1.0)
        diag = math.hypot(bbox.width, bbox.height)
        cam_dist = diag * 0.75
        pos = Vec3(
            c.x - cam_dist * 0.7,
            c.y - cam_dist * 0.7,
            cam_dist * 0.6,
        )
        return pos, Vec3(c.x, c.y, 1.0)

    def fireplace_focal(self, scene: SceneGraph) -> tuple[Vec3, Vec3]:
        """Frame shot with fireplace or feature wall as focal point."""
        if scene.floor_plan and scene.floor_plan.rooms:
            living = next(
                (r for r in scene.floor_plan.rooms if r.type == RoomType.LIVING_ROOM),
                scene.floor_plan.rooms[0],
            )
            return self.eye_level(living)
        return Vec3(0, -4, 1.6), Vec3(0, 0, 1.2)

    def walkthrough_sequence(
        self, plan: FloorPlanData, steps: int = 8
    ) -> list[tuple[Vec3, Vec3]]:
        """Generate a camera path through rooms for animation."""
        cameras = []
        for room in plan.rooms[:steps]:
            pos, target = self.eye_level(room)
            cameras.append((pos, target))
        return cameras

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _room_bbox(self, room: Room):
        from ..types import BoundingBox2D
        if not room.polygon:
            return None
        xs = [p.x for p in room.polygon]
        ys = [p.y for p in room.polygon]
        return BoundingBox2D(min(xs), min(ys), max(xs), max(ys))
