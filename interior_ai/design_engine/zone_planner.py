"""Plan functional zones within rooms: conversation, TV, dining, reading, etc."""

from __future__ import annotations
from dataclasses import dataclass, field
import math

from ..types import Vec2, Room, RoomType, BoundingBox2D


@dataclass
class FunctionalZone:
    name: str
    center: Vec2
    radius_m: float
    primary_furniture: list[str] = field(default_factory=list)
    orientation_deg: float = 0.0


class ZonePlanner:
    """Decompose a room into functional zones for furniture grouping.

    Living room zones:
    - Conversation zone (sofa + chairs facing each other)
    - TV/media zone
    - Reading nook (near window if available)
    - Transition zone (near door — keep clear)

    Bedroom zones:
    - Sleep zone (bed)
    - Dressing zone
    - Seating/reading area (if room ≥ 14 m²)
    """

    MIN_READING_NOOK_AREA = 1.5   # m² required for a reading nook zone

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_zones(self, room: Room) -> list[FunctionalZone]:
        planner = {
            RoomType.LIVING_ROOM: self._zones_living,
            RoomType.DINING_ROOM: self._zones_dining,
            RoomType.BEDROOM: self._zones_bedroom,
            RoomType.OFFICE: self._zones_office,
        }.get(room.type, self._zones_generic)
        return planner(room)

    # ------------------------------------------------------------------
    # Room-specific zone plans
    # ------------------------------------------------------------------

    def _zones_living(self, room: Room) -> list[FunctionalZone]:
        centroid = room.centroid
        bbox = self._bbox(room)
        if bbox is None:
            return []
        zones = []
        # Primary conversation zone (centre of room)
        zones.append(FunctionalZone(
            name="conversation",
            center=centroid,
            radius_m=2.0,
            primary_furniture=["sofa", "coffee_table", "accent_chair"],
        ))
        # TV zone (towards one wall, facing conversation zone)
        tv_x = centroid.x + bbox.width * 0.25
        zones.append(FunctionalZone(
            name="tv_media",
            center=Vec2(tv_x, centroid.y),
            radius_m=1.2,
            primary_furniture=["tv_unit"],
            orientation_deg=180,
        ))
        # Reading nook near far wall
        if room.area > 18:
            zones.append(FunctionalZone(
                name="reading_nook",
                center=Vec2(bbox.min_x + 1.0, centroid.y),
                radius_m=1.0,
                primary_furniture=["accent_chair", "side_table", "floor_lamp"],
                orientation_deg=90,
            ))
        return zones

    def _zones_dining(self, room: Room) -> list[FunctionalZone]:
        centroid = room.centroid
        return [FunctionalZone(
            name="dining",
            center=centroid,
            radius_m=2.0,
            primary_furniture=["dining_table", "dining_chairs"],
        )]

    def _zones_bedroom(self, room: Room) -> list[FunctionalZone]:
        centroid = room.centroid
        bbox = self._bbox(room)
        if bbox is None:
            return []
        zones = [FunctionalZone(
            name="sleep",
            center=Vec2(centroid.x, bbox.max_y - 1.5),
            radius_m=1.8,
            primary_furniture=["bed", "side_table", "side_table"],
        )]
        if room.area > 14:
            zones.append(FunctionalZone(
                name="seating",
                center=Vec2(centroid.x - bbox.width * 0.3, bbox.min_y + 1.5),
                radius_m=1.0,
                primary_furniture=["accent_chair", "side_table"],
            ))
        return zones

    def _zones_office(self, room: Room) -> list[FunctionalZone]:
        centroid = room.centroid
        bbox = self._bbox(room)
        if bbox is None:
            return []
        return [FunctionalZone(
            name="work",
            center=Vec2(centroid.x, bbox.max_y - 1.0),
            radius_m=1.2,
            primary_furniture=["desk", "chair"],
        )]

    def _zones_generic(self, room: Room) -> list[FunctionalZone]:
        return [FunctionalZone(
            name="general",
            center=room.centroid,
            radius_m=1.5,
            primary_furniture=[],
        )]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bbox(self, room: Room) -> BoundingBox2D | None:
        if not room.polygon:
            return None
        xs = [p.x for p in room.polygon]
        ys = [p.y for p in room.polygon]
        return BoundingBox2D(min(xs), min(ys), max(xs), max(ys))
