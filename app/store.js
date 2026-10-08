// Collection storage. The app only uses load / save / subscribe, so a remote
// backend (accounts + sync) can replace this module later without UI changes.
// The stored shape matches the export file: {owned: string[], updated_at}.

const KEY = "euros.collection.v1";

export function createLocalStore(storage = globalThis.localStorage) {
  const listeners = new Set();

  function read() {
    try {
      const data = JSON.parse(storage.getItem(KEY));
      return new Set(Array.isArray(data?.owned) ? data.owned.filter((x) => typeof x === "string") : []);
    } catch {
      return new Set();
    }
  }

  // Other tabs of the app write to the same storage.
  globalThis.addEventListener?.("storage", (e) => {
    if (e.key === KEY) for (const fn of listeners) fn(read());
  });

  return {
    /** @returns {Promise<Set<string>>} */
    async load() {
      return read();
    },
    /** @param {Set<string>} owned */
    async save(owned) {
      storage.setItem(KEY, JSON.stringify({ owned: [...owned].sort(), updated_at: new Date().toISOString() }));
    },
    /** @param {(owned: Set<string>) => void} fn  called when another tab changes the collection */
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

/** Ask the browser not to evict our storage under pressure. Best effort. */
export async function requestPersistence() {
  try {
    return (await navigator.storage?.persist?.()) ?? false;
  } catch {
    return false;
  }
}
