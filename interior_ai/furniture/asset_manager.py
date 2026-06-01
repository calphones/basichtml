"""Manage furniture asset files: discovery, download, caching, validation."""

from __future__ import annotations
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Optional
import urllib.request

from .furniture_db import FurnitureDatabase, FurnitureAsset
from ..types import FurnitureCategory


# Poly Haven model manifest (CC0 assets safe for commercial use)
POLY_HAVEN_BASE = "https://api.polyhaven.com/asset"
KNOWN_CC0_SOURCES = ["poly_haven", "procedural"]


class AssetManager:
    """Resolve, download, cache, and validate 3D furniture model files.

    Asset resolution priority:
    1. Local cache (previously downloaded or user-provided)
    2. Procedural generation (always available, no download needed)
    3. Poly Haven API (CC0 .blend files)
    4. Fallback: generate procedurally

    Models are cached under `assets_root/furniture/<id>/model.glb`.
    """

    def __init__(
        self,
        assets_root: str | Path = "./assets",
        db: Optional[FurnitureDatabase] = None,
    ):
        self.root = Path(assets_root)
        self.furniture_dir = self.root / "furniture"
        self.furniture_dir.mkdir(parents=True, exist_ok=True)
        self._db = db or FurnitureDatabase()
        self._manifest_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, asset_id: str) -> Optional[Path]:
        """Return local path to model file, downloading if necessary.

        Returns None if the asset should be generated procedurally.
        """
        asset = self._db.get(asset_id)
        if asset is None:
            return None
        if asset.source == "procedural" or asset.model_path is None:
            return None  # signal caller to use ProceduralFurnitureGen
        local = self.furniture_dir / asset_id / "model.glb"
        if local.exists():
            return local
        return None  # would download here in production

    def list_available(self, category: Optional[FurnitureCategory] = None) -> list[FurnitureAsset]:
        if category:
            return self._db.by_category(category)
        return self._db.all_assets()

    def import_user_model(
        self, src_path: str | Path, asset_id: str, name: str,
        category: FurnitureCategory,
    ) -> FurnitureAsset:
        """Import a user-provided .glb/.fbx/.obj model into the local catalogue."""
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(src)
        dest_dir = self.furniture_dir / asset_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / ("model" + src.suffix)
        shutil.copy2(src, dest)
        from ..types import Vec3
        asset = FurnitureAsset(
            id=asset_id,
            name=name,
            category=category,
            license="user_provided",
            source="user",
            model_path=str(dest.relative_to(self.root)),
            thumbnail_path=None,
            dimensions_m=Vec3(1.0, 1.0, 1.0),
        )
        self._db._assets[asset_id] = asset
        return asset

    def scan_local(self) -> list[FurnitureAsset]:
        """Discover .glb / .fbx files already in assets/furniture/."""
        found = []
        for model_file in self.furniture_dir.rglob("*.glb"):
            asset_id = model_file.parent.name
            if self._db.get(asset_id) is None:
                from ..types import Vec3
                asset = FurnitureAsset(
                    id=asset_id,
                    name=asset_id.replace("_", " ").title(),
                    category=FurnitureCategory.DECOR,
                    license="unknown",
                    source="local",
                    model_path=str(model_file.relative_to(self.root)),
                    thumbnail_path=None,
                    dimensions_m=Vec3(1.0, 1.0, 1.0),
                )
                self._db._assets[asset_id] = asset
                found.append(asset)
        return found

    def cache_stats(self) -> dict:
        total = sum(1 for _ in self.furniture_dir.rglob("*.glb"))
        size_mb = sum(
            f.stat().st_size for f in self.furniture_dir.rglob("*") if f.is_file()
        ) / 1_048_576
        return {"cached_models": total, "cache_size_mb": round(size_mb, 2)}
