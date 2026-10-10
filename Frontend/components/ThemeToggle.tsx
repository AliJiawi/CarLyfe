"use client";

import { useEffect, useState } from "react";

const KEY = "carlyfe-theme";

/** Light/dark switch. Default is light; the choice is remembered in localStorage. */
export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  // The inline script in layout.tsx has already set data-theme before first paint; mirror it.
  useEffect(() => {
    setDark(document.documentElement.dataset.theme === "dark");
  }, []);

  const toggle = () => {
    const next = !dark;
    const root = document.documentElement;
    root.classList.add("theme-switching");
    if (next) root.dataset.theme = "dark";
    else delete root.dataset.theme;
    window.setTimeout(() => root.classList.remove("theme-switching"), 320);
    try {
      localStorage.setItem(KEY, next ? "dark" : "light");
    } catch {
      /* private mode: the choice just won't persist */
    }
    setDark(next);
  };

  return (
    <button type="button" className="theme-toggle" role="switch" aria-checked={dark} aria-label="Dark mode" onClick={toggle}>
      <span className="switch-track" aria-hidden="true">
        <span className="switch-knob" />
      </span>
      Dark
    </button>
  );
}
