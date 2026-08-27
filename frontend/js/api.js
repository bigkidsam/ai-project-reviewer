// API client for all backend calls
// Automatically connects to FastAPI on http://127.0.0.1:8000
const API_BASE =
  typeof window !== "undefined"
    ? window.location.port === "8000"
      ? ""
      : `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://127.0.0.1:8000";


async function handleResponseError(resp) {
  const text = await resp.text();
  let errorMsg = `Request failed with status ${resp.status}`;
  try {
    const data = JSON.parse(text);
    if (data.detail) {
      if (typeof data.detail === "string") {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
      } else {
        errorMsg = JSON.stringify(data.detail);
      }
    }
  } catch {
    if (text) errorMsg = text;
  }
  return new Error(errorMsg);
}

/**
 * Check backend health.
 * @returns {Promise<{status: string}>}
 */
export async function healthCheck() {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) throw new Error("Backend unreachable");
  return resp.json();
}

/**
 * Submit a GitHub repo URL for review.
 * @param {string} repoUrl
 * @param {number} maxFiles
 * @returns {Promise<object>} ReviewResponse
 */
export async function postReview(repoUrl, maxFiles) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl, max_files: Number(maxFiles) }),
    });
  } catch (netErr) {
    throw new Error(
      "Cannot connect to the backend server. Please make sure the backend is running on http://127.0.0.1:8000."
    );
  }

  if (!resp.ok) {
    throw await handleResponseError(resp);
  }
  return resp.json();
}


/**
 * Upload an archive file (.zip / .tar.gz) for review.
 * @param {File} file
 * @param {number} maxFiles
 * @returns {Promise<object>} ReviewResponse
 */
export async function uploadReview(file, maxFiles) {
  const formData = new FormData();
  formData.append("file", file);

  let resp;
  try {
    resp = await fetch(`${API_BASE}/upload?max_files=${Number(maxFiles)}`, {
      method: "POST",
      body: formData,
    });
  } catch (netErr) {
    throw new Error(
      "Cannot connect to the backend server. Please make sure the backend is running on http://127.0.0.1:8000."
    );
  }

  if (!resp.ok) {
    throw await handleResponseError(resp);
  }
  return resp.json();
}

/**
 * Fetch a stored review by ID.
 * @param {string} reviewId
 * @returns {Promise<object>} ReviewResponse
 */
export async function getReview(reviewId) {
  let resp;
  try {
    resp = await fetch(
      `${API_BASE}/review/${encodeURIComponent(reviewId)}`
    );
  } catch (netErr) {
    throw new Error(
      "Cannot connect to the backend server. Please make sure the backend is running on http://127.0.0.1:8000."
    );
  }

  if (!resp.ok) {
    throw await handleResponseError(resp);
  }
  return resp.json();
}


/**
 * List reviews from database with filtering, sorting, and pagination.
 * @param {object} params
 * @param {string} [params.search]
 * @param {string} [params.sortBy]
 * @param {number} [params.skip]
 * @param {number} [params.limit]
 * @returns {Promise<{total: number, items: object[]}>}
 */
export async function listReviewsApi({ search = "", sortBy = "date_desc", skip = 0, limit = 50 } = {}) {
  const query = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
    sort_by: sortBy,
  });
  if (search) {
    query.set("search", search);
  }

  const resp = await fetch(`${API_BASE}/reviews?${query.toString()}`);
  if (!resp.ok) {
    throw await handleResponseError(resp);
  }
  return resp.json();
}

/**
 * Delete a review from the database.
 * @param {string} reviewId
 * @returns {Promise<object>}
 */
export async function deleteReviewApi(reviewId) {
  const resp = await fetch(`${API_BASE}/review/${encodeURIComponent(reviewId)}`, {
    method: "DELETE",
  });
  if (!resp.ok) {
    throw await handleResponseError(resp);
  }
  return resp.json();
}

/**
 * Auth: Login with username/email & password.
 */
export async function loginUser(usernameOrEmail, password) {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
  });
  if (!resp.ok) throw await handleResponseError(resp);
  return resp.json();
}

/**
 * Auth: Register new account.
 */
export async function registerUser(username, email, password) {
  const resp = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  if (!resp.ok) throw await handleResponseError(resp);
  return resp.json();
}

/**
 * Auth: One-click instant demo login.
 */
export async function demoLoginUser() {
  const resp = await fetch(`${API_BASE}/auth/demo`, {
    method: "POST",
  });
  if (!resp.ok) throw await handleResponseError(resp);
  return resp.json();
}

