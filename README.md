# Interior AI Designer

Open-source, local-first AI interior design platform for real residential homes.

---

## Overview

Turns your builder floor plans, PDFs, and inspiration images into photorealistic
3D interior renders with intelligent furniture placement, style matching, and
natural-language editing — all running locally, no enterprise subscriptions.

**Target use case:** Modern suburban townhomes and single-family homes.

---

## Key Features

| Capability | Details |
|---|---|
| Floor plan parsing | PDF, PNG/JPG, DXF (AutoCAD), IFC (BIM) |
| CV detection | Walls, doors, windows, stairs, room labels, dimensions |
| 3D reconstruction | Extrude 2D geometry → full architectural shell |
| Design styles | 7 styles: Modern Organic, Japandi, Scandinavian, Luxury, Minimalist, Transitional, MCM |
| Furniture placement | Clearance-validated, zone-aware, traffic-flow-conscious |
| Rendering | Blender Cycles (photoreal) + Eevee (fast preview) |
| NLP editing | "Move sofa closer to fireplace", "Use warmer lighting", "Make it more japandi" |
| Material system | 25+ PBR materials, palette extraction from inspiration images |
| Lighting | Physically-based daylight, recessed grid, pendants, indirect, HDRI |
| CC0 assets | All procedural / Poly Haven / CC0 — no copyright concerns |

---

## Architecture

```
interior_ai/
├── types.py                    # Shared data structures
├── config.yaml                 # Runtime configuration
├── requirements.txt
├── main.py                     # CLI entry points
│
├── input_parser/               # PDF, image, DXF, IFC, inspiration parsers
├── floorplan/                  # CV pipeline: detect → vectorise → scale → stairs
├── reconstruction/             # 2D → 3D shell, depth estimation, SceneGraph
├── design_engine/              # Style profiles, furniture placement, optimiser
├── furniture/                  # CC0 asset DB, procedural mesh gen, asset manager
├── materials/                  # PBR library, palette extraction, colour harmoniser
├── lighting/                   # Light placement, HDRI, daylight simulation
├── blender_integration/        # Blender subprocess bridge, render manager
├── nlp_editor/                 # Intent classifier, command parser, scene mutator
├── api/                        # FastAPI backend (REST)
│   └── routes/                 # /upload  /design  /render  /edit
├── frontend/                   # React + Vite UI
│   └── src/components/         # UploadPanel, StyleSelector, RenderViewer, NLPEditor, MaterialBoard
└── scripts/                    # setup_env.sh, download_assets.py, test_pipeline.py
```

---

## Quick Start

### 1. Install prerequisites

- **Python 3.10+**
- **Blender 3.6 LTS or 4.x** — [blender.org/download](https://www.blender.org/download/)
- **Node.js 18+** (for the frontend) — [nodejs.org](https://nodejs.org)
- **Tesseract OCR** (optional, for dimension text parsing)
  ```bash
  # Ubuntu / Debian
  sudo apt install tesseract-ocr
  # macOS
  brew install tesseract
  ```

### 2. Set up the environment

```bash
git clone https://github.com/calphones/basichtml.git
cd basichtml

bash interior_ai/scripts/setup_env.sh
source .venv/bin/activate

# Tell the system where Blender lives
export BLENDER_PATH=/path/to/blender   # or just 'blender' if on PATH
```

### 3. Download CC0 HDRI maps (optional but recommended)

```bash
python interior_ai/scripts/download_assets.py --hdri --output ./assets
```

### 4. Start the API server

```bash
python -m interior_ai.main server
# → Listening on http://localhost:8000
# → API docs: http://localhost:8000/docs
```

### 5. Start the frontend

```bash
cd interior_ai/frontend
npm run dev
# → http://localhost:5173
```

### 6. CLI design generation

```bash
python -m interior_ai.main design \
  --floor-plan path/to/plan.pdf \
  --style modern_organic \
  --prompt "Warm modern organic living room with curved sectional, light oak" \
  --output ./output
```

---

## Design Styles

| Style | Description |
|---|---|
| `modern_organic` | Warm neutrals, curved silhouettes, natural materials, boucle |
| `japandi` | Wabi-sabi minimalism, raw wood, zen restraint, muted tones |
| `scandinavian` | Bright whites, blonde wood, functional hygge warmth |
| `contemporary_luxury` | Rich materials, marble, velvet, high contrast drama |
| `minimalist` | Absolute restraint, negative space, monochrome palette |
| `transitional` | Bridge between traditional warmth and modern simplicity |
| `mid_century_modern` | 1950s optimism, teak, tapered legs, bold accents |

---

## Natural Language Editing

After generating a design:

```
"Move sofa closer to fireplace"
"Make room brighter"
"Use lighter wood flooring"
"Replace sectional with curved one"
"Add more storage"
"Use warmer lighting"
"Make it more japandi"
"Add a reading nook"
"Use cognac leather on the sofa"
"Make family-friendly"
```

---

## API Reference

Full interactive docs at `http://localhost:8000/docs` when the server is running.

| Endpoint | Method | Description |
|---|---|---|
| `/upload/floor-plan` | POST | Upload PDF/image/DXF/IFC |
| `/upload/inspiration` | POST | Upload inspiration image |
| `/design/parse-floor-plan` | POST | Parse uploaded floor plan |
| `/design/generate` | POST | Generate full interior design |
| `/design/styles` | GET | List all design styles |
| `/render/submit` | POST | Queue a render job |
| `/render/run/{job_id}` | POST | Execute render synchronously |
| `/render/result/{job_id}` | GET | Download rendered image |
| `/edit/command` | POST | Apply NL edit command |
| `/edit/preview` | POST | Preview intent without applying |
| `/edit/undo/{session_id}` | POST | Undo last command |
| `/assets/furniture` | GET | List furniture catalogue |
| `/health` | GET | System health + Blender status |

---

## Smoke Tests

```bash
python interior_ai/scripts/test_pipeline.py
```

Runs 9 tests covering types, styles, materials, furniture, NLP, and synthetic scene generation — no Blender or GPU required.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Rendering | Blender + Cycles / Eevee |
| Computer vision | OpenCV, PyTorch, SAM2, Depth Anything V2 |
| 3D / BIM | trimesh, Open3D, IfcOpenShell, ezdxf |
| OCR | Tesseract / PaddleOCR |
| Geometry | Shapely, NumPy, SciPy |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18 + Vite |
| Assets | CC0 / Poly Haven / procedural |

---

## Performance Targets

| Task | Target |
|---|---|
| First design draft | < 5 minutes |
| Eevee preview render | ~30 seconds |
| Cycles photoreal render | < 20 minutes (RTX 4070+) |

---

## Roadmap

- **Phase 1 (current):** Single-room rendering, static photoreal images
- **Phase 2:** Whole-home reconstruction, interactive editing
- **Phase 3:** AI layout optimisation, furniture recommendation engine
- **Phase 4:** Real-time walkthroughs, AR/VR support
- **Phase 5:** Collaborative multi-user designer mode

---

## License

All code: MIT. All bundled assets: CC0 (Poly Haven) or procedurally generated.
No enterprise licensing dependencies.
