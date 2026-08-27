// localStorage helpers for review history

const STORAGE_KEY = "ai_reviewer_history";

/**
 * Save a review summary to history.
 * @param {object} review - ReviewResponse data
 */
export function saveToHistory(review) {
  const history = getHistory();
  const entry = {
    review_id: review.review_id,
    repo_url: review.repo_url,
    repo_name: review.repository_metadata?.name || "unknown",
    quality_score: review.metrics?.quality_score ?? null,
    weighted_total: review.scorecard?.weighted_total ?? null,
    total_findings: review.metrics?.total_findings ?? 0,
    created_at: review.created_at || new Date().toISOString(),
  };

  // Avoid duplicates
  const existing = history.findIndex(
    (h) => h.review_id === entry.review_id
  );
  if (existing >= 0) {
    history[existing] = entry;
  } else {
    history.unshift(entry);
  }

  // Keep last 50
  const trimmed = history.slice(0, 50);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

/**
 * Cache full review payload in localStorage for offline/fast retrieval.
 */
export function saveFullReviewToStorage(review) {
  if (!review || !review.review_id) return;
  try {
    localStorage.setItem(`ai_reviewer_detail_${review.review_id}`, JSON.stringify(review));
  } catch (e) {
    console.warn("Failed to save review detail to localStorage", e);
  }
}

/**
 * Get cached full review payload by ID.
 */
export function getFullReviewFromStorage(reviewId) {
  try {
    const raw = localStorage.getItem(`ai_reviewer_detail_${reviewId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Get all saved reviews.
 * @returns {object[]}
 */
export function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

/**
 * Clear all history.
 */
export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Delete a single review by ID.
 * @param {string} reviewId
 */
export function deleteFromHistory(reviewId) {
  const history = getHistory().filter((item) => item.review_id !== reviewId);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

/**
 * Get history count.
 * @returns {number}
 */
export function getHistoryCount() {
  return getHistory().length;
}

