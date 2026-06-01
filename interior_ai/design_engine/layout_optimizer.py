"""Iterative layout optimizer: nudge furniture until clearance violations are resolved."""

from __future__ import annotations
import math
import random
from typing import Optional
import numpy as np

from ..types import FurnitureItem, Vec3, SceneGraph
from .clearance_checker import ClearanceChecker, ClearanceViolation


class LayoutOptimizer:
    """Resolve clearance violations through iterative constraint relaxation.

    Algorithm (per iteration):
    1. Run ClearanceChecker on current layout.
    2. For each 'error' violation, apply the suggested offset nudge.
    3. Re-check. Repeat up to MAX_ITERATIONS.
    4. If convergence fails, log remaining violations.

    Also performs a simulated-annealing pass to explore small local
    improvements in furniture flow score (circulation quality).
    """

    MAX_ITERATIONS = 50
    NUDGE_DAMPING = 0.8     # reduce nudge magnitude each iteration
    MIN_NUDGE_M = 0.02      # stop nudging below 2 cm
    ANNEALING_STEPS = 100
    TEMP_INITIAL = 0.5
    TEMP_FINAL = 0.01

    def __init__(self):
        self._checker = ClearanceChecker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(self, scene: SceneGraph, max_iter: int = MAX_ITERATIONS) -> SceneGraph:
        """Resolve violations and return the improved SceneGraph."""
        for iteration in range(max_iter):
            violations = self._checker.check_scene(scene)
            errors = [v for v in violations if v.severity == "error"]
            if not errors:
                break
            nudge_factor = self.NUDGE_DAMPING ** iteration
            for v in errors:
                if max(abs(v.suggested_offset[0]), abs(v.suggested_offset[1])) < self.MIN_NUDGE_M:
                    continue
                item = self._find_item(scene, v.item_id)
                if item:
                    dx, dy = v.suggested_offset
                    item.position = Vec3(
                        item.position.x + dx * nudge_factor,
                        item.position.y + dy * nudge_factor,
                        item.position.z,
                    )
        return scene

    def annealing_pass(self, scene: SceneGraph) -> SceneGraph:
        """Simulated annealing pass to improve overall flow score."""
        import copy
        best_scene = copy.deepcopy(scene)
        best_score = self._score(scene)
        temp = self.TEMP_INITIAL

        for step in range(self.ANNEALING_STEPS):
            if not scene.furniture:
                break
            item = random.choice(scene.furniture)
            orig_pos = Vec3(item.position.x, item.position.y, item.position.z)

            delta = 0.1 * (1 - step / self.ANNEALING_STEPS)
            item.position = Vec3(
                item.position.x + random.uniform(-delta, delta),
                item.position.y + random.uniform(-delta, delta),
                item.position.z,
            )

            new_score = self._score(scene)
            delta_score = new_score - best_score
            if delta_score > 0 or random.random() < math.exp(delta_score / (temp + 1e-9)):
                best_score = new_score
                best_scene = copy.deepcopy(scene)
            else:
                item.position = orig_pos

            temp = self.TEMP_INITIAL * (self.TEMP_FINAL / self.TEMP_INITIAL) ** (step / self.ANNEALING_STEPS)

        return best_scene

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score(self, scene: SceneGraph) -> float:
        violations = self._checker.check_scene(scene)
        error_penalty = sum(10.0 for v in violations if v.severity == "error")
        warn_penalty = sum(1.0 for v in violations if v.severity == "warning")
        spacing_score = self._spacing_score(scene.furniture)
        return spacing_score - error_penalty - warn_penalty

    def _spacing_score(self, furniture: list[FurnitureItem]) -> float:
        if len(furniture) < 2:
            return 0.0
        total = 0.0
        for i, a in enumerate(furniture):
            for b in furniture[i+1:]:
                dist = math.hypot(a.position.x - b.position.x, a.position.y - b.position.y)
                min_gap = (a.scale.x + b.scale.x) / 2 + 0.91
                if dist >= min_gap:
                    total += 1.0
        return total

    def _find_item(self, scene: SceneGraph, item_id: str) -> Optional[FurnitureItem]:
        for item in scene.furniture:
            if item.id == item_id:
                return item
        return None
