"""Built-in PBR material definitions for walls, floors, furniture, and accents."""

from __future__ import annotations
from ..types import Material, MaterialType, Color


def _mat(
    name: str, mtype: MaterialType, hex_color: str,
    roughness: float = 0.5, metallic: float = 0.0,
    texture: str | None = None, scale: float = 1.0,
) -> Material:
    return Material(
        name=name,
        type=mtype,
        base_color=Color.from_hex(hex_color),
        roughness=roughness,
        metallic=metallic,
        texture_path=texture,
        scale=scale,
    )


MATERIAL_LIBRARY: dict[str, Material] = {

    # ── Paints ──────────────────────────────────────────────────────────
    "warm_white":           _mat("warm_white",          MaterialType.MATTE_PAINT, "#FAF7F2", 0.95),
    "greige":               _mat("greige",              MaterialType.MATTE_PAINT, "#C8BFB0", 0.95),
    "charcoal":             _mat("charcoal",            MaterialType.MATTE_PAINT, "#3A3A3A", 0.90),
    "cream":                _mat("cream",               MaterialType.MATTE_PAINT, "#F5F0E8", 0.95),
    "sage":                 _mat("sage",                MaterialType.MATTE_PAINT, "#8FA882", 0.92),
    "dusty_blue":           _mat("dusty_blue",          MaterialType.MATTE_PAINT, "#8EA8B8", 0.90),
    "terracotta":           _mat("terracotta",          MaterialType.MATTE_PAINT, "#C2714F", 0.88),

    # ── Wood floors ─────────────────────────────────────────────────────
    "light_oak":            _mat("light_oak",           MaterialType.WOOD, "#C8A86A", 0.55, 0.0,
                                  "textures/light_oak_floor.jpg", 2.0),
    "white_oak":            _mat("white_oak",           MaterialType.WOOD, "#D6C49A", 0.60, 0.0,
                                  "textures/white_oak_floor.jpg", 2.0),
    "walnut":               _mat("walnut",              MaterialType.WOOD, "#6B4C38", 0.50, 0.0,
                                  "textures/walnut_floor.jpg", 2.0),
    "natural_maple":        _mat("natural_maple",       MaterialType.WOOD, "#D4B896", 0.58, 0.0),
    "teak_parquet":         _mat("teak_parquet",        MaterialType.WOOD, "#9C6D3E", 0.52, 0.0),
    "dark_walnut":          _mat("dark_walnut",         MaterialType.WOOD, "#3D2810", 0.45, 0.0),

    # ── Stone / tile ────────────────────────────────────────────────────
    "white_marble":         _mat("white_marble",        MaterialType.MARBLE, "#F0EDE8", 0.10, 0.0,
                                  "textures/white_marble.jpg"),
    "calacatta_gold":       _mat("calacatta_gold",      MaterialType.MARBLE, "#E8E0D4", 0.12, 0.0,
                                  "textures/calacatta_gold.jpg"),
    "slate_grey":           _mat("slate_grey",          MaterialType.STONE, "#8C8C8C", 0.80, 0.0),
    "travertine":           _mat("travertine",          MaterialType.STONE, "#C8B89A", 0.55, 0.0),

    # ── Metals ──────────────────────────────────────────────────────────
    "brushed_brass":        _mat("brushed_brass",       MaterialType.BRUSHED_METAL, "#C8A04A", 0.35, 0.90),
    "brushed_nickel":       _mat("brushed_nickel",      MaterialType.BRUSHED_METAL, "#C0C0C0", 0.25, 0.85),
    "matte_black_metal":    _mat("matte_black_metal",   MaterialType.BRUSHED_METAL, "#1A1A1A", 0.70, 0.80),
    "brushed_gold":         _mat("brushed_gold",        MaterialType.BRUSHED_METAL, "#D4AF37", 0.30, 0.92),

    # ── Textiles ────────────────────────────────────────────────────────
    "cream_boucle":         _mat("cream_boucle",        MaterialType.BOUCLE,  "#F0EBE0", 0.95),
    "warm_linen":           _mat("warm_linen",          MaterialType.LINEN,   "#D4C4A8", 0.90),
    "sage_velvet":          _mat("sage_velvet",         MaterialType.VELVET,  "#7A9B7A", 0.80),
    "cognac_leather":       _mat("cognac_leather",      MaterialType.LEATHER, "#8B5E3C", 0.45),
    "ivory_linen":          _mat("ivory_linen",         MaterialType.LINEN,   "#FAF5EA", 0.90),

    # ── Glass ───────────────────────────────────────────────────────────
    "clear_glass":          _mat("clear_glass",         MaterialType.GLASS,   "#E8F4F8", 0.05, 0.0),
    "frosted_glass":        _mat("frosted_glass",       MaterialType.GLASS,   "#EEF2F5", 0.60, 0.0),
}


class MaterialLibrary:
    """Query and resolve materials by name or type."""

    def __init__(self):
        self._mats = dict(MATERIAL_LIBRARY)

    def get(self, name: str) -> Material | None:
        return self._mats.get(name)

    def by_type(self, mtype: MaterialType) -> list[Material]:
        return [m for m in self._mats.values() if m.type == mtype]

    def add(self, material: Material) -> None:
        self._mats[material.name] = material

    def floor_materials(self) -> list[Material]:
        return self.by_type(MaterialType.WOOD) + [
            m for m in self.by_type(MaterialType.STONE)
        ]

    def wall_materials(self) -> list[Material]:
        return self.by_type(MaterialType.MATTE_PAINT)

    def get_style_floor(self, style_name: str) -> Material:
        from ..design_engine.style_profiles import STYLE_PROFILES
        from ..types import DesignStyle
        try:
            profile = STYLE_PROFILES[DesignStyle(style_name)]
            mat = self.get(profile.floor_finish)
            return mat or self._mats["light_oak"]
        except (KeyError, ValueError):
            return self._mats["light_oak"]

    def all_names(self) -> list[str]:
        return list(self._mats.keys())
