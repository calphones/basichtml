#!/usr/bin/env python3
"""Download CC0 HDRI maps from Poly Haven and set up the asset directory.

Usage:
    python interior_ai/scripts/download_assets.py --hdri --output ./assets

Note: HDRI downloads require ~400 MB per file. Run once on initial setup.
All assets used are CC0 (public domain equivalent) from polyhaven.com.
"""

from __future__ import annotations
import argparse
import os
import sys
import urllib.request
from pathlib import Path

POLY_HAVEN_BASE = "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/4k"

HDRI_DOWNLOADS = [
    ("venice_sunset_4k.hdr",   f"{POLY_HAVEN_BASE}/venice_sunset_4k.hdr"),
    ("studio_small_08_4k.hdr", f"{POLY_HAVEN_BASE}/studio_small_08_4k.hdr"),
    ("overcast_sky_4k.hdr",    f"{POLY_HAVEN_BASE}/overcast_sky_4k.hdr"),
    ("morning_light_4k.hdr",   f"{POLY_HAVEN_BASE}/morning_light_4k.hdr"),
]

TEXTURE_DOWNLOADS: list[tuple[str, str]] = []  # add Poly Haven texture URLs here


def download_file(url: str, dest: Path, label: str) -> bool:
    if dest.exists():
        print(f"  [skip] {label} already exists")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {label} ({url}) → {dest} ...")
    try:
        def progress(count, block_size, total_size):
            if total_size > 0:
                pct = min(100, count * block_size * 100 // total_size)
                print(f"\r    {pct}%", end="", flush=True)
        urllib.request.urlretrieve(url, str(dest), reporthook=progress)
        print(f"\r  ✓ {label}")
        return True
    except Exception as e:
        print(f"\r  ✗ Failed to download {label}: {e}")
        if dest.exists():
            dest.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Download CC0 assets for Interior AI")
    parser.add_argument("--hdri", action="store_true", help="Download HDRI maps (~400MB each)")
    parser.add_argument("--textures", action="store_true", help="Download PBR textures")
    parser.add_argument("--output", default="./assets", help="Asset root directory")
    parser.add_argument("--dry-run", action="store_true", help="List files without downloading")
    args = parser.parse_args()

    output = Path(args.output)
    print(f"Asset directory: {output.resolve()}")

    if not args.hdri and not args.textures:
        print("Nothing to download. Use --hdri or --textures.")
        parser.print_help()
        return

    if args.dry_run:
        print("\nDry run — files that would be downloaded:")
        if args.hdri:
            for name, url in HDRI_DOWNLOADS:
                print(f"  HDRI: {name}")
        if args.textures:
            for name, url in TEXTURE_DOWNLOADS:
                print(f"  Texture: {name}")
        return

    if args.hdri:
        print("\nDownloading HDRI environment maps (CC0 from Poly Haven)...")
        hdri_dir = output / "hdri"
        failed = []
        for name, url in HDRI_DOWNLOADS:
            ok = download_file(url, hdri_dir / name, name)
            if not ok:
                failed.append(name)
        if failed:
            print(f"\nWarning: {len(failed)} HDRI(s) failed to download: {failed}")
        else:
            print(f"\n✓ All {len(HDRI_DOWNLOADS)} HDRI maps downloaded")

    if args.textures and TEXTURE_DOWNLOADS:
        print("\nDownloading PBR textures (CC0 from Poly Haven)...")
        tex_dir = output / "textures"
        for name, url in TEXTURE_DOWNLOADS:
            download_file(url, tex_dir / name, name)

    print("\nAsset download complete.")


if __name__ == "__main__":
    main()
