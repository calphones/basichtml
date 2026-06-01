"""Shared data structures used across all pipeline modules."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DesignStyle(str, Enum):
    MODERN_ORGANIC = "modern_organic"
    JAPANDI = "japandi"
    SCANDINAVIAN = "scandinavian"
    CONTEMPORARY_LUXURY = "contemporary_luxury"
    MINIMALIST = "minimalist"
    TRANSITIONAL = "transitional"
    MID_CENTURY_MODERN = "mid_century_modern"


class RoomType(str, Enum):
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    KITCHEN = "kitchen"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    OFFICE = "office"
    HALLWAY = "hallway"
    FOYER = "foyer"
    LAUNDRY = "laundry"
    GARAGE = "garage"
    UNKNOWN = "unknown"


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    ARCHWAY = "archway"
    SLIDING_DOOR = "sliding_door"


class FurnitureCategory(str, Enum):
    SEATING = "seating"
    SECTIONAL = "sectional"
    DINING_TABLE = "dining_table"
    COFFEE_TABLE = "coffee_table"
    RUG = "rug"
    BED = "bed"
    LAMP = "lamp"
    DECOR = "decor"
    STORAGE = "storage"
    TV_UNIT = "tv_unit"
    ACCENT_CHAIR = "accent_chair"
    SIDE_TABLE = "side_table"
    BOOKSHELF = "bookshelf"
    DESK = "desk"


class MaterialType(str, Enum):
    WOOD = "wood"
    STONE = "stone"
    MARBLE = "marble"
    MATTE_PAINT = "matte_paint"
    BRUSHED_METAL = "brushed_metal"
    LINEN = "linen"
    BOUCLE = "boucle"
    LEATHER = "leather"
    VELVET = "velvet"
    CERAMIC = "ceramic"
    GLASS = "glass"
    CONCRETE = "concrete"


class LightType(str, Enum):
    NATURAL = "natural"
    RECESSED = "recessed"
    PENDANT = "pendant"
    SCONCE = "sconce"
    FLOOR_LAMP = "floor_lamp"
    TABLE_LAMP = "table_lamp"
    INDIRECT = "indirect"
    HDRI = "hdri"


class RenderMode(str, Enum):
    PREVIEW = "preview"
    PHOTOREAL = "photoreal"
    TOPDOWN = "topdown"
    WALKTHROUGH = "walkthrough"
    MATERIAL_BOARD = "material_board"


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

@dataclass
class Vec2:
    x: float
    y: float

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y])

    def distance_to(self, other: Vec2) -> float:
        return float(np.linalg.norm(self.as_array() - other.as_array()))

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)


@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)


@dataclass
class BoundingBox2D:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> Vec2:
        return Vec2((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)


# ---------------------------------------------------------------------------
# Architectural elements
# ---------------------------------------------------------------------------

@dataclass
class WallSegment:
    start: Vec2
    end: Vec2
    thickness: float = 0.2       # metres
    height: float = 2.7          # metres
    is_exterior: bool = False
    id: str = ""

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Vec2:
        return Vec2((self.start.x + self.end.x) / 2, (self.start.y + self.end.y) / 2)

    @property
    def direction(self) -> np.ndarray:
        d = self.end.as_array() - self.start.as_array()
        norm = np.linalg.norm(d)
        return d / norm if norm > 0 else d


@dataclass
class Opening:
    type: OpeningType
    wall_id: str
    position_along_wall: float   # 0..1 normalised
    width: float                  # metres
    height: float                 # metres
    sill_height: float = 0.0      # for windows


@dataclass
class StaircaseElement:
    position: Vec2
    direction_degrees: float      # 0 = north, 90 = east
    step_count: int = 13
    width: float = 0.9
    rise_per_step: float = 0.19
    run_per_step: float = 0.26
    has_landing: bool = False
    landing_position: Optional[Vec2] = None
    open_to_below: bool = False


@dataclass
class Room:
    id: str
    type: RoomType
    polygon: list[Vec2]           # ordered vertices
    ceiling_height: float = 2.7
    label: str = ""
    floor: int = 0                # storey index
    area: float = 0.0             # m², computed from polygon

    def compute_area(self) -> float:
        pts = self.polygon
        n = len(pts)
        a = 0.0
        for i in range(n):
            j = (i + 1) % n
            a += pts[i].x * pts[j].y
            a -= pts[j].x * pts[i].y
        self.area = abs(a) / 2.0
        return self.area

    @property
    def centroid(self) -> Vec2:
        xs = [p.x for p in self.polygon]
        ys = [p.y for p in self.polygon]
        return Vec2(sum(xs) / len(xs), sum(ys) / len(ys))


@dataclass
class FloorPlanData:
    """Fully parsed and vectorised floor plan."""
    rooms: list[Room] = field(default_factory=list)
    walls: list[WallSegment] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    stairs: list[StaircaseElement] = field(default_factory=list)
    scale_m_per_px: float = 1.0   # metres per pixel in source image
    storeys: int = 1
    source_image_path: str = ""
    raw_dimensions: dict = field(default_factory=dict)  # extracted text dims


# ---------------------------------------------------------------------------
# Furniture & scene
# ---------------------------------------------------------------------------

@dataclass
class Color:
    r: float   # 0..1
    g: float
    b: float
    a: float = 1.0

    @classmethod
    def from_hex(cls, hex_str: str) -> Color:
        h = hex_str.lstrip("#")
        r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        return cls(r, g, b)

    def to_hex(self) -> str:
        return "#{:02x}{:02x}{:02x}".format(
            int(self.r * 255), int(self.g * 255), int(self.b * 255)
        )


@dataclass
class Material:
    name: str
    type: MaterialType
    base_color: Color
    roughness: float = 0.5
    metallic: float = 0.0
    texture_path: Optional[str] = None
    normal_map_path: Optional[str] = None
    scale: float = 1.0


@dataclass
class FurnitureItem:
    id: str
    category: FurnitureCategory
    name: str
    position: Vec3
    rotation_z: float = 0.0       # degrees
    scale: Vec3 = field(default_factory=lambda: Vec3(1, 1, 1))
    model_path: Optional[str] = None
    material: Optional[Material] = None
    bounding_box: Optional[BoundingBox2D] = None
    room_id: str = ""
    clearance_radius: float = 0.6  # metres around item


@dataclass
class LightSource:
    id: str
    type: LightType
    position: Vec3
    color: Color = field(default_factory=lambda: Color(1.0, 0.95, 0.8))
    intensity: float = 1.0
    radius: float = 0.1
    room_id: str = ""


@dataclass
class SceneGraph:
    """Complete 3D scene representation."""
    floor_plan: Optional[FloorPlanData] = None
    furniture: list[FurnitureItem] = field(default_factory=list)
    lights: list[LightSource] = field(default_factory=list)
    materials: dict[str, Material] = field(default_factory=dict)  # name → Material
    hdri_path: Optional[str] = None
    camera_position: Optional[Vec3] = None
    camera_target: Optional[Vec3] = None
    camera_fov: float = 60.0
    style: Optional[DesignStyle] = None
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# User input / preferences
# ---------------------------------------------------------------------------

@dataclass
class Palette:
    primary: Color
    secondary: Color
    accent: Color
    neutral: Color
    description: str = ""


@dataclass
class DesignSpec:
    style: DesignStyle = DesignStyle.MODERN_ORGANIC
    palette: Optional[Palette] = None
    priority_rooms: list[RoomType] = field(default_factory=list)
    inspiration_image_paths: list[str] = field(default_factory=list)
    natural_language_prompt: str = ""
    max_furniture_budget_usd: Optional[float] = None
    family_friendly: bool = True
    pet_friendly: bool = False
    extra_storage: bool = False


@dataclass
class RenderRequest:
    scene: SceneGraph
    mode: RenderMode = RenderMode.PREVIEW
    resolution: tuple[int, int] = (1920, 1080)
    samples: int = 64
    output_path: str = "/tmp/render.png"
    camera_position: Optional[Vec3] = None
    camera_target: Optional[Vec3] = None
