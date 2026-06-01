"""Convert builder PDF floor plans into high-resolution raster images."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import numpy as np

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class PDFParser:
    """Extract clean architectural drawings from PDF documents.

    Builder PDFs often contain multiple pages (site plan, floor plan per storey,
    electrical, mechanical). This parser identifies floor-plan pages by content
    heuristics (room labels, dimension annotations) and exports them at a
    configurable DPI suitable for CV processing.
    """

    DEFAULT_DPI = 300
    MIN_PAGE_AREA_PX = 100_000   # discard thumbnail pages

    def __init__(self, dpi: int = DEFAULT_DPI):
        if not HAS_FITZ:
            raise ImportError("pymupdf is required: pip install pymupdf")
        self.dpi = dpi

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_pages(self, pdf_path: str | Path) -> list[np.ndarray]:
        """Return all pages as RGB uint8 numpy arrays."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            if arr.shape[0] * arr.shape[1] >= self.MIN_PAGE_AREA_PX:
                pages.append(arr.copy())
        doc.close()
        return pages

    def extract_floor_plans(self, pdf_path: str | Path) -> list[np.ndarray]:
        """Return only pages that look like floor plans."""
        all_pages = self.extract_pages(pdf_path)
        return [p for p in all_pages if self._is_floor_plan(p)]

    def extract_text(self, pdf_path: str | Path) -> list[str]:
        """Extract embedded text per page (for dimension scraping)."""
        pdf_path = Path(pdf_path)
        doc = fitz.open(str(pdf_path))
        texts = [page.get_text() for page in doc]
        doc.close()
        return texts

    def save_pages(self, pdf_path: str | Path, output_dir: str | Path) -> list[Path]:
        """Save extracted pages as PNG files and return their paths."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        pages = self.extract_pages(pdf_path)
        saved = []
        for i, page_arr in enumerate(pages):
            if HAS_PIL:
                img = Image.fromarray(page_arr)
                out = output_dir / f"page_{i:03d}.png"
                img.save(str(out))
                saved.append(out)
        return saved

    # ------------------------------------------------------------------
    # Heuristics
    # ------------------------------------------------------------------

    def _is_floor_plan(self, page: np.ndarray) -> bool:
        """Rough heuristic: floor plans have many thin lines and few photos."""
        import cv2  # type: ignore
        gray = cv2.cvtColor(page, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = edges.mean() / 255.0
        # floor plans: moderate edge density, mostly monochrome
        color_variance = page.std(axis=2).mean()
        return edge_density > 0.02 and color_variance < 40.0
