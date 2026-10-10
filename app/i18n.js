// UI strings and locale-aware formatting.
// To add a language: add an entry to MESSAGES with the same keys. The language
// switcher appears automatically when more than one locale exists. Coin text
// falls back to English when the dataset has no `<field>_<locale>` value.

const MESSAGES = {
  zh: {
    "lang.name": "中文",
    "lang.html": "zh-CN",
    "app.title": "€2 纪念币收藏",
    "filter.search": "搜索标题、描述、国家",
    "filter.year": "年份",
    "filter.country": "国家",
    "filter.all_years": "全部年份",
    "filter.all_countries": "全部国家",
    "filter.stars": "稀有度",
    "filter.all_stars": "全部稀有度",
    "stars.option": "{n} 星 {stars}",
    "stars.label": "稀有度 {n} 星（满分 5 星）",
    "filter.reset": "清除筛选",
    "count": "{n} 枚",
    "empty": "没有符合条件的纪念币。",
    "empty.mine": "还没有收藏。点击硬币右上角的圆圈即可标记为已收藏。",
    "view.label": "视图",
    "view.all": "全部硬币",
    "view.mine": "我的收藏（{n}）",
    "pager.label": "分页",
    "pager.prev": "上一页",
    "pager.next": "下一页",
    "pager.page": "第 {n} 页",
    "pager.status": "第 {page} / {pages} 页",
    "progress": "已收藏 {owned} / {total}",
    "card.open": "查看详情：{title}",
    "toggle.add": "标记为已收藏",
    "toggle.remove": "取消收藏",
    "toggle.owned": "已收藏",
    "toggle.not_owned": "未收藏",
    "detail.close": "关闭",
    "detail.volume": "发行量",
    "detail.date": "发行日期",
    "detail.rarity": "稀有度",
    "detail.rarity_note": "按发行量估算",
    "detail.rarity_none": "不评级（无单一发行量）",
    "detail.country": "发行国",
    "detail.description": "设计说明",
    "detail.english_only": "暂无中文翻译，显示英文原文。",
    "detail.variants": "各国版本（{n}）",
    "detail.joint_note": "共同发行币：欧元区国家发行同一设计，国名和铭文各不相同。",
    "detail.source": "ECB 原始页面",
    "detail.volume_varies": "各国不同",
    "stats.title": "收藏统计",
    "stats.overall": "总进度",
    "stats.by_country": "按国家",
    "stats.by_year": "按年份",
    "stats.col.name": "名称",
    "stats.col.progress": "进度",
    "stats.col.count": "已收藏 / 总数",
    "stats.filter_hint": "点击一行可筛选",
    "data.export": "导出收藏",
    "data.import": "导入收藏",
    "data.imported": "已导入：新增 {added} 枚，共 {total} 枚已收藏。",
    "data.imported_unknown": "{n} 个编号不在当前数据中，已保留。",
    "data.import_error": "导入失败：文件格式不正确。",
    "data.load_error": "数据加载失败，请检查网络后刷新。",
    "footer.privacy": "收藏记录只保存在本设备的浏览器中，不会上传。清除浏览器数据会丢失记录，请定期导出备份。",
    "footer.source": "硬币数据和图片来源：欧洲中央银行（European Central Bank）。中文翻译和字段整理为本站所加。",
    "footer.flags": "国旗图标：flag-icons（MIT 许可）。",
    "joint": "欧元区共同发行",
  },
};

const COUNTRY_NAMES = {
  zh: {
    ad: "安道尔", at: "奥地利", be: "比利时", bg: "保加利亚", cy: "塞浦路斯", de: "德国",
    ee: "爱沙尼亚", es: "西班牙", eu: "欧元区共同发行", fi: "芬兰", fr: "法国", gr: "希腊",
    hr: "克罗地亚", ie: "爱尔兰", it: "意大利", lt: "立陶宛", lu: "卢森堡", lv: "拉脱维亚",
    mc: "摩纳哥", mt: "马耳他", nl: "荷兰", pt: "葡萄牙", si: "斯洛文尼亚", sk: "斯洛伐克",
    sm: "圣马力诺", va: "梵蒂冈",
  },
};

const DATE_FORMATS = {
  zh: {
    day: (y, m, d) => `${y}年${m}月${d}日`,
    month: (y, m) => `${y}年${m}月`,
    year: (y) => `${y}年`,
  },
};

const STORAGE_KEY = "euros.locale";
export const LOCALES = Object.keys(MESSAGES);
let locale = pickLocale();

function pickLocale() {
  const saved = globalThis.localStorage?.getItem(STORAGE_KEY);
  if (saved && MESSAGES[saved]) return saved;
  const nav = (globalThis.navigator?.languages || []).map((l) => l.slice(0, 2));
  return nav.find((l) => MESSAGES[l]) || LOCALES[0];
}

export function getLocale() {
  return locale;
}

export function setLocale(next) {
  if (!MESSAGES[next]) return;
  locale = next;
  globalThis.localStorage?.setItem(STORAGE_KEY, next);
}

export function localeName(l) {
  return MESSAGES[l]?.["lang.name"] ?? l;
}

export function t(key, vars = {}) {
  const s = MESSAGES[locale][key] ?? MESSAGES[LOCALES[0]][key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

export function countryName(code) {
  return COUNTRY_NAMES[locale]?.[code] ?? code.toUpperCase();
}

/** Localized coin field: `<field>_<locale>`, else English. Returns {text, fallback}. */
export function coinText(coin, field) {
  const own = coin[`${field}_${locale}`];
  if (own) return { text: own, fallback: false };
  const en = coin[`${field}_en`] ?? coin[field];
  return { text: en ?? "", fallback: locale !== "en" };
}

/** Format an ISO date of variable precision (YYYY, YYYY-MM, YYYY-MM-DD). */
export function formatDate(iso) {
  if (!iso) return "";
  const f = DATE_FORMATS[locale] ?? DATE_FORMATS.zh;
  const [y, m, d] = iso.split("-").map(Number);
  return d ? f.day(y, m, d) : m ? f.month(y, m) : f.year(y);
}

export function formatNumber(n) {
  return new Intl.NumberFormat(t("lang.html")).format(n);
}

/** Fill every [data-i18n] text and [data-i18n-attr="attr:key,..."] attribute under root. */
export function applyI18n(root = document) {
  document.documentElement.lang = t("lang.html");
  for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of root.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":");
      el.setAttribute(attr, t(key));
    }
  }
}
