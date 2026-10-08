# euros — €2 commemorative coin collection

## Product decisions

- Product: a PWA for tracking a personal collection of €2 commemorative coins. Works offline after first load.
- Hosting: GitHub Pages, free tier only. Static files only: no server, no database, no paid services.
- Repository is public. Everything committed is public.
- Data source: ECB pages `https://www.ecb.europa.eu/euro/coins/comm/html/comm_{YEAR}.en.html` (2004 onwards).
- ECB terms allow reuse if content stays accurate and the ECB is cited as source. Show "Source: European Central Bank" in the app. State our changes (parsed fields, Chinese translation) as ours.

## Privacy rules

- `legacy/` and `private/` are gitignored. Never commit, copy, or quote their content into tracked files.
- Collection status (which coins the user owns) is private. It lives in `private/collection.json`, never in `data/`.
- The future PWA keeps collection status on the device (e.g. localStorage/IndexedDB), with import/export of the same JSON shape. Do not publish it.

## Layout

| Path | Content |
|---|---|
| `scraper/ecb.py` | Pure parsing: page → coin dicts, volume/date parsing, slugs |
| `scraper/scrape.py` | CLI: fetch pages, archive HTML, download images, write `data/coins.json` |
| `scripts/migrate_legacy.py` | xlsx → `description_zh` and `private/collection.json` |
| `scripts/validate.py` | Count and field checks against `data/raw/` and xlsx |
| `data/coins.json` | Public dataset, one object per coin, ordered by year then ECB page order |
| `data/images/{year}/{id}.{ext}` | Coin images; joint-issue variants in `data/images/{year}/{id}/{key}.{ext}` |
| `data/raw/comm_{year}.en.html` | Archived ECB pages, used as fallback when the ECB is unreachable |

## Commands

```sh
uv run --with-requirements scraper/requirements.txt python -m scraper.scrape            # all years
uv run --with-requirements scraper/requirements.txt python -m scraper.scrape --offline  # re-parse data/raw only
uv run --with-requirements scraper/requirements.txt python scripts/migrate_legacy.py
uv run --with-requirements scraper/requirements.txt python scripts/validate.py
uv run --with-requirements scraper/requirements.txt python -m pytest -q tests
```

System Python is 3.9 without bs4; always run through `uv`.

## Scraper rules

- Locate fields by label text (`Feature:`, `Description:`, `Issuing volume:`, `Issuing date:`) over each `<p>`'s full text, never by position. ECB markup splits labels across tags and spreads descriptions over several `<p>`.
- One coin per `main div.box`. Country from its `<h3>`.
- 2 s delay between requests; User-Agent names the project and repo URL.
- Incremental: a coin keeps its bytes and `scraped_at` unless a content field changed. Images download only when missing or when their source URL changed.

## Data schema (`data/coins.json`)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `{year}-{country_code}-{slug}`; slug = first 4 non-stopwords of the title. Generated once, then reused (matched by year+country+title, else unique image URL). No manual id list. |
| `year` | int | Page year |
| `country` | string | Canonical English name (`Vatican City`, `Netherlands`, `Euro area countries`) |
| `country_code` | string | ISO 3166-1 alpha-2, lowercase (`gr` for Greece); `eu` for joint issues |
| `title` | string | ECB "Feature" |
| `description_en` | string | ECB "Description" |
| `description_zh` | string \| null | From legacy xlsx; scraper preserves it |
| `volume_raw` / `volume` | string / int \| null | `volume` null when not a single number |
| `issue_date_raw` / `issue_date` | string / string \| null | `YYYY-MM-DD`, `YYYY-MM`, or `YYYY` (quarters, seasons, ranges) |
| `image` | string \| null | Local path relative to repo root |
| `image_source_url` | string | ECB image URL |
| `variant_images` | object | Joint issues only: `{key: {image, image_source_url}}`, key = country code (e.g. `lu-face` for extra variants) |
| `source_url` | string | ECB year page |
| `is_joint_issue` | bool | `true` for "Euro area countries" coins |
| `scraped_at` | string | UTC time of the last content change |

`private/collection.json`: `{"source", "exported_at", "owned": [id, ...], "unmatched_owned": [...]}`.

## Joint issues

- Joint issues (2007, 2009, 2012, 2015, 2022) stay one record each, as on the ECB page. No per-country split.
- UI: show the EU flag for joint issues, not a national flag.
- Country filter: a joint issue matches a country if the country is in `variant_images` (key before any `-` suffix, e.g. `lu-face` → `lu`).
- Known gap: the ECB 2022 page has no German variant image, so `de` is missing from `2022-eu-35-years-erasmus-programme`.
