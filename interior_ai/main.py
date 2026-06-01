"""Interior AI Designer — command-line entry points.

Usage:
    # Start the API server
    python -m interior_ai.main server

    # Run the full pipeline on a single floor plan (CLI mode)
    python -m interior_ai.main design --floor-plan path/to/plan.pdf --style modern_organic

    # Batch render all rooms from an IFC file
    python -m interior_ai.main batch --ifc path/to/building.ifc --output ./renders
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path


def run_server(args):
    import uvicorn
    from .api.main import create_app
    import yaml

    config = {}
    if Path("interior_ai/config.yaml").exists():
        with open("interior_ai/config.yaml") as f:
            cfg = yaml.safe_load(f)
        api_cfg = cfg.get("api", {})
        config = {
            "cors_origins": api_cfg.get("cors_origins", []),
            "session_timeout_minutes": api_cfg.get("session_timeout_minutes", 60),
        }

    app = create_app(config)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


def run_design(args):
    """CLI: generate a design from a floor plan and render it."""
    from pathlib import Path
    from .types import DesignSpec, DesignStyle, RenderMode, RenderRequest
    from .input_parser.pdf_parser import PDFParser
    from .input_parser.image_parser import ImageParser
    from .floorplan.detector import FloorPlanDetector
    from .floorplan.vectorizer import Vectorizer
    from .floorplan.scale_inferrer import ScaleInferrer
    from .reconstruction.room_reconstructor import RoomReconstructor
    from .design_engine.furniture_placer import FurniturePlacer
    from .design_engine.layout_optimizer import LayoutOptimizer
    from .blender_integration.scene_builder import BlenderSceneBuilder
    from .blender_integration.material_applier import BlenderMaterialApplier
    from .blender_integration.render_manager import RenderManager
    from .lighting.light_placer import LightPlacer

    fp_path = Path(args.floor_plan)
    print(f"[1/6] Parsing floor plan: {fp_path}")
    floor_plan = _parse_floor_plan(fp_path)
    print(f"      Rooms: {len(floor_plan.rooms)}, Walls: {len(floor_plan.walls)}")

    spec = DesignSpec(
        style=DesignStyle(args.style),
        natural_language_prompt=args.prompt or "",
        family_friendly=not args.no_family,
    )
    if args.inspiration:
        spec.inspiration_image_paths = [args.inspiration]

    print(f"[2/6] Reconstructing 3D scene ({spec.style.value} style)")
    reconstructor = RoomReconstructor()
    scene = reconstructor.reconstruct(floor_plan, spec=spec)

    print("[3/6] Placing furniture")
    placer = FurniturePlacer(spec)
    scene = placer.place_for_scene(scene)
    print(f"      Placed {len(scene.furniture)} furniture items")

    print("[4/6] Optimising layout")
    scene = LayoutOptimizer().optimize(scene)

    print("[5/6] Applying materials and lighting")
    scene = BlenderSceneBuilder().prepare(scene, spec)
    scene = BlenderMaterialApplier().apply(scene)

    print(f"[6/6] Rendering ({args.render_mode})")
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "render_01.png")

    render_mgr = RenderManager(output_root=args.output)
    job_id = render_mgr.submit(
        scene, RenderMode(args.render_mode), output_path=output_path
    )
    job = render_mgr.run_sync(job_id)

    if job.status.value == "complete":
        print(f"\n✓ Render complete: {job.output_path}")
    else:
        print(f"\n✗ Render failed: {job.error}")
        sys.exit(1)


def _parse_floor_plan(path: Path):
    ext = path.suffix.lower()
    if ext == ".pdf":
        from .input_parser.pdf_parser import PDFParser
        from .floorplan.detector import FloorPlanDetector
        from .floorplan.vectorizer import Vectorizer
        from .floorplan.scale_inferrer import ScaleInferrer
        pdf = PDFParser()
        pages = pdf.extract_floor_plans(path) or pdf.extract_pages(path)
        if not pages:
            from .types import FloorPlanData
            return FloorPlanData(source_image_path=str(path))
        image = pages[0]
        scale = ScaleInferrer().infer(image, pdf.extract_text(path))
        result = FloorPlanDetector(scale_m_per_px=scale).detect(image)
        from .types import FloorPlanData
        plan = FloorPlanData(walls=result.walls, openings=result.openings,
                              stairs=result.stairs, scale_m_per_px=scale)
        return Vectorizer().vectorize(plan)
    elif ext == ".dxf":
        from .input_parser.dxf_parser import DXFParser
        return DXFParser().parse(path)
    elif ext == ".ifc":
        from .input_parser.ifc_parser import IFCParser
        return IFCParser().parse(path)
    else:
        from .input_parser.image_parser import ImageParser
        from .floorplan.detector import FloorPlanDetector
        from .floorplan.vectorizer import Vectorizer
        from .floorplan.scale_inferrer import ScaleInferrer
        img = ImageParser().load(path)
        scale = ScaleInferrer().infer(img)
        result = FloorPlanDetector(scale_m_per_px=scale).detect(img)
        from .types import FloorPlanData
        plan = FloorPlanData(walls=result.walls, openings=result.openings,
                              stairs=result.stairs, scale_m_per_px=scale)
        return Vectorizer().vectorize(plan)


def main():
    parser = argparse.ArgumentParser(description="Interior AI Designer")
    sub = parser.add_subparsers(dest="command")

    # server
    srv = sub.add_parser("server", help="Start API server")
    srv.add_argument("--host", default="0.0.0.0")
    srv.add_argument("--port", type=int, default=8000)
    srv.add_argument("--reload", action="store_true")

    # design
    des = sub.add_parser("design", help="Generate design from floor plan")
    des.add_argument("--floor-plan", required=True)
    des.add_argument("--style", default="modern_organic",
                      choices=[s.value for s in __import__("interior_ai.types", fromlist=["DesignStyle"]).DesignStyle])
    des.add_argument("--prompt", default="")
    des.add_argument("--inspiration", default=None)
    des.add_argument("--output", default="./output")
    des.add_argument("--render-mode", default="preview",
                      choices=["preview", "photoreal", "topdown"])
    des.add_argument("--no-family", action="store_true")

    args = parser.parse_args()
    if args.command == "server":
        run_server(args)
    elif args.command == "design":
        run_design(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
