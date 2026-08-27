// New review page logic — tabs, drag-drop, progress steps
import { renderNav } from "./nav.js";
import { postReview, uploadReview } from "./api.js";
import { saveToHistory } from "./storage.js";
import { initScrollAnimations } from "./scroll-animations.js";

renderNav("review");

const githubForm = document.getElementById("github-form");
const uploadForm = document.getElementById("upload-form");
const statusArea = document.getElementById("status-area");
const loadingState = document.getElementById("loading-state");
const loadingText = document.getElementById("loading-text");
const errorState = document.getElementById("error-state");
const errorMessage = document.getElementById("error-message");
const retryBtn = document.getElementById("retry-btn");
const githubSubmitBtn = document.getElementById("github-submit-btn");
const uploadSubmitBtn = document.getElementById("upload-submit-btn");

// ---- Tab Switching ----
const tabBtns = document.querySelectorAll(".tab-btn");
const tabContents = document.querySelectorAll(".tab-content");

tabBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const tabId = btn.dataset.tab;
    tabBtns.forEach((b) => b.classList.remove("active"));
    tabContents.forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${tabId}`).classList.add("active");
  });
});

// ---- Drag & Drop ----
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("upload-file");
const fileNameDisplay = document.getElementById("file-name-display");

if (dropZone) {
  ["dragenter", "dragover"].forEach((ev) => {
    dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((ev) => {
    dropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      fileInput.files = files;
      showFileName(files[0].name);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      showFileName(fileInput.files[0].name);
    }
  });
}

function showFileName(name) {
  if (fileNameDisplay) {
    fileNameDisplay.textContent = `📎 ${name}`;
  }
}

// ---- Status Helpers ----
function showLoading(message) {
  statusArea.classList.remove("hidden");
  loadingState.classList.remove("hidden");
  errorState.classList.add("hidden");
  loadingText.textContent = message;
  startProgressAnimation();
}

function showError(msg) {
  statusArea.classList.remove("hidden");
  loadingState.classList.add("hidden");
  errorState.classList.remove("hidden");
  errorMessage.textContent = msg;
}

function hideStatus() {
  statusArea.classList.add("hidden");
  stopProgressAnimation();
}

function onSuccess(data) {
  saveToHistory(data);
  window.location.href = `/results.html?id=${encodeURIComponent(data.review_id)}`;
}

// ---- Progress Animation ----
let progressInterval = null;

function startProgressAnimation() {
  const steps = document.querySelectorAll(".progress-step");
  let current = 0;

  // Reset all steps
  steps.forEach((s) => {
    s.classList.remove("active", "done");
  });
  if (steps[0]) steps[0].classList.add("active");

  const timings = [3000, 8000, 4000]; // how long each step shows before advancing

  function advance() {
    if (current < steps.length - 1) {
      steps[current].classList.remove("active");
      steps[current].classList.add("done");
      steps[current].querySelector(".progress-step-icon").textContent = "✅";
      current++;
      steps[current].classList.add("active");
    }
  }

  let stepIdx = 0;
  function scheduleNext() {
    if (stepIdx >= timings.length) return;
    progressInterval = setTimeout(() => {
      advance();
      stepIdx++;
      scheduleNext();
    }, timings[stepIdx]);
  }

  scheduleNext();
}

function stopProgressAnimation() {
  if (progressInterval) {
    clearTimeout(progressInterval);
    progressInterval = null;
  }
}

// ---- GitHub URL form ----
githubForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  let repoUrl = document.getElementById("repo-url").value.trim();
  const maxFiles = document.getElementById("github-max-files").value;

  // Normalize URL (support "owner/repo", "github.com/owner/repo", and "https://...")
  if (repoUrl.includes("github.com/")) {
    if (!repoUrl.startsWith("http://") && !repoUrl.startsWith("https://")) {
      repoUrl = "https://" + repoUrl;
    }
  } else if (!repoUrl.startsWith("http://") && !repoUrl.startsWith("https://")) {
    repoUrl = `https://github.com/${repoUrl}`;
  }

  githubSubmitBtn.disabled = true;
  uploadSubmitBtn.disabled = true;
  showLoading("Cloning repository and running analysis…");

  try {
    const data = await postReview(repoUrl, maxFiles);
    onSuccess(data);
  } catch (err) {
    showError(err.message || "Review failed. Check the backend logs.");
  } finally {
    githubSubmitBtn.disabled = false;
    uploadSubmitBtn.disabled = false;
    stopProgressAnimation();
  }
});


// ---- Upload form ----
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  const maxFiles = document.getElementById("upload-max-files").value;

  githubSubmitBtn.disabled = true;
  uploadSubmitBtn.disabled = true;
  showLoading(`Uploading "${file.name}" and running analysis…`);

  try {
    const data = await uploadReview(file, maxFiles);
    onSuccess(data);
  } catch (err) {
    showError(err.message || "Upload failed. Check the file format.");
  } finally {
    githubSubmitBtn.disabled = false;
    uploadSubmitBtn.disabled = false;
    stopProgressAnimation();
  }
});

// Retry button
retryBtn.addEventListener("click", () => {
  hideStatus();
});

initScrollAnimations();
