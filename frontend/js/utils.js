// Utility functions — formatters, color mappers, helpers

/**
 * Format an ISO date string to a readable format.
 * @param {string} isoString
 * @returns {string}
 */
export function formatDate(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Get severity badge class.
 * @param {string} severity
 * @returns {string}
 */
export function severityClass(severity) {
  const s = (severity || "low").toLowerCase();
  return `badge-${s}`;
}

/**
 * Get a color for a score value (0-100).
 * @param {number} score
 * @returns {string} CSS color
 */
export function scoreColor(score) {
  if (score >= 80) return "#10b981";
  if (score >= 60) return "#f59e0b";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

/**
 * Map scorecard category key to display name.
 */
const CATEGORY_LABELS = {
  code_quality: "Code Quality",
  architecture: "Architecture",
  documentation: "Documentation",
  security: "Security",
  performance: "Performance",
  ui_ux: "UI / UX",
  innovation: "Innovation",
  testing: "Testing",
};

/**
 * Category colors for scorecard bars.
 */
const CATEGORY_COLORS = {
  code_quality: "#4361ee",
  architecture: "#7c3aed",
  documentation: "#0891b2",
  security: "#dc2626",
  performance: "#ea580c",
  ui_ux: "#d946ef",
  innovation: "#0d9488",
  testing: "#2563eb",
};

export function categoryLabel(key) {
  return CATEGORY_LABELS[key] || key;
}

export function categoryColor(key) {
  return CATEGORY_COLORS[key] || "#6b7280";
}

/**
 * Escape HTML to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
export function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Truncate a string to maxLen with ellipsis.
 */
export function truncate(str, maxLen = 80) {
  if (!str || str.length <= maxLen) return str || "";
  return str.slice(0, maxLen) + "…";
}

/**
 * Safely get nested property.
 */
export function safeGet(obj, path, fallback = "—") {
  const keys = path.split(".");
  let val = obj;
  for (const key of keys) {
    val = val?.[key];
    if (val === undefined || val === null) return fallback;
  }
  return val;
}
