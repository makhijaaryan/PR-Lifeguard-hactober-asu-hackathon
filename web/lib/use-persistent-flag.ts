import { useCallback, useSyncExternalStore } from "react";

const EVENT = "pr-lifeguard:storage";

function read(key: string, fallback: boolean) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v === "1";
  } catch {
    return fallback; // storage blocked (private mode etc.)
  }
}

/** A boolean remembered in localStorage. Server render and storage failures use `fallback`. */
export function usePersistentFlag(key: string, fallback: boolean): [boolean, (v: boolean) => void] {
  const subscribe = useCallback((cb: () => void) => {
    window.addEventListener(EVENT, cb);
    window.addEventListener("storage", cb);
    return () => {
      window.removeEventListener(EVENT, cb);
      window.removeEventListener("storage", cb);
    };
  }, []);
  const value = useSyncExternalStore(
    subscribe,
    () => read(key, fallback),
    () => fallback,
  );
  const set = useCallback(
    (v: boolean) => {
      try {
        localStorage.setItem(key, v ? "1" : "0");
      } catch {}
      window.dispatchEvent(new Event(EVENT));
    },
    [key],
  );
  return [value, set];
}
