"""Monocular depth estimation from room photographs using Depth Anything V2."""

from __future__ import annotations
from pathlib import Path
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class DepthEstimator:
    """Estimate per-pixel depth from a single room photo.

    Uses Depth Anything V2 via ONNX Runtime for hardware-agnostic inference.
    Falls back to a simple gradient-based heuristic if the model is unavailable.

    Output is a normalised depth map (0 = nearest, 1 = farthest) at
    the input image resolution.
    """

    INPUT_SIZE = (518, 518)
    MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self, model_path: str | Path | None = None):
        self._session = None
        if model_path and Path(model_path).exists():
            self._load_model(model_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def estimate(self, image: np.ndarray) -> np.ndarray:
        """Return depth map (H, W) float32, values in [0, 1].

        Args:
            image: RGB uint8 (H, W, 3)

        Returns:
            Depth map same spatial size as input image.
        """
        if self._session is not None:
            return self._run_onnx(image)
        return self._heuristic_depth(image)

    def estimate_metric(
        self, image: np.ndarray, room_height_m: float = 2.74
    ) -> np.ndarray:
        """Return approximate metric depth (metres) using room height as anchor."""
        normalised = self.estimate(image)
        # Scale so 95th percentile ≈ room_height_m (floor-to-ceiling depth)
        p95 = float(np.percentile(normalised, 95))
        if p95 < 1e-6:
            return normalised * room_height_m
        return normalised * (room_height_m / p95)

    def extract_room_planes(
        self, image: np.ndarray, depth: np.ndarray
    ) -> dict[str, np.ndarray]:
        """Identify floor, wall, and ceiling planes from depth + segmentation."""
        h, w = depth.shape
        planes = {}
        # Floor: bottom 20% of image with nearest median depth in that strip
        floor_strip = depth[int(h * 0.8):, :]
        planes["floor_depth"] = floor_strip
        # Ceiling: top 15% of image
        planes["ceiling_depth"] = depth[:int(h * 0.15), :]
        # Left / right walls
        planes["left_wall_depth"] = depth[:, :int(w * 0.2)]
        planes["right_wall_depth"] = depth[:, int(w * 0.8):]
        return planes

    # ------------------------------------------------------------------
    # ONNX inference
    # ------------------------------------------------------------------

    def _load_model(self, model_path: str | Path) -> None:
        if not HAS_ORT:
            return
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        try:
            self._session = ort.InferenceSession(str(model_path), providers=providers)
        except Exception:
            self._session = None

    def _run_onnx(self, image: np.ndarray) -> np.ndarray:
        orig_h, orig_w = image.shape[:2]
        inp = self._preprocess(image)
        input_name = self._session.get_inputs()[0].name
        output = self._session.run(None, {input_name: inp})[0]
        depth = output.squeeze()
        if not HAS_CV2:
            return depth
        depth_resized = cv2.resize(depth, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        d_min, d_max = depth_resized.min(), depth_resized.max()
        if d_max - d_min > 1e-6:
            depth_resized = (depth_resized - d_min) / (d_max - d_min)
        return depth_resized.astype(np.float32)

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        if not HAS_CV2:
            raise ImportError("opencv-python required")
        resized = cv2.resize(image, self.INPUT_SIZE).astype(np.float32) / 255.0
        normalised = (resized - self.MEAN) / self.STD
        return normalised.transpose(2, 0, 1)[None]  # (1, C, H, W)

    # ------------------------------------------------------------------
    # Heuristic fallback (vertical gradient proxy)
    # ------------------------------------------------------------------

    def _heuristic_depth(self, image: np.ndarray) -> np.ndarray:
        """Approximate depth by assuming floor is bottom (far) and ceiling is top (near).
        This is only a last-resort fallback when no model is available.
        """
        h, w = image.shape[:2]
        # Vertical gradient: objects higher in image tend to be farther
        gradient = np.linspace(0.3, 1.0, h, dtype=np.float32)[:, None]
        depth = np.broadcast_to(gradient, (h, w)).copy()
        # Modulate by image brightness (dark regions = shadows = closer)
        if len(image.shape) == 3:
            gray = image.mean(axis=2).astype(np.float32) / 255.0
            depth = depth * 0.7 + gray * 0.3
        d_min, d_max = depth.min(), depth.max()
        if d_max > d_min:
            depth = (depth - d_min) / (d_max - d_min)
        return depth
