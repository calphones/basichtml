"""Style profiles: colour palettes, material preferences, and furniture guidance per style."""

from __future__ import annotations
from dataclasses import dataclass, field

from ..types import DesignStyle, Color, Palette, MaterialType


@dataclass
class StyleProfile:
    style: DesignStyle
    description: str
    palette: Palette
    primary_materials: list[MaterialType]
    secondary_materials: list[MaterialType]
    # Furniture geometry preferences
    prefer_curved: bool = False
    prefer_low_profile: bool = False
    prefer_natural_textures: bool = False
    # Typical finishes
    wall_color_hex: str = "#F5F0EB"
    trim_color_hex: str = "#FFFFFF"
    floor_finish: str = "light_oak"
    metal_finish: str = "brushed_brass"
    # Typical furniture footprints (m) — used for procedural scaling
    sofa_depth_m: float = 0.90
    sofa_length_m: float = 2.80
    dining_table_m: tuple[float, float] = (1.0, 2.0)
    coffee_table_h_m: float = 0.42
    # Lighting
    preferred_color_temp_k: int = 2700
    use_pendant_lighting: bool = True
    use_indirect_lighting: bool = False
    # NL descriptor keywords (used by LLM intent matching)
    keywords: list[str] = field(default_factory=list)


def _palette(p, s, a, n, desc="") -> Palette:
    return Palette(
        primary=Color.from_hex(p),
        secondary=Color.from_hex(s),
        accent=Color.from_hex(a),
        neutral=Color.from_hex(n),
        description=desc,
    )


STYLE_PROFILES: dict[DesignStyle, StyleProfile] = {

    DesignStyle.MODERN_ORGANIC: StyleProfile(
        style=DesignStyle.MODERN_ORGANIC,
        description="Warm neutrals, natural materials, curved silhouettes, soft lighting.",
        palette=_palette("#C9B99A", "#E8DFD0", "#3D2B1F", "#F5F0EB", "warm sand and espresso"),
        primary_materials=[MaterialType.WOOD, MaterialType.LINEN, MaterialType.BOUCLE],
        secondary_materials=[MaterialType.LEATHER, MaterialType.STONE],
        prefer_curved=True,
        prefer_natural_textures=True,
        wall_color_hex="#F0EAE0",
        trim_color_hex="#EDE7DC",
        floor_finish="light_oak",
        metal_finish="brushed_brass",
        preferred_color_temp_k=2700,
        use_indirect_lighting=True,
        keywords=["warm", "organic", "natural", "curved", "cozy", "earthy", "boucle"],
    ),

    DesignStyle.JAPANDI: StyleProfile(
        style=DesignStyle.JAPANDI,
        description="Wabi-sabi minimalism: muted tones, raw wood, zen restraint.",
        palette=_palette("#A89880", "#D4C9B8", "#2C2C2C", "#F2EDE8", "natural linen and charcoal"),
        primary_materials=[MaterialType.WOOD, MaterialType.LINEN, MaterialType.CERAMIC],
        secondary_materials=[MaterialType.CONCRETE, MaterialType.STONE],
        prefer_low_profile=True,
        prefer_natural_textures=True,
        wall_color_hex="#EAE4DC",
        trim_color_hex="#E0D9CF",
        floor_finish="natural_maple",
        metal_finish="brushed_nickel",
        preferred_color_temp_k=3000,
        use_pendant_lighting=False,
        keywords=["japandi", "zen", "wabi-sabi", "minimal", "serene", "quiet", "raw"],
    ),

    DesignStyle.SCANDINAVIAN: StyleProfile(
        style=DesignStyle.SCANDINAVIAN,
        description="Bright whites, blonde wood, functional form, hygge warmth.",
        palette=_palette("#FFFFFF", "#F7F5F2", "#2B2B2B", "#E8E4DF", "crisp white and birch"),
        primary_materials=[MaterialType.WOOD, MaterialType.LINEN, MaterialType.MATTE_PAINT],
        secondary_materials=[MaterialType.GLASS, MaterialType.CERAMIC],
        wall_color_hex="#FAFAFA",
        trim_color_hex="#FFFFFF",
        floor_finish="white_oak",
        metal_finish="brushed_nickel",
        preferred_color_temp_k=3000,
        keywords=["scandinavian", "nordic", "hygge", "bright", "clean", "white", "birch"],
    ),

    DesignStyle.CONTEMPORARY_LUXURY: StyleProfile(
        style=DesignStyle.CONTEMPORARY_LUXURY,
        description="Rich materials, sculptural forms, high-contrast drama.",
        palette=_palette("#1A1A1A", "#C8A96E", "#F0F0F0", "#2D2D2D", "onyx and gold"),
        primary_materials=[MaterialType.MARBLE, MaterialType.LEATHER, MaterialType.BRUSHED_METAL],
        secondary_materials=[MaterialType.VELVET, MaterialType.GLASS],
        prefer_low_profile=True,
        wall_color_hex="#F2F0ED",
        trim_color_hex="#FFFFFF",
        floor_finish="dark_walnut",
        metal_finish="brushed_gold",
        preferred_color_temp_k=2700,
        use_indirect_lighting=True,
        keywords=["luxury", "high-end", "dramatic", "marble", "velvet", "dark", "rich"],
    ),

    DesignStyle.MINIMALIST: StyleProfile(
        style=DesignStyle.MINIMALIST,
        description="Absolute restraint: monochrome palette, negative space, every piece intentional.",
        palette=_palette("#FFFFFF", "#E8E8E8", "#1C1C1C", "#F5F5F5", "pure white and charcoal"),
        primary_materials=[MaterialType.MATTE_PAINT, MaterialType.CONCRETE, MaterialType.GLASS],
        secondary_materials=[MaterialType.WOOD, MaterialType.BRUSHED_METAL],
        prefer_low_profile=True,
        wall_color_hex="#F8F8F8",
        trim_color_hex="#FFFFFF",
        floor_finish="polished_concrete",
        metal_finish="matte_black",
        preferred_color_temp_k=4000,
        use_pendant_lighting=False,
        keywords=["minimal", "clean", "white", "simple", "sparse", "modern", "pared-back"],
    ),

    DesignStyle.TRANSITIONAL: StyleProfile(
        style=DesignStyle.TRANSITIONAL,
        description="Bridge between traditional warmth and modern simplicity.",
        palette=_palette("#C4B5A3", "#EDE6DC", "#4A3E35", "#F5F0E8", "greige and warm wood"),
        primary_materials=[MaterialType.WOOD, MaterialType.LINEN, MaterialType.STONE],
        secondary_materials=[MaterialType.LEATHER, MaterialType.CERAMIC],
        wall_color_hex="#EDE8E1",
        trim_color_hex="#FFFFFF",
        floor_finish="medium_oak",
        metal_finish="brushed_nickel",
        preferred_color_temp_k=2700,
        keywords=["transitional", "classic", "timeless", "warm", "balanced", "neutral"],
    ),

    DesignStyle.MID_CENTURY_MODERN: StyleProfile(
        style=DesignStyle.MID_CENTURY_MODERN,
        description="1950s–60s optimism: tapered legs, bold accents, teak wood.",
        palette=_palette("#D4603A", "#F5C87A", "#1F3A4A", "#F2EDE5", "terracotta, mustard, teal"),
        primary_materials=[MaterialType.WOOD, MaterialType.LEATHER, MaterialType.LINEN],
        secondary_materials=[MaterialType.BRUSHED_METAL, MaterialType.CERAMIC],
        wall_color_hex="#F0EAE0",
        trim_color_hex="#FFFFFF",
        floor_finish="teak_parquet",
        metal_finish="brushed_gold",
        preferred_color_temp_k=2700,
        keywords=["mid-century", "mcm", "retro", "teak", "tapered", "organic", "vintage"],
    ),
}
