@~/vibe-playbook/00_教练规则.md
@~/vibe-playbook/02_默认技术栈与免费方案.md
@~/vibe-playbook/05_本地AI模型方案.md

## 协作规则
- 先给计划（Plan mode），用户确认后再写代码。
- 开工前读 `~/vibe-playbook/03_经验日志.md`，避免重复踩坑。
- 实际检查网页、API、文件、模型输出，不凭猜测写代码。
- 每个阶段结束时运行验证，报告结果。
- 小步提交。不提交密钥、`.env`、`legacy/`、`private/`、模型文件和个人数据。
- 每次工作结束前：按下面的格式更新 `PROGRESS.md`，提交并推送，然后运行 `git status -sb` 确认没有未推送的提交。

## 交接清单
以下情况，回复末尾必须输出交接清单：
- 每次工作结束，推送完成后。
- 需要用户在 GitHub 网页、手机、账号或系统设置里操作时（例如开启 Pages、添加 Secrets、真机测试、授权）。
- 遇到无法自己解决的报错，或需要用户做决策时。
- 同一个问题修了两次仍未解决时，建议用户回 Claude.ai。

格式：

### 交接清单
- 推送状态：<已推送，最新提交 xxxxxxx / 未推送，原因>
- 需要你做：
  1. <具体操作，写明在哪里点什么；没有就写“无”>
- 发给 Claude.ai（可选，只在需要第二意见时填写；否则写“无”）：
  > 看看进度：<仓库地址>。<需要诊断的问题或待做的决策>

## PROGRESS.md 固定格式
```markdown
# PROGRESS
- 状态：<进行中 / 已完成 / 暂停>
- 当前阶段：<阶段编号和名称>
- 累计用时：<小时>
- 线上地址：<GitHub Pages 链接，没有就留空>

## 最近一次工作（<日期>）
- 完成：
- 验证结果：<运行了什么检查，结果如何>

## 下次从这里继续
1.

## 未解决问题
-
```

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

## Front end

- No framework, no build step, no npm dependencies: plain HTML, ES modules, CSS. What is in `main` is what Pages serves.
- GitHub Pages serves the repo root of `main` (`.nojekyll`). All paths are relative; the site lives under `/euros/`.
- UI language: Chinese only for now. All UI strings live in `app/i18n.js`; adding a locale = adding one dictionary. Coin text uses `<field>_<locale>` and falls back to English with a visible note.
- Collection storage: `localStorage` key `euros.collection.v1`, shape `{owned: [id], updated_at}` (same `owned` shape as export files and `private/collection.json`). Only `app/store.js` touches storage, through `load`/`save`/`subscribe`, so a remote backend with accounts can replace it later.
- Grid is paginated, 48 coins per page (`PAGE_SIZE` in `app/filter.js`); page is in the URL hash; filter changes reset to page 1. Header toggle "全部硬币 / 我的收藏" sets the owned filter.
- Joint issues show the EU flag. Country filter includes joint issues (see below). Stats count each coin once (joint issues under `eu`).
- Flags: `flags/*.svg` from flag-icons (MIT, `flags/LICENSE`).
- Offline (`sw.js`): shell and `coins.json` stale-while-revalidate; thumbnails and flags precached (~7 MB); full images cached on first view. Bump the cache names in `sw.js` only when the caching scheme changes.
- Owned state uses brass: light `#8a6a1f` (white check, 5.05:1), dark `#d4a948` (dark check, 7.85:1). Unowned coins stay in full color (user decision 2026-10-09).
- Meter colors are validated with the dataviz palette script: light fill `#256abf` / track `#cde2fb`, dark fill `#3987e5` / track `#104281`.

## Layout

| Path | Content |
|---|---|
| `index.html`, `app/` | PWA: `main.js` (DOM), `filter.js` (pure logic), `i18n.js`, `store.js`, `styles.css` |
| `sw.js`, `manifest.webmanifest`, `icons/` | Service worker, manifest, app icons |
| `scripts/make_thumbs.py` | 256 px WebP thumbnails: `data/images/...jpg` → `data/thumbs/...webp` |
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
uv run --with-requirements scraper/requirements.txt python scripts/make_thumbs.py     # after every scrape
uv run --with-requirements scraper/requirements.txt python -m pytest -q tests
node --test tests/js/                                                                  # front-end logic
```

Local preview under the same path as Pages: serve a directory that contains a symlink `euros -> <repo>` with `python3 -m http.server`, then open `http://127.0.0.1:8000/euros/`.

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
| `description_zh` | string \| null | 371 from the legacy xlsx (cached Google Translate); the rest translated by Claude on 2026-10-08. The scraper preserves it; new coins need a translation pass. |
| `volume_raw` / `volume` | string / int \| null | `volume` null when not a single number |
| `issue_date_raw` / `issue_date` | string / string \| null | `YYYY-MM-DD`, `YYYY-MM`, or `YYYY` (quarters, seasons, ranges) |
| `image` | string \| null | Local path relative to repo root |
| `image_source_url` | string | ECB image URL |
| `variant_images` | object | Joint issues only: `{key: {image, image_source_url}}`, key = country code (e.g. `lu-face` for extra variants) |
| `source_url` | string | ECB year page |
| `is_joint_issue` | bool | `true` for "Euro area countries" coins |
| `scraped_at` | string | UTC time of the last content change |

`private/collection.json`: `{"source", "exported_at", "owned": [id, ...], "unmatched_owned": [...]}`.

## Rarity stars

- Our own estimate from `volume`, not ECB data. Computed in the front end (`rarityStars` in `app/filter.js`), never written to `coins.json`.
- Lower bound inclusive: < 100,000 = 5★; 100,000–299,999 = 4★; 300,000–999,999 = 3★; 1,000,000–9,999,999 = 2★; ≥ 10,000,000 = 1★.
- `volume` null → no rating (today: the 5 joint issues).
- UI: stars on cards and in the detail sheet with the note "按发行量估算"; star filter in the hash as `stars=1..5`.

## Joint issues

- Joint issues (2007, 2009, 2012, 2015, 2022) stay one record each, as on the ECB page. No per-country split.
- UI: show the EU flag for joint issues, not a national flag.
- Country filter: a joint issue matches a country if the country is in `variant_images` (key before any `-` suffix, e.g. `lu-face` → `lu`).
- Known gap: the ECB 2022 page has no German variant image, so `de` is missing from `2022-eu-35-years-erasmus-programme`.
