"""Generate 256 px WebP thumbnails for every image in data/images/.

data/images/2004/x.jpg -> data/thumbs/2004/x.webp (same relative path, .webp).
Incremental: a thumbnail is rebuilt only when missing or older than its source.
Thumbnails without a source image are deleted.

Usage: python scripts/make_thumbs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "data" / "images"
THUMBS = ROOT / "data" / "thumbs"
SIZE = 256
QUALITY = 80


def thumb_path(image: Path) -> Path:
    return (THUMBS / image.relative_to(IMAGES)).with_suffix(".webp")


def main() -> int:
    sources = [p for p in IMAGES.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    made = 0
    for src in sources:
        dst = thumb_path(src)
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
            im.thumbnail((SIZE, SIZE), Image.LANCZOS)
            im.save(dst, "WEBP", quality=QUALITY, method=6)
        made += 1
    wanted = {thumb_path(s) for s in sources}
    removed = 0
    for t in THUMBS.rglob("*.webp"):
        if t not in wanted:
            t.unlink()
            removed += 1
    for d in sorted((p for p in THUMBS.rglob("*") if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    total = sum(t.stat().st_size for t in THUMBS.rglob("*.webp"))
    print(f"thumbnails: {len(sources)} sources, {made} built, {removed} removed, {total / 1e6:.1f} MB total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
