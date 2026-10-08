"""Validate data/coins.json against the archived ECB pages and the legacy xlsx.

Usage: python scripts/validate.py
Exit code 1 if counts mismatch or required data is missing.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper import ecb  # noqa: E402
from scraper.scrape import COINS_JSON, RAW  # noqa: E402

XLSX = ROOT / "legacy" / "硬币收藏清单.xlsx"
REQUIRED = ["id", "year", "country", "country_code", "title", "description_en", "volume_raw",
            "issue_date_raw", "issue_date", "image", "image_source_url", "source_url"]
PLAIN_VOLUME_RE = re.compile(r"^\d[\d ,.]*( million)? coins$")
PLAIN_DATE_RE = re.compile(r"^(\d{1,2} )?[A-Z][a-z]+ \d{4}$")


def legacy_counts() -> Counter:
    if not XLSX.exists():
        return Counter()
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)["纪念币"]
    return Counter(int(r[1]) for r in ws.iter_rows(min_row=2, values_only=True) if r[1] is not None)


def main() -> int:
    coins = json.loads(COINS_JSON.read_text(encoding="utf-8"))
    ok = True

    print("## Count per year: ECB page boxes vs coins.json vs legacy xlsx")
    page = {int(p.name[5:9]): ecb.count_boxes(p.read_text(encoding="utf-8")) for p in sorted(RAW.glob("comm_*.en.html"))}
    ours = Counter(c["year"] for c in coins)
    legacy = legacy_counts()
    print(f"  {'year':<6}{'page':>6}{'json':>6}{'xlsx':>6}")
    for year in sorted(set(page) | set(ours)):
        flag = "" if page.get(year) == ours.get(year) else "  MISMATCH"
        ok &= not flag
        print(f"  {year:<6}{page.get(year, '-'):>6}{ours.get(year, 0):>6}{legacy.get(year, '-'):>6}{flag}")
    print(f"  {'total':<6}{sum(page.values()):>6}{len(coins):>6}{sum(legacy.values()) or '-':>6}")

    ids = Counter(c["id"] for c in coins)
    dupes = [i for i, n in ids.items() if n > 1]
    print(f"\n## Duplicate ids: {len(dupes)}")
    for i in dupes:
        print(f"  {i}")
    ok &= not dupes

    print("\n## Empty required fields")
    empty = [(c["id"], f) for c in coins for f in REQUIRED if c.get(f) in (None, "")]
    for cid, f in empty:
        print(f"  {cid}: {f}")
    if not empty:
        print("  none")

    print("\n## Missing image files")
    missing = [p for c in coins for p in [c.get("image")] + [v["image"] for v in (c.get("variant_images") or {}).values()]
               if p and not (ROOT / p).exists()]
    for p in missing:
        print(f"  {p}")
    print("  none" if not missing else "")
    ok &= not missing

    print("\n## Suspicious volume (null or not '<number> [million] coins')")
    for c in coins:
        raw = c.get("volume_raw") or ""
        if c.get("volume") is None or not PLAIN_VOLUME_RE.match(raw) or len(raw) > 40:
            print(f"  {c['id']}: volume={c.get('volume')} raw={raw!r}")

    print("\n## Issue date: year-only precision or unparsed")
    for c in coins:
        raw = c.get("issue_date_raw") or ""
        if c.get("issue_date") is None or not PLAIN_DATE_RE.match(raw) or len(raw) > 40:
            print(f"  {c['id']}: issue_date={c.get('issue_date')} raw={raw!r}")

    print("\n## Placeholder or shared images")
    shared = Counter(c["image_source_url"] for c in coins)
    for c in coins:
        url = c.get("image_source_url") or ""
        if "placeholder" in url.lower() or shared[url] > 1:
            print(f"  {c['id']}: {url}")

    print("\n## Joint issues")
    for c in coins:
        if c["is_joint_issue"]:
            print(f"  {c['id']}: {len(c.get('variant_images') or {})} variants: {', '.join(c.get('variant_images') or {})}")

    print(f"\nRESULT: {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
