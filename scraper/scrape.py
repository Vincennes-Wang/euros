"""Scrape ECB €2 commemorative coin pages into data/coins.json.

Usage:
    python -m scraper.scrape                 # fetch all years, update data/
    python -m scraper.scrape --years 2024 2025
    python -m scraper.scrape --offline       # re-parse data/raw only, no network
    python -m scraper.scrape --strict        # exit 1 on any warning, archive fallback or image failure

Incremental: unchanged coins keep their bytes and scraped_at; existing images are
not downloaded again unless their source URL changed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from scraper import ecb

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
IMAGES = DATA / "images"
COINS_JSON = DATA / "coins.json"

USER_AGENT = "euros-coin-collection/0.1 (+https://github.com/Vincennes-Wang/euros)"
DELAY_SECONDS = 2.0

# Fields compared to decide whether a coin changed. scraped_at and description_zh
# are excluded: the first is bookkeeping, the second comes from migrate_legacy.
CONTENT_FIELDS = [
    "year", "country", "country_code", "title", "description_en", "volume_raw", "volume",
    "issue_date_raw", "issue_date", "image", "image_source_url", "source_url",
    "is_joint_issue", "variant_images",
]
FIELD_ORDER = [
    "id", "year", "country", "country_code", "title", "description_en", "description_zh",
    "volume_raw", "volume", "issue_date_raw", "issue_date", "image", "image_source_url",
    "variant_images", "source_url", "is_joint_issue", "scraped_at",
]


class Fetcher:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last = 0.0

    def get(self, url: str) -> requests.Response:
        wait = DELAY_SECONDS - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            return self.session.get(url, timeout=30)
        finally:
            self._last = time.monotonic()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def load_existing() -> list[dict]:
    return json.loads(COINS_JSON.read_text(encoding="utf-8")) if COINS_JSON.exists() else []


# Server time embedded in every page; differs on each fetch and is not content.
VOLATILE_RE = re.compile(r"ECB\.clientTimeError = \d+")


def same_page(a: str, b: str) -> bool:
    return VOLATILE_RE.sub("", a) == VOLATILE_RE.sub("", b)


def get_page(fetcher: Fetcher | None, year: int, warnings: list[str]) -> str | None:
    """Fetch a year page and archive it. Fall back to data/raw (with a warning) if the fetch fails."""
    raw_path = RAW / f"comm_{year}.en.html"
    if fetcher:
        try:
            resp = fetcher.get(ecb.page_url(year))
        except requests.RequestException as exc:
            warnings.append(f"{year}: fetch failed ({exc}); used archive")
        else:
            if resp.status_code == 404:
                return None
            if resp.ok:
                resp.encoding = "utf-8"
                old = raw_path.read_bytes().decode("utf-8") if raw_path.exists() else None
                if old is None or not same_page(old, resp.text):
                    write_if_changed(raw_path, resp.text.encode("utf-8"))
                    print(f"  {year}: raw HTML saved")
                return resp.text
            warnings.append(f"{year}: HTTP {resp.status_code}; used archive")
    return raw_path.read_bytes().decode("utf-8") if raw_path.exists() else None


def assign_ids(coins: list[dict], existing: list[dict]) -> None:
    """Reuse ids of matching existing coins; generate year-cc-slug for new ones."""
    by_image = {(c["year"], c["image_source_url"]): c["id"] for c in existing if c.get("image_source_url")}
    by_title = {(c["year"], c["country_code"], c["title"]): c["id"] for c in existing}
    # Image URLs are not unique (placeholders), so a URL match only counts once.
    image_counts: dict = {}
    for c in coins:
        key = (c["year"], c["image_source_url"])
        image_counts[key] = image_counts.get(key, 0) + 1
    taken: set[str] = set()
    pending = []
    for c in coins:
        key_img = (c["year"], c["image_source_url"])
        candidate = by_title.get((c["year"], c["country_code"], c["title"]))
        if candidate is None and image_counts[key_img] == 1:
            candidate = by_image.get(key_img)
        if candidate and candidate not in taken:
            c["id"] = candidate
            taken.add(candidate)
        else:
            pending.append(c)
    for c in pending:
        base = f"{c['year']}-{c['country_code'] or 'xx'}-{ecb.slugify(c['title'] or 'untitled')}"
        new_id, n = base, 2
        while new_id in taken:
            new_id, n = f"{base}-{n}", n + 1
        c["id"] = new_id
        taken.add(new_id)


def image_ext(url: str) -> str:
    name = url.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "jpg"
    return "jpg" if ext == "jpeg" else ext


def download(fetcher: Fetcher | None, url: str, path: Path, force: bool, warnings: list[str]) -> bool:
    """Download url to path unless present. Return False if the file is missing afterwards."""
    if path.exists() and not force:
        return True
    if fetcher is None:
        return path.exists()
    try:
        resp = fetcher.get(url)
    except requests.RequestException as exc:
        warnings.append(f"image failed: {url} ({exc})")
        return path.exists()
    if not resp.ok or not resp.headers.get("Content-Type", "").startswith("image/"):
        warnings.append(f"image failed: {url} (HTTP {resp.status_code}, {resp.headers.get('Content-Type')})")
        return path.exists()
    write_if_changed(path, resp.content)
    print(f"  image saved: {path.relative_to(ROOT)}")
    return True


def attach_images(fetcher: Fetcher | None, coin: dict, old: dict | None, warnings: list[str]) -> None:
    year_dir = IMAGES / str(coin["year"])
    src = coin["image_source_url"]
    coin["image"] = None
    if src:
        path = year_dir / f"{coin['id']}.{image_ext(src)}"
        changed = bool(old) and old.get("image_source_url") != src
        if download(fetcher, src, path, changed, warnings):
            coin["image"] = path.relative_to(ROOT).as_posix()
    sources = coin.pop("variant_image_sources", None)
    if sources is None:
        return
    old_variants = (old or {}).get("variant_images") or {}
    variants = {}
    for key, url in sources.items():
        path = year_dir / coin["id"] / f"{key}.{image_ext(url)}"
        changed = key in old_variants and old_variants[key].get("image_source_url") != url
        local = download(fetcher, url, path, changed, warnings)
        variants[key] = {"image": path.relative_to(ROOT).as_posix() if local else None, "image_source_url": url}
    coin["variant_images"] = variants


def finalize(coin: dict, old: dict | None, timestamp: str) -> dict:
    coin["description_zh"] = (old or {}).get("description_zh")
    unchanged = old is not None and all(old.get(f) == coin.get(f) for f in CONTENT_FIELDS)
    coin["scraped_at"] = old["scraped_at"] if unchanged else timestamp
    return {k: coin[k] for k in FIELD_ORDER if k in coin}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, nargs="*", help="only these years (default: all)")
    parser.add_argument("--offline", action="store_true", help="parse data/raw only; no network")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on any warning, archive fallback, dropped coin or failed image")
    args = parser.parse_args(argv)

    fetcher = None if args.offline else Fetcher()
    existing = load_existing()
    timestamp = now_iso()

    if args.years:
        years = sorted(args.years)
    else:
        last = datetime.now(timezone.utc).year + 1
        years = list(range(ecb.FIRST_YEAR, last + 1))

    scraped: dict[int, list[dict]] = {}
    warnings: list[str] = []
    for year in years:
        html = get_page(fetcher, year, warnings)
        if html is None:
            if not args.years and year > datetime.now(timezone.utc).year - 1:
                continue  # future year not published yet
            warnings.append(f"{year}: page not available")
            continue
        coins, page_warnings = ecb.parse_page(html, year)
        warnings += page_warnings
        old_year = [c for c in existing if c["year"] == year]
        assign_ids(coins, old_year)
        old_by_id = {c["id"]: c for c in old_year}
        result = []
        for coin in coins:
            old = old_by_id.get(coin["id"])
            attach_images(fetcher, coin, old, warnings)
            result.append(finalize(coin, old, timestamp))
        removed = sorted(set(old_by_id) - {c["id"] for c in result})
        for rid in removed:
            warnings.append(f"{year}: {rid} no longer on the page (dropped)")
        scraped[year] = result
        print(f"{year}: {len(result)} coins")

    kept_years = {c["year"] for c in existing} - set(scraped)
    out = [c for c in existing if c["year"] in kept_years]
    for year in sorted(scraped):
        out += scraped[year]
    out.sort(key=lambda c: c["year"])  # stable: keeps page order within a year

    ids = [c["id"] for c in out]
    if len(ids) != len(set(ids)):
        warnings.append("duplicate ids in output")
    data = (json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    print(f"coins.json {'updated' if write_if_changed(COINS_JSON, data) else 'unchanged'}: {len(out)} coins")
    for w in warnings:
        print(f"WARNING {w}", file=sys.stderr)
    if args.strict and warnings:
        print(f"strict: {len(warnings)} warning(s); failing", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
