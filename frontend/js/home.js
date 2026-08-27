// Home page logic
import { renderNav } from "./nav.js";
import { healthCheck } from "./api.js";
import { getHistory, getHistoryCount } from "./storage.js";
import { initScrollAnimations, animateCounter } from "./scroll-animations.js";

renderNav("home");

// Health check
const healthEl = document.getElementById("health-status");

healthCheck()
  .then(() => {
    healthEl.className = "alert alert-success";
    healthEl.innerHTML = '<span class="status-dot status-dot-ok"></span> Backend is running and healthy.';
  })
  .catch(() => {
    healthEl.className = "alert alert-error";
    healthEl.innerHTML =
      '<span class="status-dot status-dot-error"></span> Backend is not reachable. Make sure the backend server is running on <code>http://127.0.0.1:8000</code>.';
  });

// History count & stats
const history = getHistory();
const count = history.length;
document.getElementById("history-count").textContent = count;

// Animate stats
const reviewsEl = document.getElementById("stat-reviews");
const avgEl = document.getElementById("stat-avg-score");

animateCounter(reviewsEl, count, 800);

if (count > 0) {
  const scores = history
    .map((h) => h.weighted_total)
    .filter((s) => s != null && !isNaN(s));
  if (scores.length > 0) {
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    animateCounter(avgEl, avg, 1000, "", 1);
  }
}

// Quick load
document.getElementById("quick-load-btn").addEventListener("click", () => {
  const id = document.getElementById("quick-review-id").value.trim();
  if (id) {
    window.location.href = `/results.html?id=${encodeURIComponent(id)}`;
  }
});

document.getElementById("quick-review-id").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    document.getElementById("quick-load-btn").click();
  }
});

// Init scroll reveal
initScrollAnimations();
