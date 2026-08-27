// Chart.js wrapper — radar, donut, bar, and SVG gauge
const activeCharts = {};

function getChartClass() {
  return typeof window !== "undefined" && window.Chart ? window.Chart : null;
}

function destroyExistingChart(canvasId, canvas, ChartClass) {
  if (activeCharts[canvasId]) {
    try {
      activeCharts[canvasId].destroy();
    } catch (e) {}
    delete activeCharts[canvasId];
  }
  if (ChartClass && typeof ChartClass.getChart === "function" && canvas) {
    try {
      const existing = ChartClass.getChart(canvas);
      if (existing) existing.destroy();
    } catch (e) {}
  }
}

// ---- Shared chart theme ----
function getChartColors() {
  const isDark = document.documentElement.getAttribute("data-theme") !== "light";
  return {
    gridColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
    tickColor: isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.5)",
    textColor: isDark ? "#cbd5e1" : "#475569",
    bgAlpha: isDark ? 0.15 : 0.12,
  };
}

const CATEGORY_COLORS = {
  code_quality: "#3b82f6",
  architecture: "#8b5cf6",
  documentation: "#06b6d4",
  security: "#ef4444",
  performance: "#f97316",
  ui_ux: "#d946ef",
  innovation: "#14b8a6",
  testing: "#2563eb",
};

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

const SEVERITY_COLORS = {
  critical: "#dc2626",
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#10b981",
};

// ---- Radar Chart (Scorecard) ----
/**
 * Render the 8-category scorecard radar chart.
 * @param {string} canvasId
 * @param {object} categories - { code_quality: { score, weight }, ... }
 * @returns {Chart}
 */
export function renderRadarChart(canvasId, categories) {
  const canvas = document.getElementById(canvasId);
  const ChartClass = getChartClass();
  if (!canvas || !ChartClass || !categories) return null;
  destroyExistingChart(canvasId, canvas, ChartClass);
  const ctx = canvas.getContext("2d");
  const colors = getChartColors();

  const labels = [];
  const data = [];
  const bgColors = [];

  for (const [key, cat] of Object.entries(categories)) {
    labels.push(CATEGORY_LABELS[key] || key);
    const scoreVal = typeof cat === "object" && cat !== null ? (cat.score ?? 0) : (typeof cat === "number" ? cat : 0);
    data.push(scoreVal);
    bgColors.push(CATEGORY_COLORS[key] || "#6b7280");
  }

  activeCharts[canvasId] = new ChartClass(ctx, {
    type: "radar",
    data: {
      labels,
      datasets: [
        {
          label: "Score",
          data,
          fill: true,
          backgroundColor: `rgba(59, 130, 246, ${colors.bgAlpha})`,
          borderColor: "#3b82f6",
          borderWidth: 2,
          pointBackgroundColor: bgColors,
          pointBorderColor: "#fff",
          pointBorderWidth: 1,
          pointRadius: 5,
          pointHoverRadius: 7,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15,23,42,0.9)",
          titleColor: "#f1f5f9",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(59,130,246,0.3)",
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: (ctx) => `Score: ${ctx.parsed.r}/100`,
          },
        },
      },
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          ticks: {
            stepSize: 20,
            color: colors.tickColor,
            backdropColor: "transparent",
            font: { size: 10 },
          },
          grid: {
            color: colors.gridColor,
          },
          angleLines: {
            color: colors.gridColor,
          },
          pointLabels: {
            color: colors.textColor,
            font: { size: 11, weight: "600" },
          },
        },
      },
      animation: {
        duration: 1200,
        easing: "easeOutCubic",
      },
    },
  });
  return activeCharts[canvasId];
}

// ---- Donut Chart (Severity) ----
/**
 * Render severity breakdown as a doughnut chart.
 * @param {string} canvasId
 * @param {object} counts - { critical: N, high: N, medium: N, low: N }
 * @returns {Chart}
 */
export function renderDonutChart(canvasId, counts) {
  const canvas = document.getElementById(canvasId);
  const ChartClass = getChartClass();
  if (!canvas || !ChartClass || !counts) return null;
  destroyExistingChart(canvasId, canvas, ChartClass);
  const ctx = canvas.getContext("2d");

  const levels = ["critical", "high", "medium", "low"];
  const data = levels.map((l) => counts[l] ?? 0);
  const colors = levels.map((l) => SEVERITY_COLORS[l]);

  activeCharts[canvasId] = new ChartClass(ctx, {
    type: "doughnut",
    data: {
      labels: levels.map((l) => l.charAt(0).toUpperCase() + l.slice(1)),
      datasets: [
        {
          data,
          backgroundColor: colors,
          borderColor: "transparent",
          borderWidth: 0,
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: getChartColors().textColor,
            padding: 16,
            usePointStyle: true,
            pointStyle: "circle",
            font: { size: 11, weight: "600" },
          },
        },
        tooltip: {
          backgroundColor: "rgba(15,23,42,0.9)",
          titleColor: "#f1f5f9",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(59,130,246,0.3)",
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
        },
      },
      animation: {
        animateRotate: true,
        duration: 1000,
        easing: "easeOutCubic",
      },
    },
  });
  return activeCharts[canvasId];
}

// ---- Horizontal Bar Chart (Categories) ----
/**
 * Render category breakdown as horizontal bars.
 * @param {string} canvasId
 * @param {object} counts - { bug_risk: N, maintainability: N, ... }
 * @returns {Chart}
 */
export function renderBarChart(canvasId, counts) {
  const canvas = document.getElementById(canvasId);
  const ChartClass = getChartClass();
  if (!canvas || !ChartClass || !counts) return null;
  destroyExistingChart(canvasId, canvas, ChartClass);
  const ctx = canvas.getContext("2d");
  const chartColors = getChartColors();

  const catLabels = {
    bug_risk: "Bug Risk",
    maintainability: "Maintainability",
    style: "Style",
    security: "Security",
  };

  const labels = [];
  const data = [];
  const bgColors = [];
  const barColors = ["#3b82f6", "#8b5cf6", "#06b6d4", "#ef4444", "#f97316", "#14b8a6"];

  let colorIdx = 0;
  for (const [key, val] of Object.entries(counts)) {
    labels.push(catLabels[key] || key);
    data.push(val);
    bgColors.push(barColors[colorIdx % barColors.length]);
    colorIdx++;
  }

  return new ChartClass(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: bgColors,
          borderRadius: 6,
          borderSkipped: false,
          barThickness: 28,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15,23,42,0.9)",
          titleColor: "#f1f5f9",
          bodyColor: "#cbd5e1",
          borderColor: "rgba(59,130,246,0.3)",
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
        },
      },
      scales: {
        x: {
          grid: { color: chartColors.gridColor },
          ticks: { color: chartColors.tickColor, font: { size: 11 } },
        },
        y: {
          grid: { display: false },
          ticks: { color: chartColors.textColor, font: { size: 12, weight: "600" } },
        },
      },
      animation: {
        duration: 800,
        easing: "easeOutCubic",
      },
    },
  });
}

// ---- SVG Circular Gauge ----
/**
 * Render an animated SVG circular score gauge.
 * @param {string} containerId - ID of the container element
 * @param {number} score - Score value (0-100)
 * @param {number} size - Diameter in pixels (default 180)
 */
export function renderScoreGauge(containerId, score, size = 180) {
  const container = document.getElementById(containerId);
  if (!container) return;

  score = Math.max(0, Math.min(100, score ?? 0));
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  // Color based on score
  let color;
  if (score >= 80) color = "#10b981";
  else if (score >= 60) color = "#f59e0b";
  else if (score >= 40) color = "#f97316";
  else color = "#ef4444";

  const label = score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Moderate" : "Needs Work";

  container.innerHTML = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="score-gauge-svg">
      <circle
        cx="${size / 2}" cy="${size / 2}" r="${radius}"
        fill="none"
        stroke="var(--color-border, rgba(255,255,255,0.08))"
        stroke-width="10"
      />
      <circle
        cx="${size / 2}" cy="${size / 2}" r="${radius}"
        fill="none"
        stroke="${color}"
        stroke-width="10"
        stroke-linecap="round"
        stroke-dasharray="${circumference}"
        stroke-dashoffset="${circumference}"
        transform="rotate(-90 ${size / 2} ${size / 2})"
        class="score-gauge-arc"
        style="--target-offset: ${offset}; --circumference: ${circumference};"
      />
      <text
        x="${size / 2}" y="${size / 2 - 8}"
        text-anchor="middle"
        dominant-baseline="central"
        fill="${color}"
        font-size="2.2rem"
        font-weight="700"
        font-family="var(--font-family)"
        class="score-gauge-value"
      >${score.toFixed(1)}</text>
      <text
        x="${size / 2}" y="${size / 2 + 22}"
        text-anchor="middle"
        dominant-baseline="central"
        fill="var(--color-text-secondary, #94a3b8)"
        font-size="0.75rem"
        font-weight="600"
        font-family="var(--font-family)"
        text-transform="uppercase"
        letter-spacing="0.05em"
      >${label}</text>
    </svg>
  `;

  // Animate the arc
  requestAnimationFrame(() => {
    const arc = container.querySelector(".score-gauge-arc");
    if (arc) {
      arc.style.transition = "stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)";
      arc.style.strokeDashoffset = offset;
    }
  });
}
