// History page logic — database-backed history with local cache fallback
import { renderNav } from "./nav.js";
import { listReviewsApi, deleteReviewApi } from "./api.js";
import { getHistory, clearHistory, deleteFromHistory } from "./storage.js";
import { formatDate, scoreColor, escapeHtml, truncate } from "./utils.js";
import { initScrollAnimations } from "./scroll-animations.js";

renderNav("history");

const contentEl = document.getElementById("history-content");
const clearBtn = document.getElementById("clear-history-btn");
const searchInput = document.getElementById("search-input");
const sortSelect = document.getElementById("sort-select");
const countDisplay = document.getElementById("history-count-display");

let currentHistory = [];
let searchTimeout = null;

async function loadHistory() {
  const query = (searchInput?.value || "").trim();
  const sortMode = sortSelect?.value || "date_desc";

  // Map sort mode to backend sort_by
  const sortMap = {
    "date-desc": "date_desc",
    "date-asc": "date_asc",
    "score-desc": "score_desc",
    "score-asc": "score_asc",
    "findings-desc": "findings_desc",
  };
  const sortBy = sortMap[sortMode] || "date_desc";

  try {
    const data = await listReviewsApi({
      search: query,
      sortBy: sortBy,
      limit: 100,
    });
    if (data && Array.isArray(data.items)) {
      currentHistory = data.items.map((item) => ({
        review_id: item.review_id,
        repo_url: item.repo_url,
        repo_name: item.repository_metadata?.name || item.repo_name || "Repository",
        quality_score: item.metrics?.quality_score ?? item.quality_score,
        weighted_total: item.scorecard?.weighted_total ?? item.weighted_total,
        total_findings: item.metrics?.total_findings ?? item.total_findings ?? 0,
        created_at: item.created_at,
      }));
    }
  } catch (err) {
    // Fallback to local storage
    currentHistory = getHistory();
  }

  renderList();
}

function renderList() {
  if (countDisplay) {
    countDisplay.textContent = `${currentHistory.length} reviews`;
  }

  if (currentHistory.length === 0) {
    clearBtn.classList.add("hidden");
    contentEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <div class="empty-state-title">No reviews yet</div>
        <div class="empty-state-desc">Reviews you run will automatically appear here with metrics and score history.</div>
        <a href="/review.html" class="btn btn-primary">🚀 Start a Review</a>
      </div>
    `;
    return;
  }

  clearBtn.classList.remove("hidden");

  let html = '<div class="history-grid">';

  for (const entry of currentHistory) {
    const score = entry.weighted_total != null ? entry.weighted_total : entry.quality_score;
    const scoreText = score != null ? Number(score).toFixed(1) : "—";
    const color = score != null ? scoreColor(Number(score)) : "var(--color-text-muted)";
    const reviewId = escapeHtml(entry.review_id || "");

    html += `
      <div class="history-card" id="card-${reviewId}">
        <div class="history-card-header">
          <div>
            <div class="history-card-name">${escapeHtml(entry.repo_name || "Repository")}</div>
            <a href="${escapeHtml(entry.repo_url || "#")}" target="_blank" class="form-hint" style="text-decoration: underline; word-break: break-all;">
              ${escapeHtml(truncate(entry.repo_url || "—", 40))}
            </a>
          </div>
          <div class="history-card-score" style="border-color: ${color}; color: ${color};">
            ${scoreText}
          </div>
        </div>

        <div class="history-card-meta">
          <span>📅 ${formatDate(entry.created_at)}</span>
          <span>⚠️ ${entry.total_findings ?? 0} findings</span>
        </div>

        <div class="history-card-actions">
          <a href="/results.html?id=${encodeURIComponent(entry.review_id)}" class="btn btn-primary btn-sm">
            View Details
          </a>
          <button class="history-card-delete" data-id="${reviewId}" title="Delete review" aria-label="Delete review">
            ✕
          </button>
        </div>
      </div>
    `;
  }

  html += "</div>";
  contentEl.innerHTML = html;

  // Attach delete handlers
  contentEl.querySelectorAll(".history-card-delete").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.getAttribute("data-id");
      if (id && confirm("Delete this review from the database?")) {
        const card = document.getElementById(`card-${id}`);
        if (card) {
          card.style.opacity = "0";
          card.style.transform = "scale(0.95)";
        }
        try {
          await deleteReviewApi(id);
        } catch {
          // ignore error if already removed
        }
        deleteFromHistory(id);
        setTimeout(loadHistory, 200);
      }
    });
  });

  initScrollAnimations();
}

// Clear all history
clearBtn.addEventListener("click", async () => {
  if (confirm("Are you sure you want to clear all review history? This will delete local cached items.")) {
    clearHistory();
    // Also try deleting each on backend
    for (const item of currentHistory) {
      try {
        await deleteReviewApi(item.review_id);
      } catch {}
    }
    loadHistory();
  }
});

// Search debounce
if (searchInput) {
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadHistory, 300);
  });
}

if (sortSelect) {
  sortSelect.addEventListener("change", () => {
    loadHistory();
  });
}

loadHistory();
