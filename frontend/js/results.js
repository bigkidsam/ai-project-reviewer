// Results page logic — charts, gauge, typewriter, export
import { renderNav } from "./nav.js";
import { getReview } from "./api.js";
import { saveToHistory, saveFullReviewToStorage, getFullReviewFromStorage } from "./storage.js";
import { renderRadarChart, renderDonutChart, renderBarChart, renderScoreGauge } from "./charts.js";
import { initScrollAnimations, animateCounter } from "./scroll-animations.js";
import {
  formatDate,
  severityClass,
  scoreColor,
  categoryLabel,
  categoryColor,
  escapeHtml,
  truncate,
} from "./utils.js";

let fullReviewData = null;

function getLoadingEl() { return document.getElementById("page-loading"); }
function getErrorEl() { return document.getElementById("page-error"); }
function getContentEl() { return document.getElementById("results-content"); }
function getErrorMsgEl() { return document.getElementById("error-msg"); }

function initResultsPage() {
  renderNav("results");

  const params = new URLSearchParams(window.location.search);
  const reviewId = params.get("id");

  if (!reviewId) {
    showError("No review ID provided. Go to the review page to start a new analysis.");
  } else {
    loadReview(reviewId);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initResultsPage);
} else {
  initResultsPage();
}

async function loadReview(id) {
  // 1. Instant render from local cache if available (0ms latency)
  const cached = getFullReviewFromStorage(id);
  if (cached) {
    fullReviewData = cached;
    renderResults(cached);
  }

  // 2. Fetch fresh review from API in background
  try {
    const data = await getReview(id);
    fullReviewData = data;
    saveToHistory(data);
    saveFullReviewToStorage(data);
    renderResults(data);
  } catch (err) {
    if (!cached) {
      showError(
        err.message || "Failed to load review. Please make sure the backend server is running on http://127.0.0.1:8000."
      );
    }
  }
}

function showError(msg) {
  const loadingEl = getLoadingEl();
  if (loadingEl) loadingEl.classList.add("hidden");

  const errorEl = getErrorEl();
  if (errorEl) errorEl.classList.remove("hidden");

  const errorMsgEl = getErrorMsgEl();
  if (errorMsgEl) errorMsgEl.textContent = msg;
}

function renderResults(data) {
  const loadingEl = getLoadingEl();
  if (loadingEl) loadingEl.classList.add("hidden");

  const contentEl = getContentEl();
  if (contentEl) contentEl.classList.remove("hidden");
  if (!data) return;

  const renderSteps = [
    { name: "Header", fn: () => renderHeader(data) },
    { name: "Scorecard", fn: () => renderScorecard(data.scorecard) },
    { name: "Metrics", fn: () => renderMetrics(data.metrics) },
    { name: "SeverityChart", fn: () => renderSeverityChart(data.metrics?.severity_counts) },
    { name: "CategoryChart", fn: () => renderCategoryChart(data.metrics?.category_counts) },
    { name: "Metadata", fn: () => renderMetadata(data.repository_metadata) },
    { name: "AiReview", fn: () => renderAiReview(data.ai_review) },
    { name: "AnalyzedFiles", fn: () => renderAnalyzedFiles(data.analyzed_files) },
    { name: "Findings", fn: () => renderFindings(data.findings) },
    { name: "Fixes", fn: () => renderFixes(data.fix_suggestions) },
    { name: "RawOutput", fn: () => renderRawOutput(data.issues) },
    { name: "Export", fn: () => setupExport() },
  ];

  for (const step of renderSteps) {
    try {
      step.fn();
    } catch (e) {
      console.warn(`Error rendering ${step.name}:`, e);
    }
  }

  // Initialize scroll animations after content is rendered
  requestAnimationFrame(() => {
    try {
      initScrollAnimations();
    } catch (e) {}
  });
}

// ---- 1. Header ----
function renderHeader(data) {
  const name = data.repository_metadata?.name || "Unknown Repository";
  const repoNameEl = document.getElementById("repo-name");
  if (repoNameEl) repoNameEl.textContent = name;
  document.title = `${name} — Review Results`;

  const urlLink = document.getElementById("repo-url-link");
  if (urlLink) {
    urlLink.textContent = data.repo_url || "—";
    urlLink.href = data.repo_url || "#";
  }

  const reviewIdEl = document.getElementById("review-id");
  if (reviewIdEl) reviewIdEl.textContent = data.review_id || reviewId || "—";

  const reviewDateEl = document.getElementById("review-date");
  if (reviewDateEl) reviewDateEl.textContent = formatDate(data.created_at);
}

// ---- 2. Scorecard + Radar Chart + Gauge ----
function renderScorecard(scorecard) {
  const section = document.getElementById("scorecard-section");
  if (!scorecard || !scorecard.categories) {
    section.classList.add("hidden");
    return;
  }

  const grid = document.getElementById("scorecard-grid");
  grid.innerHTML = "";

  for (const [key, cat] of Object.entries(scorecard.categories)) {
    const scoreVal = typeof cat === "object" && cat !== null ? (cat.score ?? 0) : (typeof cat === "number" ? cat : 0);
    const weightVal = typeof cat === "object" && cat !== null ? (cat.weight ?? 0) : 0;
    const color = categoryColor(key);
    const card = document.createElement("div");
    card.className = "score-card";
    card.innerHTML = `
      <div class="score-card-label">${categoryLabel(key)}</div>
      <div class="score-card-value" style="color: ${scoreColor(scoreVal)};">${scoreVal}</div>
      <div class="score-card-weight">Weight: ${weightVal}%</div>
      <div class="score-card-bar">
        <div class="score-card-bar-fill" style="width: ${scoreVal}%; background: ${color};"></div>
      </div>
    `;
    grid.appendChild(card);
  }

  // Render radar chart
  renderRadarChart("radar-chart", scorecard.categories);

  // Render score gauge
  const total = scorecard.weighted_total ?? 0;
  renderScoreGauge("score-gauge", total);
}

// ---- 3. Metrics ----
function renderMetrics(metrics) {
  const grid = document.getElementById("metrics-grid");
  if (!metrics) return;

  const items = [
    { label: "Quality Score", value: metrics.quality_score ?? "—", icon: "⭐" },
    { label: "Files Analyzed", value: metrics.total_files_analyzed ?? "—", icon: "📁" },
    { label: "Total Findings", value: metrics.total_findings ?? "—", icon: "🔍" },
    { label: "Issue Density", value: metrics.issue_density_per_file ?? "—", icon: "📊" },
    { label: "Files with Issues", value: metrics.files_with_issues ?? "—", icon: "⚠️" },
    { label: "Files with Errors", value: metrics.files_with_errors ?? "—", icon: "❌" },
  ];

  grid.innerHTML = items
    .map(
      (item) => `
    <div class="metric-card">
      <div class="metric-label">${item.label}</div>
      <div class="metric-value">${item.value}</div>
    </div>
  `
    )
    .join("");
}

// ---- 4. Severity Donut Chart ----
function renderSeverityChart(counts) {
  if (!counts) return;
  renderDonutChart("severity-chart", counts);
}

// ---- 5. Category Bar Chart ----
function renderCategoryChart(counts) {
  if (!counts) return;
  renderBarChart("category-chart", counts);
}

// ---- 6. Repository Metadata ----
function renderMetadata(meta) {
  const grid = document.getElementById("metadata-grid");
  if (!meta) return;

  const boolItems = [
    { label: "README", value: meta.has_readme },
    { label: "Documentation", value: meta.has_docs },
    { label: "pyproject.toml", value: meta.has_pyproject },
    { label: "requirements.txt", value: meta.has_requirements },
    { label: "Tests", value: meta.has_tests },
    { label: "Backend Code", value: meta.has_backend },
    { label: "Frontend Code", value: meta.has_frontend },
    { label: "ML Code", value: meta.has_ml_code },
    { label: "AI Code", value: meta.has_ai_code },
    { label: "Novel Structure", value: meta.has_novel_structure },
  ];

  const numItems = [
    { label: "Python Files", value: meta.python_file_count },
    { label: "Frontend Files", value: meta.frontend_file_count },
    { label: "Test Files", value: meta.test_file_count },
    { label: "README Length", value: meta.readme_length != null ? `${meta.readme_length} chars` : null },
  ];

  let html = "";

  for (const item of boolItems) {
    const icon = item.value ? "✅" : "❌";
    html += `
      <div class="info-item">
        <span class="info-item-icon">${icon}</span>
        <span class="info-item-label">${item.label}</span>
      </div>
    `;
  }

  for (const item of numItems) {
    if (item.value == null) continue;
    html += `
      <div class="info-item">
        <span class="info-item-icon">📊</span>
        <span class="info-item-label">${item.label}</span>
        <span class="info-item-value">${item.value}</span>
      </div>
    `;
  }

  grid.innerHTML = html;
}

// ---- 7. AI Review (Typewriter) ----
function renderAiReview(text) {
  const el = document.getElementById("ai-review-text");
  const content = text || "No AI review summary available.";

  // Typewriter effect
  el.textContent = "";
  el.classList.add("typewriter-cursor");

  let i = 0;
  const speed = 8; // ms per character
  const maxChars = 2000; // Don't animate very long texts
  const shouldAnimate = content.length <= maxChars;

  if (shouldAnimate) {
    function type() {
      if (i < content.length) {
        el.textContent += content.charAt(i);
        i++;
        setTimeout(type, speed);
      } else {
        el.classList.remove("typewriter-cursor");
      }
    }

    // Start after a short delay
    setTimeout(type, 500);
  } else {
    el.textContent = content;
    el.classList.remove("typewriter-cursor");
  }
}

// ---- 8. Analyzed Files ----
function renderAnalyzedFiles(files) {
  const container = document.getElementById("analyzed-files-list");
  const countEl = document.getElementById("files-count");

  if (!files || files.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>No files analyzed.</p></div>';
    return;
  }

  countEl.textContent = `${files.length} files`;
  container.innerHTML = files
    .map((f) => `<div class="info-item" style="margin-bottom: 4px;"><span>📄</span> ${escapeHtml(f)}</div>`)
    .join("");
}

// ---- 9. Findings Table ----
let allFindings = [];

function renderFindings(findings) {
  allFindings = findings || [];
  const countEl = document.getElementById("findings-count");
  if (countEl) countEl.textContent = `${allFindings.length} total`;

  // Populate tool filter
  const tools = [...new Set(allFindings.map((f) => f.tool).filter(Boolean))];
  const toolSelect = document.getElementById("filter-tool");
  if (toolSelect) {
    tools.forEach((tool) => {
      const opt = document.createElement("option");
      opt.value = tool;
      opt.textContent = tool;
      toolSelect.appendChild(opt);
    });
    toolSelect.removeEventListener("change", applyFindingFilters);
    toolSelect.addEventListener("change", applyFindingFilters);
  }

  const sevFilter = document.getElementById("filter-severity");
  if (sevFilter) {
    sevFilter.removeEventListener("change", applyFindingFilters);
    sevFilter.addEventListener("change", applyFindingFilters);
  }

  applyFindingFilters();
}

function applyFindingFilters() {
  const sevFilter = document.getElementById("filter-severity")?.value || "";
  const toolFilter = document.getElementById("filter-tool")?.value || "";

  let filtered = allFindings;
  if (sevFilter) {
    filtered = filtered.filter((f) => f.severity === sevFilter);
  }
  if (toolFilter) {
    filtered = filtered.filter((f) => f.tool === toolFilter);
  }

  const countEl = document.getElementById("findings-count");
  if (countEl) countEl.textContent = `${filtered.length} of ${allFindings.length}`;

  const tbody = document.getElementById("findings-tbody");
  if (!tbody) return;

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--color-text-muted);">No findings match the filter.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered
    .map(
      (f) => `
    <tr>
      <td><span class="badge ${severityClass(f.severity)}">${f.severity}</span></td>
      <td><span class="badge badge-tool">${escapeHtml(f.tool || "—")}</span></td>
      <td style="font-family: var(--font-mono); font-size: var(--font-size-xs);">${escapeHtml(f.file || "—")}:${f.line ?? ""}${f.column ? ":" + f.column : ""}</td>
      <td><code style="font-family: var(--font-mono); font-size: var(--font-size-xs);">${escapeHtml(f.code || "—")}</code></td>
      <td>${escapeHtml(f.message || "—")}</td>
    </tr>
  `
    )
    .join("");
}

// ---- 10. Fix Suggestions ----
function renderFixes(fixes) {
  const tbody = document.getElementById("fixes-tbody");
  const countEl = document.getElementById("fixes-count");

  if (!fixes || fixes.length === 0) {
    countEl.textContent = "0 suggestions";
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--color-text-muted);">No fix suggestions.</td></tr>';
    return;
  }

  countEl.textContent = `${fixes.length} suggestions`;

  tbody.innerHTML = fixes
    .map((s, idx) => {
      const tierClass = s.tier === "rule_based" ? "badge-rule_based" : "badge-model_guided";
      const tierLabel = s.tier === "rule_based" ? "Rule-Based" : "Model-Guided";
      const suggestion = s.suggested_code
        ? `<div style="position: relative;">
            <code class="code-block" style="display: block; margin-top: 4px; padding: 8px; max-height: 100px; font-size: 0.7rem;">${escapeHtml(s.suggested_code)}</code>
            <button class="copy-btn" onclick="copyCode(this, '${idx}')" style="position: absolute; top: 8px; right: 8px;">Copy</button>
           </div>`
        : "";
      const explanation = s.explanation
        ? `<div style="margin-top: 4px; color: var(--color-text-secondary); font-size: var(--font-size-xs);">${escapeHtml(s.explanation)}</div>`
        : "";

      return `
        <tr>
          <td><span class="badge ${tierClass}">${tierLabel}</span></td>
          <td>${escapeHtml(s.confidence || "—")}</td>
          <td style="font-family: var(--font-mono); font-size: var(--font-size-xs);">${escapeHtml(s.file || "—")}:${s.line ?? ""}</td>
          <td>${escapeHtml(s.problem || "—")}</td>
          <td>${suggestion}${explanation}</td>
        </tr>
      `;
    })
    .join("");
}

// ---- 11. Raw Output ----
function renderRawOutput(issues) {
  document.getElementById("raw-output").textContent = issues || "No raw output available.";

  document.getElementById("raw-output-toggle").addEventListener("click", () => {
    document.getElementById("raw-output-collapsible").classList.toggle("open");
  });
}

// ---- 12. Export ----
function setupExport() {
  document.getElementById("export-json-btn").addEventListener("click", () => {
    if (!fullReviewData) return;
    const blob = new Blob([JSON.stringify(fullReviewData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `review-${fullReviewData.review_id || "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

// Global copy function for fix suggestions
window.copyCode = function (btn, idx) {
  const fixes = fullReviewData?.fix_suggestions;
  if (!fixes || !fixes[idx]) return;
  navigator.clipboard.writeText(fixes[idx].suggested_code || "").then(() => {
    btn.textContent = "Copied!";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = "Copy";
      btn.classList.remove("copied");
    }, 2000);
  });
};
