"""Generate harmonious colour schemes from seed colours using colour theory."""

from __future__ import annotations
import math
import numpy as np

from ..types import Color, Palette


class ColorHarmonizer:
    """Generate complementary, analogous, triadic, and split-complementary palettes.

    Operates in HSL colour space for perceptually intuitive relationships.
    Designed for residential interior use:
    - Keeps chroma modest (no jarring saturated hues)
    - Biases toward warm temperatures (2700–3000 K)
    - Provides both 'calm' and 'accent' variants
    """

    MAX_CHROMA = 0.45    # cap saturation for residential tasteful restraint
    MIN_LIGHTNESS = 0.25
    MAX_LIGHTNESS = 0.88

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analogous(self, seed: Color, spread_deg: float = 30.0) -> Palette:
        """Two colours within `spread_deg` of seed, neutral, and accent."""
        h, s, l = self._to_hsl(seed)
        c1 = self._from_hsl(h - spread_deg / 360, s * 0.8, min(l + 0.12, self.MAX_LIGHTNESS))
        c2 = self._from_hsl(h + spread_deg / 360, s * 0.8, max(l - 0.10, self.MIN_LIGHTNESS))
        neutral = self._from_hsl(h, min(s * 0.3, 0.1), 0.92)
        accent = self._from_hsl(h + 0.5, min(s * 1.2, self.MAX_CHROMA), l)
        return Palette(primary=seed, secondary=c1, accent=accent, neutral=neutral,
                        description="analogous")

    def complementary(self, seed: Color) -> Palette:
        h, s, l = self._to_hsl(seed)
        comp = self._from_hsl((h + 0.5) % 1.0, min(s, self.MAX_CHROMA), l)
        neutral = self._from_hsl(h, 0.05, 0.93)
        secondary = self._from_hsl(h, min(s * 0.5, 0.2), min(l + 0.15, self.MAX_LIGHTNESS))
        return Palette(primary=seed, secondary=secondary, accent=comp, neutral=neutral,
                        description="complementary")

    def triadic(self, seed: Color) -> Palette:
        h, s, l = self._to_hsl(seed)
        c1 = self._from_hsl((h + 1/3) % 1.0, min(s * 0.7, self.MAX_CHROMA), l)
        c2 = self._from_hsl((h + 2/3) % 1.0, min(s * 0.7, self.MAX_CHROMA), l)
        neutral = self._from_hsl(h, 0.05, 0.92)
        return Palette(primary=seed, secondary=c1, accent=c2, neutral=neutral,
                        description="triadic")

    def warm_neutral_scheme(self, warmth: float = 0.5) -> Palette:
        """Generate a warm neutral scheme for living spaces (no seed required).

        Args:
            warmth: 0 = cooler greys, 1 = warmer tans/sands
        """
        base_hue = 0.08 + warmth * 0.04    # 28°–43° (warm yellow-orange range)
        return Palette(
            primary=self._from_hsl(base_hue, 0.18, 0.72),
            secondary=self._from_hsl(base_hue, 0.10, 0.86),
            accent=self._from_hsl(0.05, 0.35, 0.38),
            neutral=self._from_hsl(base_hue, 0.05, 0.95),
            description=f"warm_neutral (warmth={warmth:.2f})",
        )

    # ------------------------------------------------------------------
    # Colour conversion helpers
    # ------------------------------------------------------------------

    def _to_hsl(self, color: Color) -> tuple[float, float, float]:
        r, g, b = color.r, color.g, color.b
        mx, mn = max(r, g, b), min(r, g, b)
        l = (mx + mn) / 2
        if mx == mn:
            return 0.0, 0.0, l
        d = mx - mn
        s = d / (2 * l) if l < 0.5 else d / (2 - 2 * l)
        if mx == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        return h / 6, s, l

    def _from_hsl(self, h: float, s: float, l: float) -> Color:
        h = h % 1.0
        s = max(0.0, min(1.0, s))
        l = max(self.MIN_LIGHTNESS, min(self.MAX_LIGHTNESS, l))
        if s == 0:
            return Color(l, l, l)
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q

        def hue_to_rgb(t: float) -> float:
            t = t % 1.0
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 0.5: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p

        return Color(
            r=hue_to_rgb(h + 1/3),
            g=hue_to_rgb(h),
            b=hue_to_rgb(h - 1/3),
        )
