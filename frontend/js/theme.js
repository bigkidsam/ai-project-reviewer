// Theme manager — dark/light mode toggle with localStorage persistence

const STORAGE_KEY = "ai_reviewer_theme";

/**
 * Get the current theme.
 * @returns {"dark" | "light"}
 */
export function getTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "dark" || stored === "light") return stored;
  // Fallback to OS preference
  if (window.matchMedia?.("(prefers-color-scheme: light)").matches) return "light";
  return "dark";
}

/**
 * Apply a theme to the document.
 * @param {"dark" | "light"} theme
 */
export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(STORAGE_KEY, theme);
  // Update toggle icon if present
  const icon = document.getElementById("theme-toggle-icon");
  if (icon) {
    icon.textContent = theme === "dark" ? "☀️" : "🌙";
  }
}

/**
 * Toggle between dark and light themes.
 * @returns {"dark" | "light"} The new theme
 */
export function toggleTheme() {
  const current = getTheme();
  const next = current === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}

/**
 * Initialize theme on page load (call early).
 */
export function initTheme() {
  applyTheme(getTheme());
}
