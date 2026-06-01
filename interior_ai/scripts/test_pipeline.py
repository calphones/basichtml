#!/usr/bin/env python3
"""Smoke test: run the full pipeline with synthetic data (no real floor plan needed).

Usage:
    python interior_ai/scripts/test_pipeline.py
"""

from __future__ import annotations
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_types():
    from interior_ai.types import (
        Vec2, Vec3, WallSegment, Room, RoomType, SceneGraph,
        DesignStyle, FurnitureItem, FurnitureCategory, Color, Palette
    )
    c = Color.from_hex("#C9B99A")
    assert c.to_hex() == "#c9b99a"
    v = Vec2(1.0, 2.0)
    assert abs(v.distance_to(Vec2(4.0, 6.0)) - 5.0) < 0.001
    print("  [✓] types")


def test_style_profiles():
    from interior_ai.design_engine.style_profiles import STYLE_PROFILES
    from interior_ai.types import DesignStyle
    assert DesignStyle.MODERN_ORGANIC in STYLE_PROFILES
    profile = STYLE_PROFILES[DesignStyle.JAPANDI]
    assert profile.prefer_low_profile is True
    print("  [✓] style_profiles")


def test_material_library():
    from interior_ai.materials.material_library import MaterialLibrary
    lib = MaterialLibrary()
    mat = lib.get("light_oak")
    assert mat is not None
    assert mat.roughness < 1.0
    floors = lib.floor_materials()
    assert len(floors) > 0
    print("  [✓] material_library")


def test_furniture_db():
    from interior_ai.furniture.furniture_db import FurnitureDatabase
    from interior_ai.types import FurnitureCategory
    db = FurnitureDatabase()
    assets = db.by_category(FurnitureCategory.SEATING)
    assert len(assets) > 0
    results = db.search("curved")
    assert len(results) > 0
    print("  [✓] furniture_db")


def test_intent_classifier():
    from interior_ai.nlp_editor.intent_classifier import IntentClassifier, IntentType
    clf = IntentClassifier()
    intent = clf.classify("Move sofa closer to the fireplace")
    assert intent.type == IntentType.MOVE_FURNITURE
    intent = clf.classify("Make the room brighter")
    assert intent.type in (IntentType.CHANGE_BRIGHTNESS, IntentType.CHANGE_LIGHTING)
    intent = clf.classify("Use japandi style")
    assert intent.type == IntentType.CHANGE_STYLE
    print("  [✓] intent_classifier")


def test_color_harmonizer():
    from interior_ai.materials.color_harmonizer import ColorHarmonizer
    from interior_ai.types import Color
    harmonizer = ColorHarmonizer()
    seed = Color.from_hex("#C9B99A")
    palette = harmonizer.analogous(seed)
    assert palette.primary == seed
    assert 0 <= palette.accent.r <= 1
    print("  [✓] color_harmonizer")


def test_procedural_gen():
    from interior_ai.furniture.procedural_gen import ProceduralFurnitureGen
    from interior_ai.types import FurnitureCategory, Vec3
    gen = ProceduralFurnitureGen()
    geo = gen.generate(FurnitureCategory.SEATING, Vec3(2.2, 0.9, 0.85))
    assert len(geo.meshes) > 0
    assert geo.meshes[0].vertices.shape[1] == 3
    print("  [✓] procedural_gen")


def test_synthetic_scene():
    from interior_ai.types import (
        Vec2, Vec3, WallSegment, Room, RoomType, FloorPlanData,
        DesignSpec, DesignStyle
    )
    from interior_ai.reconstruction.room_reconstructor import RoomReconstructor
    from interior_ai.design_engine.furniture_placer import FurniturePlacer
    from interior_ai.design_engine.layout_optimizer import LayoutOptimizer

    # Build a simple square living room
    walls = [
        WallSegment(Vec2(0, 0), Vec2(6, 0), id="w1"),
        WallSegment(Vec2(6, 0), Vec2(6, 5), id="w2"),
        WallSegment(Vec2(6, 5), Vec2(0, 5), id="w3"),
        WallSegment(Vec2(0, 5), Vec2(0, 0), id="w4"),
    ]
    room = Room(
        id="living_001",
        type=RoomType.LIVING_ROOM,
        polygon=[Vec2(0, 0), Vec2(6, 0), Vec2(6, 5), Vec2(0, 5)],
    )
    room.compute_area()
    assert abs(room.area - 30.0) < 0.1

    plan = FloorPlanData(rooms=[room], walls=walls)
    spec = DesignSpec(style=DesignStyle.MODERN_ORGANIC, family_friendly=True)

    reconstructor = RoomReconstructor()
    scene = reconstructor.reconstruct(plan, spec=spec)
    assert scene.floor_plan is not None
    assert len(scene.lights) > 0

    placer = FurniturePlacer(spec)
    scene = placer.place_for_scene(scene)
    assert len(scene.furniture) > 0

    optimizer = LayoutOptimizer()
    scene = optimizer.optimize(scene)
    print(f"  [✓] synthetic_scene — {len(scene.furniture)} furniture items placed")


def test_nlp_mutator():
    from interior_ai.types import (
        Vec2, Vec3, WallSegment, Room, RoomType, FloorPlanData,
        DesignSpec, DesignStyle, SceneGraph
    )
    from interior_ai.nlp_editor.scene_mutator import NLPSceneMutator

    plan = FloorPlanData(
        rooms=[Room(id="r1", type=RoomType.LIVING_ROOM,
                    polygon=[Vec2(0,0), Vec2(6,0), Vec2(6,5), Vec2(0,5)])],
        walls=[],
    )
    scene = SceneGraph(floor_plan=plan, style=DesignStyle.MODERN_ORGANIC)

    mutator = NLPSceneMutator()
    scene = mutator.apply("Make the room brighter", scene)
    scene = mutator.apply("Add more storage", scene)
    assert any(f.category.value == "storage" for f in scene.furniture)
    print(f"  [✓] nlp_mutator — {len(scene.furniture)} furniture after mutations")


TESTS = [
    test_types,
    test_style_profiles,
    test_material_library,
    test_furniture_db,
    test_intent_classifier,
    test_color_harmonizer,
    test_procedural_gen,
    test_synthetic_scene,
    test_nlp_mutator,
]


def main():
    print("Interior AI Designer — Pipeline Smoke Tests")
    print("=" * 50)
    passed = 0
    failed = 0
    for test in TESTS:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [✗] {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
