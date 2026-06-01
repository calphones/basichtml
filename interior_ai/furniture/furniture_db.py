"""In-memory furniture catalogue: CC0 / Poly Haven / procedural assets."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Optional

from ..types import FurnitureCategory, Vec3


@dataclass
class FurnitureAsset:
    id: str
    name: str
    category: FurnitureCategory
    license: str              # "CC0", "CC-BY", "procedural"
    source: str               # "poly_haven", "sketchfab", "procedural"
    model_path: Optional[str]   # relative to assets/furniture/
    thumbnail_path: Optional[str]
    dimensions_m: Vec3        # width, depth, height
    styles: list[str] = field(default_factory=list)   # compatible design styles
    tags: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Built-in catalogue (procedural assets — no external files needed for MVP)
# --------------------------------------------------------------------------

BUILT_IN_ASSETS: list[FurnitureAsset] = [

    # ── Seating ────────────────────────────────────────────────────────────
    FurnitureAsset("sofa_3seat_neutral", "3-Seat Sofa", FurnitureCategory.SEATING,
                   "procedural", "procedural", None, None,
                   Vec3(2.2, 0.95, 0.85),
                   ["modern_organic", "scandinavian", "transitional"],
                   ["sofa", "seating", "neutral"]),

    FurnitureAsset("sectional_curved_cream", "Curved Cream Sectional", FurnitureCategory.SECTIONAL,
                   "procedural", "procedural", None, None,
                   Vec3(3.2, 1.8, 0.85),
                   ["modern_organic", "contemporary_luxury"],
                   ["sectional", "curved", "boucle", "cream"]),

    FurnitureAsset("accent_chair_round", "Round Accent Chair", FurnitureCategory.ACCENT_CHAIR,
                   "procedural", "procedural", None, None,
                   Vec3(0.85, 0.85, 0.80),
                   ["japandi", "modern_organic", "scandinavian"],
                   ["accent", "chair", "round", "cozy"]),

    # ── Tables ─────────────────────────────────────────────────────────────
    FurnitureAsset("coffee_table_rect_oak", "Rectangular Oak Coffee Table",
                   FurnitureCategory.COFFEE_TABLE,
                   "procedural", "procedural", None, None,
                   Vec3(1.2, 0.60, 0.42),
                   ["modern_organic", "scandinavian", "mid_century_modern"],
                   ["coffee_table", "oak", "wood"]),

    FurnitureAsset("coffee_table_round_marble", "Round Marble Coffee Table",
                   FurnitureCategory.COFFEE_TABLE,
                   "procedural", "procedural", None, None,
                   Vec3(0.90, 0.90, 0.40),
                   ["contemporary_luxury", "modern_organic"],
                   ["coffee_table", "round", "marble"]),

    FurnitureAsset("dining_table_rect_6seat", "6-Person Dining Table",
                   FurnitureCategory.DINING_TABLE,
                   "procedural", "procedural", None, None,
                   Vec3(1.80, 0.90, 0.75),
                   ["transitional", "scandinavian", "modern_organic"],
                   ["dining", "table", "6-person"]),

    FurnitureAsset("side_table_round", "Round Side Table",
                   FurnitureCategory.SIDE_TABLE,
                   "procedural", "procedural", None, None,
                   Vec3(0.50, 0.50, 0.58),
                   ["all"],
                   ["side_table", "round", "nightstand"]),

    # ── Beds ───────────────────────────────────────────────────────────────
    FurnitureAsset("bed_queen_upholstered", "Queen Upholstered Bed",
                   FurnitureCategory.BED,
                   "procedural", "procedural", None, None,
                   Vec3(1.52, 2.20, 1.20),
                   ["modern_organic", "contemporary_luxury", "transitional"],
                   ["bed", "queen", "upholstered", "headboard"]),

    FurnitureAsset("bed_king_platform", "King Platform Bed",
                   FurnitureCategory.BED,
                   "procedural", "procedural", None, None,
                   Vec3(1.83, 2.20, 0.40),
                   ["japandi", "minimalist"],
                   ["bed", "king", "platform", "low-profile"]),

    # ── Rugs ───────────────────────────────────────────────────────────────
    FurnitureAsset("rug_jute_natural", "Natural Jute Rug 8×10",
                   FurnitureCategory.RUG,
                   "procedural", "procedural", None, None,
                   Vec3(2.44, 3.05, 0.015),
                   ["modern_organic", "transitional", "scandinavian"],
                   ["rug", "jute", "natural", "texture"]),

    FurnitureAsset("rug_bouclette_ivory", "Ivory Bouclette Rug",
                   FurnitureCategory.RUG,
                   "procedural", "procedural", None, None,
                   Vec3(2.44, 3.05, 0.020),
                   ["modern_organic", "japandi"],
                   ["rug", "boucle", "ivory", "soft"]),

    # ── Lighting ───────────────────────────────────────────────────────────
    FurnitureAsset("floor_lamp_arc", "Arc Floor Lamp",
                   FurnitureCategory.LAMP,
                   "procedural", "procedural", None, None,
                   Vec3(0.35, 0.35, 1.80),
                   ["modern_organic", "mid_century_modern", "scandinavian"],
                   ["lamp", "arc", "floor_lamp"]),

    FurnitureAsset("pendant_cluster", "Pendant Light Cluster",
                   FurnitureCategory.LAMP,
                   "procedural", "procedural", None, None,
                   Vec3(0.6, 0.6, 0.5),
                   ["contemporary_luxury", "modern_organic"],
                   ["lamp", "pendant", "ceiling"]),

    # ── Storage / TV ───────────────────────────────────────────────────────
    FurnitureAsset("tv_unit_floating", "Floating TV Unit",
                   FurnitureCategory.TV_UNIT,
                   "procedural", "procedural", None, None,
                   Vec3(1.80, 0.40, 0.50),
                   ["modern_organic", "japandi", "minimalist"],
                   ["tv_unit", "floating", "media"]),

    FurnitureAsset("bookshelf_open", "Open Bookshelf",
                   FurnitureCategory.BOOKSHELF,
                   "procedural", "procedural", None, None,
                   Vec3(0.80, 0.30, 1.80),
                   ["all"],
                   ["bookshelf", "storage", "books"]),
]


class FurnitureDatabase:
    """Queryable furniture catalogue."""

    def __init__(self, extra_assets_path: Optional[str | Path] = None):
        self._assets: dict[str, FurnitureAsset] = {a.id: a for a in BUILT_IN_ASSETS}
        if extra_assets_path:
            self._load_json(extra_assets_path)

    def get(self, asset_id: str) -> Optional[FurnitureAsset]:
        return self._assets.get(asset_id)

    def by_category(self, category: FurnitureCategory) -> list[FurnitureAsset]:
        return [a for a in self._assets.values() if a.category == category]

    def by_style(self, style_name: str) -> list[FurnitureAsset]:
        return [a for a in self._assets.values()
                if style_name in a.styles or "all" in a.styles]

    def search(self, query: str) -> list[FurnitureAsset]:
        q = query.lower()
        results = []
        for a in self._assets.values():
            if (q in a.name.lower() or
                    any(q in tag for tag in a.tags) or
                    q in a.category.value):
                results.append(a)
        return results

    def all_assets(self) -> list[FurnitureAsset]:
        return list(self._assets.values())

    def _load_json(self, path: str | Path) -> None:
        try:
            with open(path) as f:
                data = json.load(f)
            for item in data:
                asset = FurnitureAsset(
                    id=item["id"],
                    name=item["name"],
                    category=FurnitureCategory(item["category"]),
                    license=item.get("license", "unknown"),
                    source=item.get("source", "custom"),
                    model_path=item.get("model_path"),
                    thumbnail_path=item.get("thumbnail_path"),
                    dimensions_m=Vec3(*item.get("dimensions_m", [1, 1, 1])),
                    styles=item.get("styles", []),
                    tags=item.get("tags", []),
                )
                self._assets[asset.id] = asset
        except Exception as e:
            import warnings
            warnings.warn(f"Failed to load extra assets from {path}: {e}")
