import {
  buildHash, coinCountries, exportCollection, filterCoins, JOINT, mergeImport, parseHash, sortCoins, stats, thumbPath,
} from "./filter.js";
import {
  applyI18n, coinText, countryName, formatDate, formatNumber, getLocale, localeName, LOCALES, setLocale, t,
} from "./i18n.js";
import { createLocalStore, requestPersistence } from "./store.js";

const $ = (id) => document.getElementById(id);
const store = createLocalStore();

let coins = [];
let byId = new Map();
let owned = new Set();
let state = parseHash(location.hash);
const cards = new Map(); // id -> <li>

const flagSrc = (code) => `flags/${code}.svg`;

// --- boot ----------------------------------------------------------------------

async function boot() {
  setupLocale();
  applyI18n();
  try {
    const res = await fetch("data/coins.json");
    if (!res.ok) throw new Error(res.status);
    coins = sortCoins(await res.json());
  } catch {
    $("status").textContent = t("data.load_error");
    return;
  }
  byId = new Map(coins.map((c) => [c.id, c]));
  owned = await store.load();
  store.subscribe((next) => {
    owned = next;
    refreshOwned();
  });
  buildFilterOptions();
  buildCards();
  bindEvents();
  render();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}

function setupLocale() {
  const select = $("locale");
  if (LOCALES.length < 2) return;
  select.hidden = false;
  select.replaceChildren(...LOCALES.map((l) => new Option(localeName(l), l, false, l === getLocale())));
  select.addEventListener("change", () => {
    setLocale(select.value);
    location.reload();
  });
}

// --- filters -------------------------------------------------------------------

function buildFilterOptions() {
  const years = [...new Set(coins.map((c) => c.year))].sort((a, b) => b - a);
  $("year").replaceChildren(new Option(t("filter.all_years"), ""), ...years.map((y) => new Option(String(y), y)));

  const codes = [...new Set(coins.flatMap(coinCountries))].filter((c) => c !== JOINT);
  codes.sort((a, b) => countryName(a).localeCompare(countryName(b), t("lang.html")));
  $("country").replaceChildren(
    new Option(t("filter.all_countries"), ""),
    new Option(countryName(JOINT), JOINT),
    ...codes.map((c) => new Option(countryName(c), c)),
  );
}

function syncControls() {
  $("q").value = state.q;
  $("year").value = state.year ?? "";
  $("country").value = state.country ?? "";
  $("owned").value = state.owned;
}

function setState(patch, { replace = false } = {}) {
  state = { ...state, ...patch };
  const hash = buildHash(state) || location.pathname + location.search;
  if (replace) history.replaceState(null, "", hash);
  else history.pushState(null, "", hash);
  render();
}

// --- cards ---------------------------------------------------------------------

function buildCards() {
  const tpl = $("card-tpl").content;
  for (const coin of coins) {
    const li = tpl.firstElementChild.cloneNode(true);
    li.dataset.id = coin.id;
    const title = coinText(coin, "title").text;
    const img = li.querySelector(".thumb");
    img.src = thumbPath(coin.image) ?? "";
    li.querySelector(".flag").src = flagSrc(coin.country_code);
    li.querySelector(".card-country").textContent = countryName(coin.country_code);
    li.querySelector(".card-year").textContent = coin.year;
    li.querySelector(".card-title").textContent = title;
    li.querySelector(".card-open").setAttribute("aria-label", t("card.open", { title }));
    cards.set(coin.id, li);
    paintOwned(coin.id);
  }
}

function paintOwned(id) {
  const li = cards.get(id);
  const has = owned.has(id);
  li.classList.toggle("owned", has);
  const btn = li.querySelector(".toggle");
  btn.setAttribute("aria-pressed", String(has));
  const label = has ? t("toggle.remove") : t("toggle.add");
  btn.setAttribute("aria-label", label);
  btn.title = label;
}

function render() {
  syncControls();
  const list = filterCoins(coins, state, owned, countryName);
  $("grid").replaceChildren(...list.map((c) => cards.get(c.id)));
  $("count").textContent = t("count", { n: list.length });
  $("empty").hidden = list.length > 0;
  renderProgress();
  if (state.coin && byId.has(state.coin)) {
    if (!$("detail").open || detailCoin?.id !== state.coin) openDetail(byId.get(state.coin));
  }
  else if ($("detail").open) $("detail").close();
}

function renderProgress() {
  const n = owned.size ? coins.filter((c) => owned.has(c.id)).length : 0;
  $("progress-text").textContent = t("progress", { owned: n, total: coins.length });
  $("progress-fill").style.width = `${(n / coins.length) * 100}%`;
}

async function toggleOwned(id) {
  if (owned.has(id)) owned.delete(id);
  else owned.add(id);
  await store.save(owned);
  refreshOwned(id);
}

function refreshOwned(id) {
  for (const key of id ? [id] : cards.keys()) paintOwned(key);
  if (state.owned !== "all") render();
  else renderProgress();
  if ($("detail").open) paintDetailToggle();
  if ($("stats").open) renderStats();
}

// --- detail --------------------------------------------------------------------

let detailCoin = null;

function openDetail(coin) {
  detailCoin = coin;
  const title = coinText(coin, "title").text;
  const desc = coinText(coin, "description");
  $("d-image").src = coin.image ?? "";
  $("d-image").alt = title;
  $("d-flag").src = flagSrc(coin.country_code);
  $("d-country").textContent = countryName(coin.country_code);
  $("d-year").textContent = coin.year;
  $("d-title").textContent = title;
  $("d-volume").textContent = coin.volume != null
    ? formatNumber(coin.volume)
    : coin.is_joint_issue ? t("detail.volume_varies") : coin.volume_raw ?? "";
  const date = formatDate(coin.issue_date);
  const preciseRaw = /^(\d{1,2} )?[A-Z][a-z]+ \d{4}$/.test(coin.issue_date_raw ?? "");
  $("d-date").textContent = coin.issue_date_raw && !preciseRaw ? `${date}（${coin.issue_date_raw}）` : date;
  $("d-fallback").hidden = !desc.fallback;
  $("d-description").textContent = desc.text;
  $("d-description").lang = desc.fallback ? "en" : t("lang.html");
  $("d-source").href = coin.source_url;

  const variants = Object.entries(coin.variant_images || {});
  $("d-variants").hidden = variants.length === 0;
  $("d-variants-title").textContent = t("detail.variants", { n: variants.length });
  $("d-variant-list").replaceChildren(...variants.map(([key, v]) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = v.image ?? v.image_source_url;
    a.target = "_blank";
    const img = document.createElement("img");
    img.src = thumbPath(v.image) ?? v.image_source_url;
    img.loading = "lazy";
    img.alt = "";
    const cap = document.createElement("span");
    const code = key.split("-")[0];
    cap.textContent = key.includes("-") ? `${countryName(code)}（${key.slice(code.length + 1)}）` : countryName(code);
    a.append(img, cap);
    li.append(a);
    return li;
  }));
  paintDetailToggle();
  if (!$("detail").open) $("detail").showModal();
  $("detail").scrollTop = 0;
}

function paintDetailToggle() {
  const has = owned.has(detailCoin.id);
  const btn = $("d-toggle");
  btn.setAttribute("aria-pressed", String(has));
  btn.textContent = has ? `✓ ${t("toggle.owned")}` : t("toggle.add");
}

// --- stats ---------------------------------------------------------------------

function renderStats() {
  const s = stats(coins, owned);
  $("s-owned").textContent = s.owned;
  $("s-total").textContent = s.total;
  $("s-fill").style.width = `${(s.owned / s.total) * 100}%`;
  const countries = [...s.byCountry].sort((a, b) => countryName(a[0]).localeCompare(countryName(b[0]), t("lang.html")));
  fillTable($("s-country"), countries, (code) => countryName(code), (code) => ({ country: code, year: null }));
  const years = [...s.byYear].sort((a, b) => b[0] - a[0]);
  fillTable($("s-year"), years, (y) => String(y), (y) => ({ year: y, country: null }));
}

function fillTable(table, rows, label, toFilter) {
  const head = document.createElement("thead");
  head.innerHTML = "<tr><th scope=col></th><th scope=col></th><th scope=col class=num></th></tr>";
  const ths = head.querySelectorAll("th");
  ["stats.col.name", "stats.col.progress", "stats.col.count"].forEach((k, i) => (ths[i].textContent = t(k)));
  const body = document.createElement("tbody");
  for (const [key, row] of rows) {
    const tr = document.createElement("tr");
    tr.tabIndex = 0;
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = label(key);
    const bar = document.createElement("td");
    bar.innerHTML = '<span class="meter" aria-hidden="true"><span></span></span>';
    bar.querySelector("span span").style.width = `${(row.owned / row.total) * 100}%`;
    const count = document.createElement("td");
    count.className = "num";
    count.textContent = `${row.owned} / ${row.total}`;
    tr.append(name, bar, count);
    const go = () => {
      $("stats").close();
      setState({ ...toFilter(key), owned: "all", q: "", coin: null });
    };
    tr.addEventListener("click", go);
    tr.addEventListener("keydown", (e) => e.key === "Enter" && go());
    body.append(tr);
  }
  table.replaceChildren(head, body);
}

// --- import / export -----------------------------------------------------------

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 6000);
}

function exportFile() {
  const data = exportCollection(owned);
  const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `euros-collection-${data.exported_at.slice(0, 10)}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function importFile(file) {
  try {
    const data = JSON.parse(await file.text());
    const result = mergeImport(owned, data, new Set(byId.keys()));
    owned = result.owned;
    await store.save(owned);
    refreshOwned();
    let msg = t("data.imported", { added: result.added, total: coins.filter((c) => owned.has(c.id)).length });
    if (result.unknown.length) msg += " " + t("data.imported_unknown", { n: result.unknown.length });
    toast(msg);
    requestPersistence();
  } catch {
    toast(t("data.import_error"));
  }
}

// --- events --------------------------------------------------------------------

function bindEvents() {
  let typing;
  $("q").addEventListener("input", () => {
    clearTimeout(typing);
    typing = setTimeout(() => setState({ q: $("q").value.trim(), coin: null }, { replace: true }), 150);
  });
  $("year").addEventListener("change", () => setState({ year: Number($("year").value) || null, coin: null }));
  $("country").addEventListener("change", () => setState({ country: $("country").value || null, coin: null }));
  $("owned").addEventListener("change", () => setState({ owned: $("owned").value, coin: null }));
  $("reset").addEventListener("click", () => setState({ year: null, country: null, owned: "all", q: "", coin: null }));

  $("grid").addEventListener("click", (e) => {
    const li = e.target.closest(".card");
    if (!li) return;
    if (e.target.closest(".toggle")) {
      toggleOwned(li.dataset.id);
      requestPersistence();
    } else if (e.target.closest(".card-open")) {
      setState({ coin: li.dataset.id });
    }
  });
  $("d-toggle").addEventListener("click", () => toggleOwned(detailCoin.id));
  // The detail dialog follows state.coin: closing it (Esc, button, backdrop) clears
  // the coin from the URL and render() closes it. Using the async "close" event
  // instead would race with a new #coin= navigation.
  const closeDetail = () => setState({ coin: null }, { replace: true });
  $("detail").addEventListener("cancel", (e) => {
    e.preventDefault();
    closeDetail();
  });
  for (const dialog of document.querySelectorAll("dialog")) {
    dialog.addEventListener("click", (e) => {
      if (e.target !== dialog && !e.target.closest("[data-close]")) return;
      if (dialog.id === "detail") closeDetail();
      else dialog.close();
    });
  }
  $("stats-open").addEventListener("click", () => {
    renderStats();
    $("stats").showModal();
  });
  $("export").addEventListener("click", exportFile);
  $("import").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) importFile(file);
    e.target.value = "";
  });
  window.addEventListener("popstate", () => {
    state = parseHash(location.hash);
    render();
  });
}

boot();
