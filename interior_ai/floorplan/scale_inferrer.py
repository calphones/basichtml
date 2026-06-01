"""Infer real-world scale from dimension annotations in floor plan images."""

from __future__ import annotations
import re
from typing import Optional
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# Regex patterns for common dimension formats in builder plans
DIM_PATTERNS = [
    # Feet-inches: 12'-6" or 12'6"
    re.compile(r"""(\d+)'\s*[-–]?\s*(\d+)["″]"""),
    # Feet only: 12'
    re.compile(r"""(\d+)'"""),
    # Decimal feet: 12.5 ft
    re.compile(r"""(\d+\.?\d*)\s*ft""", re.IGNORECASE),
    # Metres: 3.8m or 3.8 m
    re.compile(r"""(\d+\.?\d*)\s*m(?!\w)""", re.IGNORECASE),
    # Millimetres: 3800mm
    re.compile(r"""(\d{3,5})\s*mm""", re.IGNORECASE),
]


class ScaleInferrer:
    """Compute metres-per-pixel scale from OCR annotations or known standards.

    Strategy:
    1. Run OCR on the full image to extract dimension strings.
    2. Find dimension arrows (thin lines with endpoints) in the image.
    3. Match parsed dimension values with arrow pixel lengths.
    4. Derive m/px ratio; take median across all matched pairs.

    Falls back to US residential standard (1/4" = 1' → 1px ≈ 0.01 m at 96 DPI).
    """

    ARROW_LINE_THICKNESS_RANGE = (1, 3)
    MIN_ARROW_LEN_PX = 40
    FALLBACK_M_PER_PX = 0.01  # approx 1/4" = 1' at 96 DPI

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def infer(self, image: np.ndarray, ocr_texts: list[str] | None = None) -> float:
        """Return metres-per-pixel ratio for the given image.

        Args:
            image: RGB or grayscale uint8 array
            ocr_texts: pre-extracted OCR strings (optional; runs OCR if None)

        Returns:
            m/px ratio (positive float)
        """
        if ocr_texts is None:
            ocr_texts = self._run_ocr(image)

        dimension_metres = self._parse_dimensions(ocr_texts)
        if not dimension_metres:
            return self.FALLBACK_M_PER_PX

        arrow_lengths_px = self._detect_dimension_arrows(image)
        if not arrow_lengths_px:
            return self.FALLBACK_M_PER_PX

        ratios = []
        dim_sorted = sorted(dimension_metres)
        arr_sorted = sorted(arrow_lengths_px)
        pairs = min(len(dim_sorted), len(arr_sorted))
        for i in range(pairs):
            if arr_sorted[i] > 0:
                ratios.append(dim_sorted[i] / arr_sorted[i])

        if not ratios:
            return self.FALLBACK_M_PER_PX

        return float(np.median(ratios))

    def parse_dimensions_from_text(self, text: str) -> list[float]:
        """Parse a block of text and return all found dimensions in metres."""
        return self._parse_dimensions([text])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run_ocr(self, image: np.ndarray) -> list[str]:
        if not HAS_OCR:
            return []
        if not HAS_CV2:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        text = pytesseract.image_to_string(gray, config="--psm 6")
        return [text]

    def _parse_dimensions(self, texts: list[str]) -> list[float]:
        dims: list[float] = []
        for text in texts:
            for pattern in DIM_PATTERNS:
                for match in pattern.finditer(text):
                    groups = match.groups()
                    try:
                        value_m = self._convert_to_metres(pattern, groups)
                        if 0.1 < value_m < 100:   # sanity bounds for residential
                            dims.append(value_m)
                    except (ValueError, IndexError):
                        continue
        return sorted(set(dims))

    def _convert_to_metres(self, pattern: re.Pattern, groups: tuple) -> float:
        pattern_str = pattern.pattern
        if "ft" in pattern_str.lower():
            return float(groups[0]) * 0.3048
        if "mm" in pattern_str.lower():
            return float(groups[0]) / 1000.0
        if r"""["″]""" in pattern_str or ("'" in pattern_str and len(groups) == 2):
            # feet-inches
            feet = float(groups[0])
            inches = float(groups[1]) if len(groups) > 1 else 0
            return (feet * 12 + inches) * 0.0254
        if "'" in pattern_str:
            return float(groups[0]) * 0.3048
        if r"""m(?!\w)""" in pattern_str or "m" in pattern_str:
            return float(groups[0])
        return float(groups[0]) * 0.3048   # default to feet

    def _detect_dimension_arrows(self, image: np.ndarray) -> list[float]:
        if not HAS_CV2:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 30, 100)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=20,
            minLineLength=self.MIN_ARROW_LEN_PX, maxLineGap=3,
        )
        if lines is None:
            return []
        lengths = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = float(np.hypot(x2 - x1, y2 - y1))
            if length > self.MIN_ARROW_LEN_PX:
                lengths.append(length)
        return sorted(lengths)
