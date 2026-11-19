"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

const KEY = "lendflow-theme";
type Theme = "light" | "dark";

/** Runs in <head> before first paint, so a saved or system dark theme never flashes white. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem("${KEY}");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){}`;

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

const current = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

/** Switches between the light and dark theme and remembers the choice on this device. */
export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, current, () => "light" as Theme);
  const next: Theme = theme === "dark" ? "light" : "dark";

  function toggle() {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // storage can be blocked; the theme still applies for this visit
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
      className="grid h-9 w-9 place-items-center rounded-full border border-slate-300 text-slate-700 hover:bg-slate-100"
    >
      {theme === "dark" ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </button>
  );
}
