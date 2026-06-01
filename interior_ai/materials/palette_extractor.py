"""Extract and harmonise colour palettes from inspiration images."""

from __future__ import annotations
from pathlib import Path
import numpy as np

from ..types import Color, Palette
from ..input_parser.inspiration_parser import InspirationParser


class PaletteExtractor:
    """Extract a design palette from one or more inspiration images.

    When multiple images are provided, palettes are blended by averaging
    dominant colour clusters across all images.
    """

    def __init__(self):
        self._insp = InspirationParser()

    def from_image(self, image_path: str | Path) -> Palette:
        return self._insp.extract_palette(image_path)

    def from_images(self, image_paths: list[str | Path]) -> Palette:
        if not image_paths:
            return self._default_palette()
        palettes = [self.from_image(p) for p in image_paths]
        return self._blend_palettes(palettes)

    def from_hex_list(self, hex_colors: list[str]) -> Palette:
        colors = [Color.from_hex(h) for h in hex_colors]
        sorted_by_brightness = sorted(
            colors, key=lambda c: 0.299 * c.r + 0.587 * c.g + 0.114 * c.b
        )
        n = len(sorted_by_brightness)
        return Palette(
            primary=sorted_by_brightness[n // 2] if n else Color(0.8, 0.75, 0.7),
            secondary=sorted_by_brightness[0] if n else Color(0.95, 0.92, 0.88),
            accent=self._most_saturated(colors),
            neutral=sorted_by_brightness[-1] if n else Color(0.98, 0.97, 0.95),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _blend_palettes(self, palettes: list[Palette]) -> Palette:
        def avg_color(colors: list[Color]) -> Color:
            if not colors:
                return Color(0.8, 0.75, 0.7)
            return Color(
                r=float(np.mean([c.r for c in colors])),
                g=float(np.mean([c.g for c in colors])),
                b=float(np.mean([c.b for c in colors])),
            )
        return Palette(
            primary=avg_color([p.primary for p in palettes]),
            secondary=avg_color([p.secondary for p in palettes]),
            accent=avg_color([p.accent for p in palettes]),
            neutral=avg_color([p.neutral for p in palettes]),
        )

    def _most_saturated(self, colors: list[Color]) -> Color:
        def sat(c: Color) -> float:
            mx, mn = max(c.r, c.g, c.b), min(c.r, c.g, c.b)
            return (mx - mn) / (mx + 1e-6)
        return max(colors, key=sat) if colors else Color(0.7, 0.6, 0.4)

    def _default_palette(self) -> Palette:
        return Palette(
            primary=Color.from_hex("#C9B99A"),
            secondary=Color.from_hex("#E8DFD0"),
            accent=Color.from_hex("#3D2B1F"),
            neutral=Color.from_hex("#F5F0EB"),
            description="Default warm organic palette",
        )
