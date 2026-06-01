# How to Run — Interior AI Designer

Complete step-by-step guide for getting the system running locally and wiring it
up to a local LLM for AI-assisted development and NLP editing.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Running the System](#3-running-the-system)
4. [Using the UI](#4-using-the-ui)
5. [CLI Workflow](#5-cli-workflow)
6. [Using a Local AI Model as Context](#6-using-a-local-ai-model-as-context)
7. [Replacing the NLP Editor with a Local LLM](#7-replacing-the-nlp-editor-with-a-local-llm)
8. [Recommended Local Models](#8-recommended-local-models)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

Install these before anything else.

### Required

| Tool | Version | Download |
|---|---|---|
| Python | 3.10+ | https://python.org |
| Blender | 3.6 LTS or 4.x | https://www.blender.org/download/ |
| Node.js | 18+ | https://nodejs.org |

### Recommended

| Tool | Purpose | Install |
|---|---|---|
| Tesseract OCR | Floor plan dimension text parsing | `sudo apt install tesseract-ocr` / `brew install tesseract` |
| CUDA Toolkit | GPU rendering in Blender Cycles | https://developer.nvidia.com/cuda-downloads |
| Ollama | Local LLM for NLP editing | https://ollama.ai |

### Hardware Targets

| Task | Minimum | Recommended |
|---|---|---|
| Floor plan parsing + design gen | Any modern CPU | Any modern CPU |
| Fast preview render (Eevee) | GTX 1060 / 8 GB RAM | RTX 3070+ |
| Photoreal render (Cycles) | RTX 3070 / 16 GB RAM | RTX 4070 / 4080 |

---

## 2. Installation

```bash
# 1. Clone the repo
git clone https://github.com/calphones/basichtml.git
cd basichtml

# 2. Run the setup script — creates .venv, installs all Python deps,
#    checks for Blender/Tesseract, creates asset directories, installs
#    frontend npm packages
bash interior_ai/scripts/setup_env.sh

# 3. Activate the virtualenv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# 4. Tell the system where Blender is
export BLENDER_PATH=/usr/bin/blender          # Linux (adjust path)
# export BLENDER_PATH=/Applications/Blender.app/Contents/MacOS/Blender  # macOS
# set BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.1\blender.exe  # Windows

# Optional: download CC0 HDRI maps for better lighting (~400 MB each)
python interior_ai/scripts/download_assets.py --hdri --output ./assets
```

### Verify everything works (no GPU or Blender needed)

```bash
python interior_ai/scripts/test_pipeline.py
```

Expected output:
```
Interior AI Designer — Pipeline Smoke Tests
==================================================
  [✓] types
  [✓] style_profiles
  [✓] material_library
  [✓] furniture_db
  [✓] intent_classifier
  [✓] color_harmonizer
  [✓] procedural_gen
  [✓] synthetic_scene — 5 furniture items placed
  [✓] nlp_mutator — 6 furniture after mutations
==================================================
Results: 9 passed, 0 failed
```

---

## 3. Running the System

You need two terminals — one for the API backend, one for the frontend.

### Terminal 1 — API server

```bash
source .venv/bin/activate
export BLENDER_PATH=/path/to/blender

python -m interior_ai.main server
# Listening on http://0.0.0.0:8000
# Docs: http://localhost:8000/docs
```

### Terminal 2 — Frontend

```bash
cd interior_ai/frontend
npm run dev
# Running on http://localhost:5173
```

Open **http://localhost:5173** in your browser.

> **API-only users:** The full REST API is at http://localhost:8000.
> Interactive Swagger docs at http://localhost:8000/docs.

---

## 4. Using the UI

The UI is a 6-tab workflow:

### Tab 1 — Upload

1. Drag and drop your **builder floor plan** (PDF, PNG, JPG, DXF, or IFC)
2. Optionally add an **inspiration image** (extracts palette + style cues)
3. Click **Analyse Floor Plan** — the backend parses walls, doors, windows, stairs

### Tab 2 — Style

1. Click a style card (Modern Organic, Japandi, Scandinavian, etc.)
2. Type a natural language prompt describing your vision:
   ```
   Warm modern organic living room with curved sectional, light oak finishes,
   black accents, soft beige palette, realistic lighting, family-friendly layout
   ```
3. Click **Generate Design**

### Tab 3 — Design

- See room count, furniture count, and any layout violations
- Choose render mode: Quick Preview (~30s), Photoreal (~20min), Floor Plan View
- Pick a camera angle: Eye Level, 3/4 View, or Top Down

### Tab 4 — Render

- View the rendered image
- Download as PNG
- Re-render with different settings

### Tab 5 — Edit (NLP)

Type natural language commands to modify the scene:

```
Move sofa closer to fireplace
Make room brighter
Use lighter wood flooring
Replace sectional with a curved one
Add more storage
Use warmer lighting
Make it more japandi
Add a reading nook
Use cognac leather on the sofa
Make it family-friendly
```

Click **Undo** to step back. Click **Re-render** to see changes.

### Tab 6 — Materials

Visual board of all materials applied to the design for the selected style.

---

## 5. CLI Workflow

No UI needed — run the full pipeline from the command line.

### Basic design + preview render

```bash
python -m interior_ai.main design \
  --floor-plan path/to/plan.pdf \
  --style modern_organic \
  --output ./output
```

### With a prompt and inspiration image

```bash
python -m interior_ai.main design \
  --floor-plan plan.pdf \
  --style japandi \
  --prompt "Zen bedroom with platform bed, white oak, natural linen, minimal decor" \
  --inspiration inspo.jpg \
  --output ./output
```

### Photoreal render

```bash
python -m interior_ai.main design \
  --floor-plan plan.pdf \
  --style modern_organic \
  --render-mode photoreal \
  --output ./output
```

### Supported floor plan formats

| Format | Flag | Notes |
|---|---|---|
| PDF | `--floor-plan plan.pdf` | Builder PDFs, multi-page supported |
| PNG/JPG | `--floor-plan plan.png` | Scanned or exported images |
| DXF | `--floor-plan plan.dxf` | AutoCAD exports |
| IFC | `--floor-plan building.ifc` | BIM models (Revit, ArchiCAD) |

---

## 6. Using a Local AI Model as Context

This section covers how to feed the codebase to a local LLM so it can help you
extend, debug, or iterate on the system — without sending your floor plans or
design data to any cloud service.

### Option A — Ollama (simplest, recommended)

[Ollama](https://ollama.ai) runs models locally with a simple CLI and OpenAI-compatible API.

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a capable code model (choose one)
ollama pull codellama:34b         # good at Python, large context
ollama pull deepseek-coder:33b   # excellent code reasoning
ollama pull llama3.1:70b         # general purpose, huge context
ollama pull qwen2.5-coder:32b    # strong code + long context

# Start the Ollama server (runs on http://localhost:11434)
ollama serve
```

### Feed the codebase as context

The cleanest way to give a local LLM the full project context is to concatenate
the source into a single context file:

```bash
# Generate a context dump of the entire codebase
find interior_ai -name "*.py" | sort | xargs awk '
  { print FILENAME ":" NR ": " $0 }
  FNR==1 { print "\n\n### FILE: " FILENAME "\n" }
' > /tmp/interior_ai_context.txt

# Check size
wc -l /tmp/interior_ai_context.txt
```

Then pass it to Ollama:

```bash
ollama run deepseek-coder:33b "$(cat <<EOF
You are helping develop an open-source AI interior design system.
Here is the complete codebase:

$(cat /tmp/interior_ai_context.txt)

Question: How do I add support for spiral staircases to the staircase detector?
EOF
)"
```

### Option B — Open WebUI (browser-based chat with file upload)

[Open WebUI](https://github.com/open-webui/open-webui) gives you a ChatGPT-like
interface connected to your local Ollama models.

```bash
# Run Open WebUI via Docker
docker run -d -p 3001:8080 \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main

# Open http://localhost:3001
```

Then in Open WebUI:
1. Upload the Python files from `interior_ai/` as documents
2. Enable RAG (Retrieval Augmented Generation)
3. Ask questions about the codebase or request new features

### Option C — LM Studio (desktop GUI)

1. Download [LM Studio](https://lmstudio.ai)
2. Pull `Qwen2.5-Coder-32B-Instruct` or `DeepSeek-Coder-V2`
3. Start the local server (OpenAI-compatible at `http://localhost:1234/v1`)
4. Use the system prompt below

### Option D — Continue.dev (VSCode extension)

[Continue](https://continue.dev) is an open-source Copilot alternative for VSCode/JetBrains.

```json
// ~/.continue/config.json
{
  "models": [
    {
      "title": "Ollama - DeepSeek Coder",
      "provider": "ollama",
      "model": "deepseek-coder:33b",
      "contextLength": 32768
    }
  ],
  "contextProviders": [
    { "name": "codebase" },
    { "name": "diff" },
    { "name": "open" }
  ]
}
```

Open the `basichtml/` folder in VSCode, enable Continue, and it will index the
full codebase for context-aware completions and chat.

---

## 7. Replacing the NLP Editor with a Local LLM

The built-in NLP editor (`interior_ai/nlp_editor/`) uses rule-based intent
classification. You can upgrade it to a local LLM for much richer command
understanding.

### Wire up Ollama to the intent classifier

Create `interior_ai/nlp_editor/llm_classifier.py`:

```python
"""LLM-powered intent classifier using local Ollama API."""
import json
import urllib.request
from .intent_classifier import Intent, IntentType

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-coder:33b"   # or llama3.1:8b for speed

SYSTEM_PROMPT = """You are an interior design AI assistant.
Parse the user's command and return JSON with these fields:
- intent_type: one of move_furniture, replace_furniture, remove_furniture,
  add_furniture, change_style, change_color, change_material,
  change_lighting, change_brightness, add_storage, make_family_friendly, unknown
- confidence: 0.0-1.0
- subject: the furniture or element being changed (string or null)
- target: where to move it or what to change it to (string or null)
- modifier: descriptive adjective like "warmer", "lighter", "curved" (string or null)
Return only valid JSON, no explanation."""

def classify_with_llm(text: str) -> Intent:
    payload = json.dumps({
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nCommand: {text}",
        "stream": False,
        "format": "json",
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            result = json.loads(data["response"])
            return Intent(
                type=IntentType(result.get("intent_type", "unknown")),
                confidence=float(result.get("confidence", 0.8)),
                subject=result.get("subject"),
                target=result.get("target"),
                modifier=result.get("modifier"),
                raw_text=text,
            )
    except Exception:
        # Fall back to rule-based classifier
        from .intent_classifier import IntentClassifier
        return IntentClassifier().classify(text)
```

Then in `interior_ai/nlp_editor/command_parser.py`, swap the classifier:

```python
# Original:
from .intent_classifier import IntentClassifier
self._classifier = IntentClassifier()

# Replace with:
import os
if os.environ.get("USE_LOCAL_LLM") == "1":
    from .llm_classifier import classify_with_llm
    self._classifier = type("LLMClassifier", (), {"classify": lambda s, t: classify_with_llm(t)})()
else:
    from .intent_classifier import IntentClassifier
    self._classifier = IntentClassifier()
```

Enable it:

```bash
export USE_LOCAL_LLM=1
python -m interior_ai.main server
```

Now commands like *"the sofa feels too close to the TV, can you push it back a bit?"*
will be understood by the LLM instead of needing to match a pattern.

---

## 8. Recommended Local Models

| Model | Size | Best for | Context |
|---|---|---|---|
| `deepseek-coder:33b` | 20 GB | Code generation, debugging | 32K |
| `qwen2.5-coder:32b` | 20 GB | Code + long documents | 128K |
| `llama3.1:70b` | 40 GB | General reasoning + NLP | 128K |
| `llama3.1:8b` | 5 GB | Fast NLP on laptop | 128K |
| `codellama:34b` | 20 GB | Python-heavy code tasks | 16K |
| `mistral:7b` | 4 GB | Quick local assistant | 32K |

### System prompt to paste into any local chat

```
You are an expert Python developer helping extend an open-source AI interior
design system called Interior AI Designer.

The system architecture:
- input_parser/: PDF, image, DXF, IFC floor plan parsers
- floorplan/: OpenCV-based wall/door/window/stair detection + vectorisation
- reconstruction/: 2D→3D mesh extrusion, depth estimation, SceneGraph
- design_engine/: furniture placement, style profiles, layout optimisation
- furniture/: CC0 procedural mesh generator, asset catalogue
- materials/: PBR material library, palette extraction, colour harmoniser
- lighting/: recessed grid, daylight simulation, HDRI
- blender_integration/: subprocess bridge → Blender --background
- nlp_editor/: intent classification, scene mutation, undo
- api/: FastAPI REST backend
- frontend/: React 18 + Vite

All shared types are in interior_ai/types.py.
The system uses SceneGraph as the central data structure passed between modules.
Blender is driven via a subprocess — never imported directly outside blender_integration/.

Ask me to show you any file before suggesting changes to it.
```

---

## 9. Troubleshooting

### "Blender not found"

```bash
# Find where Blender is installed
which blender
# or on macOS:
find /Applications -name "blender" -type f 2>/dev/null

export BLENDER_PATH=/found/path/blender
```

### "Module not found" errors

```bash
# Make sure you're in the virtualenv
source .venv/bin/activate
# Reinstall deps
pip install -r interior_ai/requirements.txt
```

### Render output is blank / black

1. Check Blender is available: `GET http://localhost:8000/health`
2. Look for errors in the API server terminal output
3. Try a preview render first (Eevee) before photoreal (Cycles)
4. Ensure the scene has at least one light: the reconstructor adds defaults,
   but a missing floor plan means no window lights

### PDF floor plan produces no walls

- Ensure the PDF contains a vector floor plan (not a photograph of a plan)
- Try exporting from your builder's software as a higher DPI raster (300 DPI PNG)
- DXF export from AutoCAD/Revit gives the most accurate results

### Tesseract OCR errors

```bash
# Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-eng
# macOS
brew install tesseract
```

Scale inference falls back to US residential standard (1/4" = 1') if OCR fails —
still works, just less accurate for non-standard drawings.

### Ollama connection refused for local LLM

```bash
# Make sure Ollama server is running
ollama serve
# Check it's up
curl http://localhost:11434/api/tags
```

### Frontend can't reach the API

The Vite dev server proxies `/upload`, `/design`, `/render`, `/edit` to
`http://localhost:8000`. Make sure the API server is running on port 8000 before
starting the frontend. Check `interior_ai/frontend/vite.config.js` if you've
changed the API port.

---

## Quick Reference

```bash
# Full local stack
source .venv/bin/activate && export BLENDER_PATH=/path/to/blender

# API + UI
python -m interior_ai.main server &
cd interior_ai/frontend && npm run dev

# CLI one-shot
python -m interior_ai.main design --floor-plan plan.pdf --style modern_organic

# Smoke tests
python interior_ai/scripts/test_pipeline.py

# Local LLM (Ollama)
ollama pull deepseek-coder:33b && ollama serve &
export USE_LOCAL_LLM=1 && python -m interior_ai.main server

# Download CC0 HDRI maps
python interior_ai/scripts/download_assets.py --hdri
```
