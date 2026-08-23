"use client";

import { useCallback, useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

type ThemePref = "light" | "dark";

const STORAGE_KEY = "pp-theme";

function apply(pref: ThemePref) {
  document.documentElement.dataset.theme = pref;
}

export default function ThemeToggle() {
  const [pref, setPref] = useState<ThemePref>("dark");

  useEffect(() => {
    let saved: ThemePref = "dark";
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw === "light" || raw === "dark") saved = raw;
    } catch {}
    setPref(saved);
    apply(saved);
  }, []);

  const choose = useCallback((next: ThemePref) => {
    setPref(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {}
    apply(next);
  }, []);

  return (
    <div className="theme-toggle" role="group" aria-label="Theme preference">
      <button
        className={pref === "light" ? "on" : ""}
        aria-pressed={pref === "light"}
        onClick={() => choose("light")}
        title="Switch to Light mode"
      >
        <Sun size={13} strokeWidth={2} aria-hidden="true" />
        <span>Light</span>
      </button>
      <button
        className={pref === "dark" ? "on" : ""}
        aria-pressed={pref === "dark"}
        onClick={() => choose("dark")}
        title="Switch to Dark mode"
      >
        <Moon size={13} strokeWidth={2} aria-hidden="true" />
        <span>Dark</span>
      </button>
    </div>
  );
}
