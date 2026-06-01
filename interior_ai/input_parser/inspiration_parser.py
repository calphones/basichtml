"""Extract design cues from inspiration images and room photographs."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from ..types import Color, Palette, DesignStyle, MaterialType


class InspirationParser:
    """Analyse inspiration images to extract palette, materials, and style cues.

    Uses k-means clustering on Lab colour space to find dominant colours,
    then maps them onto the design system's palette and material vocabulary.
    """

    N_PALETTE_COLORS = 6
    SAMPLE_SIZE = (256, 256)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_palette(self, image_path: str | Path) -> Palette:
        """Return a 4-colour Palette from dominant hues in the image."""
        image = self._load_resized(image_path)
        colors = self._dominant_colors(image, self.N_PALETTE_COLORS)
        sorted_colors = sorted(colors, key=lambda c: c.r * 0.299 + c.g * 0.587 + c.b * 0.114)
        # Map extracted colors to semantic roles
        primary = sorted_colors[len(sorted_colors) // 2]
        secondary = sorted_colors[0] if len(sorted_colors) > 1 else primary
        neutral = sorted_colors[-1]
        accent = self._most_saturated(colors)
        return Palette(
            primary=primary,
            secondary=secondary,
            accent=accent,
            neutral=neutral,
            description="Extracted from inspiration image",
        )

    def infer_style(self, image_path: str | Path) -> DesignStyle:
        """Return a best-guess DesignStyle from image colour and saturation profile."""
        image = self._load_resized(image_path)
        arr = np.array(image).astype(float) / 255.0
        # Convert to HSV for saturation analysis
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        max_c = np.maximum.reduce([r, g, b])
        min_c = np.minimum.reduce([r, g, b])
        saturation = (max_c - min_c) / (max_c + 1e-6)
        mean_sat = float(saturation.mean())
        mean_val = float(max_c.mean())
        warmth = float((r - b).mean())

        if mean_sat < 0.12 and mean_val > 0.7:
            return DesignStyle.JAPANDI
        if mean_sat < 0.2 and mean_val > 0.6:
            return DesignStyle.SCANDINAVIAN
        if mean_sat < 0.2:
            return DesignStyle.MINIMALIST
        if warmth > 0.05 and mean_sat > 0.15:
            return DesignStyle.MODERN_ORGANIC
        if mean_val < 0.45:
            return DesignStyle.CONTEMPORARY_LUXURY
        return DesignStyle.TRANSITIONAL

    def detect_materials(self, image_path: str | Path) -> list[MaterialType]:
        """Return likely material types from texture analysis (heuristic)."""
        image = self._load_resized(image_path)
        arr = np.array(image).astype(float)
        gray = arr.mean(axis=2)
        # Local variance → texture complexity
        from scipy.ndimage import uniform_filter  # type: ignore
        mean = uniform_filter(gray, size=5)
        variance = uniform_filter(gray ** 2, size=5) - mean ** 2
        mean_var = float(variance.mean())
        mean_brightness = float(gray.mean())

        materials = []
        if mean_var > 200:
            materials.append(MaterialType.WOOD)
        if mean_var > 400:
            materials.append(MaterialType.STONE)
        if mean_brightness > 200:
            materials.append(MaterialType.MARBLE)
        if mean_var < 50 and mean_brightness > 180:
            materials.append(MaterialType.MATTE_PAINT)
        if not materials:
            materials.append(MaterialType.LINEN)
        return materials

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_resized(self, path: str | Path) -> "Image.Image":
        if not HAS_PIL:
            raise ImportError("Pillow is required: pip install Pillow")
        img = Image.open(str(path)).convert("RGB")
        img = img.resize(self.SAMPLE_SIZE, Image.LANCZOS)
        return img

    def _dominant_colors(self, image: "Image.Image", n: int) -> list[Color]:
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn is required: pip install scikit-learn")
        arr = np.array(image).reshape(-1, 3).astype(float) / 255.0
        km = KMeans(n_clusters=n, n_init="auto", random_state=42)
        km.fit(arr)
        centers = km.cluster_centers_
        return [Color(r=float(c[0]), g=float(c[1]), b=float(c[2])) for c in centers]

    def _most_saturated(self, colors: list[Color]) -> Color:
        def saturation(c: Color) -> float:
            mx = max(c.r, c.g, c.b)
            mn = min(c.r, c.g, c.b)
            return (mx - mn) / (mx + 1e-6)
        return max(colors, key=saturation)
