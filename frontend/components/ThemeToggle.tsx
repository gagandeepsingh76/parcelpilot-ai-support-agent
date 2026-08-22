"use client";

import { useCallback, useEffect, useState } from "react";

type ThemePref = "light" | "dark" | "system";

const STORAGE_KEY = "pp-theme";

function resolve(pref: ThemePref): "light" | "dark" {
  if (pref === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return pref;
}

function apply(pref: ThemePref) {
  document.documentElement.dataset.theme = resolve(pref);
}

export default function ThemeToggle() {
  const [pref, setPref] = useState<ThemePref>("system");

  useEffect(() => {
    let saved: ThemePref = "system";
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw === "light" || raw === "dark" || raw === "system") saved = raw;
    } catch {}
    setPref(saved);
    apply(saved);

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if ((localStorage.getItem(STORAGE_KEY) || "system") === "system") apply("system");
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const choose = useCallback((next: ThemePref) => {
    setPref(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {}
    apply(next);
  }, []);

  return (
    <div className="theme-toggle" role="group" aria-label="Theme">
      {(
        [
          ["light", "Light"],
          ["dark", "Dark"],
          ["system", "System"],
        ] as const
      ).map(([value, label]) => (
        <button
          key={value}
          className={pref === value ? "on" : ""}
          aria-pressed={pref === value}
          onClick={() => choose(value)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
