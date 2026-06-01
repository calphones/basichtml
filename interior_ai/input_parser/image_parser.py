"""Parse raster builder plan images and room photographs."""

from __future__ import annotations
from pathlib import Path
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ImageParser:
    """Load, normalise, and pre-process input images for the CV pipeline.

    Handles:
    - JPEG/PNG/TIFF/WEBP floor plan scans
    - Deskewing scanned documents
    - Contrast normalisation for faded builder prints
    - Scale bar detection
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp", ".bmp"}

    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: str | Path) -> np.ndarray:
        """Load image as RGB uint8 numpy array."""
        path = Path(path)
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported format: {path.suffix}")
        if not HAS_CV2:
            raise ImportError("opencv-python is required")
        bgr = cv2.imread(str(path))
        if bgr is None:
            raise IOError(f"Failed to read image: {path}")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def preprocess_floor_plan(self, image: np.ndarray) -> np.ndarray:
        """Clean up scanned floor plan for CV: deskew, binarise, denoise."""
        if not HAS_CV2:
            raise ImportError("opencv-python is required")
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        gray = self._deskew(gray)
        gray = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=11, C=4
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        return gray

    def preprocess_room_photo(self, image: np.ndarray) -> np.ndarray:
        """Normalise room photo for depth estimation and segmentation."""
        if not HAS_CV2:
            raise ImportError("opencv-python is required")
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        result = cv2.merge([l, a, b])
        return cv2.cvtColor(result, cv2.COLOR_LAB2RGB)

    def detect_scale_bar(self, image: np.ndarray) -> float | None:
        """Attempt to find a scale bar in the image and return m/px ratio.

        Returns None if no reliable scale bar is found.
        """
        if not HAS_CV2:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        # Look for horizontal lines in bottom strip (where scale bars usually live)
        h, w = gray.shape
        strip = gray[int(h * 0.85):, :]
        edges = cv2.Canny(strip, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                                 minLineLength=50, maxLineGap=5)
        if lines is None:
            return None
        # Longest horizontal line segment is likely the scale bar
        best_len = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 5:   # roughly horizontal
                length = abs(x2 - x1)
                if length > best_len:
                    best_len = length
        if best_len < 30:
            return None
        # Assume 1 m scale bar if detected; caller should cross-check with OCR
        return 1.0 / best_len

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Rotate image to align principal lines with axes."""
        if not HAS_CV2:
            return gray
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        if lines is None:
            return gray
        angles = []
        for line in lines[:20]:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            if abs(angle) < 45:
                angles.append(angle)
        if not angles:
            return gray
        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return gray
        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), median_angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h),
                               flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
