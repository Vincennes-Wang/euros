import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  buildHash, coinCountries, exportCollection, filterCoins, mergeImport, parseHash, sortCoins, stats, thumbPath,
} from "../../app/filter.js";

const coins = JSON.parse(readFileSync(new URL("../../data/coins.json", import.meta.url)));
const byId = (id) => coins.find((c) => c.id === id);
const none = new Set();

test("thumbPath maps images to webp thumbnails", () => {
  assert.equal(thumbPath("data/images/2009/x/lu-face.jpg"), "data/thumbs/2009/x/lu-face.webp");
  assert.equal(thumbPath(null), null);
});

test("joint issues belong to eu and every participating country", () => {
  const joint = byId("2009-eu-10th-economic-monetary-union");
  const codes = coinCountries(joint);
  assert.equal(codes[0], "eu");
  assert.ok(codes.includes("lu"));
  assert.equal(codes.filter((c) => c === "lu").length, 1, "lu and lu-face collapse to lu");
  assert.deepEqual(coinCountries(byId("2004-gr-olympic-games-athens-2004")), ["gr"]);
});

test("country filter includes joint issues the country took part in", () => {
  const fr = filterCoins(coins, { country: "fr" }, none);
  const joint = fr.filter((c) => c.is_joint_issue).map((c) => c.year).sort();
  assert.deepEqual(joint, [2007, 2009, 2012, 2015, 2022]);
  assert.ok(fr.every((c) => c.country_code === "fr" || c.is_joint_issue));
  // Monaco never took part in a joint issue on the ECB pages.
  assert.ok(filterCoins(coins, { country: "mc" }, none).every((c) => !c.is_joint_issue));
  // Known gap: no German variant on the 2022 page.
  assert.ok(!filterCoins(coins, { country: "de", year: 2022 }, none).some((c) => c.is_joint_issue));
});

test("year, owned and text filters combine", () => {
  const owned = new Set(["2004-gr-olympic-games-athens-2004"]);
  assert.equal(filterCoins(coins, { year: 2004 }, none).length, 6);
  assert.deepEqual(filterCoins(coins, { year: 2004, owned: "owned" }, owned).map((c) => c.id), [...owned]);
  assert.equal(filterCoins(coins, { year: 2004, owned: "missing" }, owned).length, 5);
  assert.deepEqual(filterCoins(coins, { year: 2004, q: "athens olympic" }, none).map((c) => c.id), ["2004-gr-olympic-games-athens-2004"]);
  // Search matches Chinese descriptions and localized country names.
  assert.ok(filterCoins(coins, { q: "梵蒂冈" }, none).length > 0);
  assert.ok(filterCoins(coins, { q: "希腊" }, none, (c) => (c === "gr" ? "希腊" : c)).some((c) => c.country_code === "gr"));
});

test("sortCoins puts newest year first and keeps page order within a year", () => {
  const sorted = sortCoins(coins);
  assert.equal(sorted[0].year, 2025);
  const y2004 = sorted.filter((c) => c.year === 2004).map((c) => c.id);
  assert.deepEqual(y2004, coins.filter((c) => c.year === 2004).map((c) => c.id));
});

test("stats count each coin once", () => {
  const owned = new Set(["2015-eu-30th-eu-flag", "2004-gr-olympic-games-athens-2004", "not-a-coin"]);
  const s = stats(coins, owned);
  assert.equal(s.total, 504);
  assert.equal(s.owned, 2);
  assert.deepEqual(s.byCountry.get("eu"), { total: 5, owned: 1 });
  assert.equal([...s.byCountry.values()].reduce((a, r) => a + r.total, 0), 504);
  assert.equal(s.byYear.get(2004).total, 6);
});

test("mergeImport adds ids, keeps unknown ones and rejects bad files", () => {
  const known = new Set(coins.map((c) => c.id));
  const r = mergeImport(new Set(["a"]), { owned: ["a", "2004-gr-olympic-games-athens-2004", "future-id"] }, known);
  assert.equal(r.added, 2);
  assert.deepEqual([...r.owned].sort(), ["2004-gr-olympic-games-athens-2004", "a", "future-id"]);
  assert.deepEqual(r.unknown, ["a", "future-id"]);
  assert.throws(() => mergeImport(new Set(), { owned: "x" }, known));
  assert.throws(() => mergeImport(new Set(), null, known));
});

test("exportCollection round-trips through mergeImport", () => {
  const out = exportCollection(new Set(["b", "a"]), new Date("2026-10-08T12:00:00.123Z"));
  assert.deepEqual(out, { source: "euros-pwa", exported_at: "2026-10-08T12:00:00Z", owned: ["a", "b"] });
  assert.deepEqual([...mergeImport(new Set(), out, new Set()).owned], ["a", "b"]);
});

test("hash state round-trips", () => {
  const state = { year: 2015, country: "fr", owned: "missing", q: "rome 条约", coin: null };
  assert.deepEqual(parseHash(buildHash(state)), state);
  assert.equal(buildHash({ owned: "all" }), "");
  assert.deepEqual(parseHash("#year=abc&owned=bogus"), { year: null, country: null, owned: "all", q: "", coin: null });
});
