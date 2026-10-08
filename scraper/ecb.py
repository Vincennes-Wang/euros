"""Pure parsing helpers for ECB €2 commemorative coin pages (no network I/O)."""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests.utils import requote_uri

BASE_URL = "https://www.ecb.europa.eu/euro/coins/comm/html/"
FIRST_YEAR = 2004


def page_url(year: int) -> str:
    return f"{BASE_URL}comm_{year}.en.html"


# Canonical name and ISO 3166-1 alpha-2 code (lowercase). "eu" marks joint issues.
COUNTRIES = {
    "andorra": ("Andorra", "ad"),
    "austria": ("Austria", "at"),
    "belgium": ("Belgium", "be"),
    "bulgaria": ("Bulgaria", "bg"),
    "croatia": ("Croatia", "hr"),
    "cyprus": ("Cyprus", "cy"),
    "estonia": ("Estonia", "ee"),
    "finland": ("Finland", "fi"),
    "france": ("France", "fr"),
    "germany": ("Germany", "de"),
    "greece": ("Greece", "gr"),
    "ireland": ("Ireland", "ie"),
    "italy": ("Italy", "it"),
    "latvia": ("Latvia", "lv"),
    "lithuania": ("Lithuania", "lt"),
    "luxembourg": ("Luxembourg", "lu"),
    "malta": ("Malta", "mt"),
    "monaco": ("Monaco", "mc"),
    "netherlands": ("Netherlands", "nl"),
    "the netherlands": ("Netherlands", "nl"),
    "nederland": ("Netherlands", "nl"),
    "portugal": ("Portugal", "pt"),
    "san marino": ("San Marino", "sm"),
    "slovakia": ("Slovakia", "sk"),
    "slovenia": ("Slovenia", "si"),
    "spain": ("Spain", "es"),
    "vatican": ("Vatican City", "va"),
    "vatican city": ("Vatican City", "va"),
    "euro area countries": ("Euro area countries", "eu"),
}


def normalize_country(name: str) -> tuple[str, str] | None:
    key = re.sub(r"[\s_]+", " ", name).strip().lower()
    return COUNTRIES.get(key)


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# --- field parsing -----------------------------------------------------------

LABELS = {
    "feature": "title",
    "description": "description_en",
    "issuing volume": "volume_raw",
    "issuing date": "issue_date_raw",
}
LABEL_RE = re.compile(r"^(feature|description|issuing volume|issuing date)\s*:\s*", re.I)


BLOCK = "\x00"


def text_blocks(content_box) -> list[str]:
    """Text of the content box split at block boundaries (p, div, br), h3 excluded.

    Text inside a block is joined with "" so labels split across tags
    ("I<strong>ssuing date") stay whole. Splitting at every block, not only <p>,
    catches labels that sit directly in a <div> (2023 Luxembourg).
    """
    box = BeautifulSoup(str(content_box), "html.parser")
    for h3 in box.find_all("h3"):
        h3.decompose()
    for tag in box.find_all(["p", "div", "br"]):
        tag.insert_before(BLOCK)
        tag.insert_after(BLOCK)
    return [t for t in (clean_text(part) for part in box.get_text("").split(BLOCK)) if t]


def parse_fields(content_box) -> tuple[dict, list[str]]:
    """Map labelled blocks to fields. Unlabelled blocks continue the previous field."""
    fields: dict[str, str] = {}
    orphans: list[str] = []
    current = None
    for text in text_blocks(content_box):
        m = LABEL_RE.match(text)
        if m:
            current = LABELS[m.group(1).lower()]
            fields[current] = text[m.end():].strip()
        elif current:
            fields[current] = f"{fields[current]} {text}".strip()
        else:
            orphans.append(text)
    return fields, orphans


VOLUME_RE = re.compile(r"^(?:max\.?\s+)?(\d[\d\s,.]*?)\s*(millions?)?\s*(?:coins)?$", re.I)


def parse_volume(raw: str | None) -> int | None:
    if not raw:
        return None
    m = VOLUME_RE.match(clean_text(raw))
    if not m:
        return None
    number, million = m.group(1).strip(), m.group(2)
    if million:
        try:
            return int(round(float(number.replace(" ", "").replace(",", ".")) * 1_000_000))
        except ValueError:
            return None
    digits = re.sub(r"[\s,.]", "", number)
    return int(digits) if digits.isdigit() else None


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
DAY_MONTH_YEAR_RE = re.compile(r"^(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?([a-z]+)\s+(\d{4})$", re.I)


def parse_date(raw: str | None) -> str | None:
    """ISO date at the precision the text supports: YYYY-MM-DD, YYYY-MM, or YYYY.

    Only a plain "[day] Month YEAR" gives month/day precision. Quarters, seasons,
    ranges and free text fall back to the year if exactly one year appears.
    """
    if not raw:
        return None
    text = clean_text(raw)
    m = DAY_MONTH_YEAR_RE.match(text)
    if m and m.group(2).lower() in MONTHS:
        day, month, year = m.group(1), MONTHS[m.group(2).lower()], m.group(3)
        return f"{year}-{month:02d}-{int(day):02d}" if day else f"{year}-{month:02d}"
    years = set(re.findall(r"\b(\d{4})\b", text))
    return years.pop() if len(years) == 1 else None


# --- ids ---------------------------------------------------------------------

SLUG_STOPWORDS = {
    "a", "an", "the", "of", "and", "in", "on", "for", "to", "at", "by", "with", "from",
    "anniversary", "series", "bundeslander", "federal", "states",
}


def slugify(title: str, max_words: int = 4) -> str:
    no_apostrophes = re.sub(r"(?<=\w)['\u2019](?=\w)", "", title.lower())  # "finland's" -> "finlands"
    ascii_ = unicodedata.normalize("NFKD", no_apostrophes).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_)
    kept = [w for w in words if w not in SLUG_STOPWORDS] or words
    return "-".join(kept[:max_words]) or "coin"


# --- page parsing ------------------------------------------------------------

def image_srcs(box) -> list[str]:
    return [img["src"].strip() for img in box.select(".coins img") if img.get("src", "").strip()]


def absolute_url(page: str, src: str) -> str:
    return requote_uri(urljoin(page, src))


def joint_variant_key(src: str) -> str:
    """Key for one national variant of a joint issue, derived from the image filename."""
    stem = re.sub(r"\.[a-z]+$", "", src.rsplit("/", 1)[-1], flags=re.I)
    stem = re.sub(r"^joint_comm_\d{4}_", "", stem)
    if re.search(r"comm_eu", stem, re.I):
        return "common"
    whole = normalize_country(re.sub(r"\d+$", "", stem))
    if whole:  # "San_Marino", "Austria1"
        return whole[1]
    base, _, suffix = stem.partition("_")
    country = normalize_country(base)
    if country:  # "Luxembourg_Face"
        return f"{country[1]}-{slugify(suffix, max_words=8)}"
    return slugify(stem, max_words=8)


def parse_page(html: str, year: int) -> tuple[list[dict], list[str]]:
    """Return (coins, warnings). Coins keep page order and carry no id yet."""
    url = page_url(year)
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if main is None:
        return [], [f"{year}: no <main> element"]
    coins, warnings = [], []
    for index, box in enumerate(main.select("div.box")):
        h3 = box.find("h3")
        country_raw = clean_text(h3.get_text(" ")) if h3 else ""
        country = normalize_country(country_raw)
        where = f"{year} #{index + 1} {country_raw!r}"
        if not country:
            warnings.append(f"{where}: unknown country")
            country = (country_raw, "")
        content = box.select_one(".content-box")
        fields, orphans = parse_fields(content) if content else ({}, [])
        for text in orphans:
            warnings.append(f"{where}: unlabelled paragraph {text[:60]!r}")
        srcs = image_srcs(box)
        if not srcs:
            warnings.append(f"{where}: no image")
        is_joint = country[1] == "eu"
        coin = {
            "year": year,
            "country": country[0],
            "country_code": country[1],
            "title": fields.get("title"),
            "description_en": fields.get("description_en"),
            "volume_raw": fields.get("volume_raw"),
            "volume": parse_volume(fields.get("volume_raw")),
            "issue_date_raw": fields.get("issue_date_raw"),
            "issue_date": parse_date(fields.get("issue_date_raw")),
            "image_source_url": None,
            "source_url": url,
            "is_joint_issue": is_joint,
        }
        if srcs:
            keys = [joint_variant_key(s) for s in srcs] if is_joint else []
            main_src = srcs[keys.index("common")] if "common" in keys else srcs[0]
            coin["image_source_url"] = absolute_url(url, main_src)
            if is_joint:
                coin["variant_image_sources"] = {
                    k: absolute_url(url, s) for k, s in zip(keys, srcs) if k != "common"
                }
            elif len(srcs) > 1:
                warnings.append(f"{where}: {len(srcs)} images, using the first")
        coins.append(coin)
    return coins, warnings


def count_boxes(html: str) -> int:
    main = BeautifulSoup(html, "html.parser").find("main")
    return len(main.select("div.box")) if main else 0
