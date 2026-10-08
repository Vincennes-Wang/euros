// Pure data logic: no DOM, no storage. Tested with `node --test tests/js`.

export const JOINT = "eu";

/** Thumbnail path for an image path: data/images/a/b.jpg -> data/thumbs/a/b.webp */
export function thumbPath(image) {
  return image ? image.replace(/^data\/images\//, "data/thumbs/").replace(/\.[^./]+$/, ".webp") : null;
}

/** Country codes a coin belongs to. Joint issues: "eu" plus every participating country. */
export function coinCountries(coin) {
  if (coin.country_code !== JOINT) return [coin.country_code];
  const codes = Object.keys(coin.variant_images || {}).map((k) => k.split("-")[0]);
  return [JOINT, ...new Set(codes)];
}

function normalize(s) {
  return (s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
}

/**
 * Filter coins.
 * @param {object[]} coins
 * @param {{year?: number|null, country?: string|null, owned?: "all"|"owned"|"missing", q?: string}} f
 * @param {Set<string>} owned
 * @param {(code: string) => string} countryName  localized name, used by the text search
 */
export function filterCoins(coins, f, owned, countryName = (c) => c) {
  const q = normalize(f.q).trim();
  const terms = q ? q.split(/\s+/) : [];
  return coins.filter((c) => {
    if (f.year && c.year !== f.year) return false;
    if (f.country && !coinCountries(c).includes(f.country)) return false;
    if (f.owned === "owned" && !owned.has(c.id)) return false;
    if (f.owned === "missing" && owned.has(c.id)) return false;
    if (terms.length) {
      const hay = normalize(
        [c.id, c.title, c.description_en, c.description_zh, c.country, countryName(c.country_code)].join(" "),
      );
      if (!terms.every((t) => hay.includes(t))) return false;
    }
    return true;
  });
}

/** Newest year first; ECB page order within a year (the input order). */
export function sortCoins(coins) {
  return coins.map((c, i) => [c, i]).sort((a, b) => b[0].year - a[0].year || a[1] - b[1]).map(([c]) => c);
}

/**
 * Collection progress. Each coin counts once: joint issues are grouped under "eu",
 * not under every participating country.
 */
export function stats(coins, owned) {
  const byCountry = new Map();
  const byYear = new Map();
  let n = 0;
  for (const c of coins) {
    const has = owned.has(c.id) ? 1 : 0;
    n += has;
    for (const [map, key] of [[byCountry, c.country_code], [byYear, c.year]]) {
      const row = map.get(key) || { total: 0, owned: 0 };
      row.total += 1;
      row.owned += has;
      map.set(key, row);
    }
  }
  return { total: coins.length, owned: n, byCountry, byYear };
}

/**
 * Merge an imported collection file into the current set.
 * Accepts {owned: string[]} (same shape as private/collection.json and our export).
 * Unknown ids are kept, so data from a newer dataset is not lost, and reported.
 * @returns {{owned: Set<string>, added: number, unknown: string[]}}
 */
export function mergeImport(current, data, knownIds) {
  if (!data || !Array.isArray(data.owned) || !data.owned.every((x) => typeof x === "string")) {
    throw new Error("invalid collection file");
  }
  const next = new Set(current);
  let added = 0;
  for (const id of data.owned) {
    if (!next.has(id)) {
      next.add(id);
      added += 1;
    }
  }
  const unknown = data.owned.filter((id) => !knownIds.has(id));
  return { owned: next, added, unknown };
}

/** Serialize the collection in the shared file format. */
export function exportCollection(owned, now = new Date()) {
  return { source: "euros-pwa", exported_at: now.toISOString().replace(/\.\d+Z$/, "Z"), owned: [...owned].sort() };
}

/** URL hash <-> view state. */
export function parseHash(hash) {
  const p = new URLSearchParams(hash.replace(/^#/, ""));
  const year = Number(p.get("year")) || null;
  const owned = ["owned", "missing"].includes(p.get("owned")) ? p.get("owned") : "all";
  return { year, country: p.get("country") || null, owned, q: p.get("q") || "", coin: p.get("coin") || null };
}

export function buildHash(state) {
  const p = new URLSearchParams();
  if (state.year) p.set("year", state.year);
  if (state.country) p.set("country", state.country);
  if (state.owned && state.owned !== "all") p.set("owned", state.owned);
  if (state.q) p.set("q", state.q);
  if (state.coin) p.set("coin", state.coin);
  const s = p.toString();
  return s ? `#${s}` : "";
}
