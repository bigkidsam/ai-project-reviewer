// Login page logic — tabs, password visibility toggle, demo login, form submit
import { renderNav } from "./nav.js";
import { loginUser, registerUser, demoLoginUser } from "./api.js";
import { initScrollAnimations } from "./scroll-animations.js";

renderNav("login");
initScrollAnimations();

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const authAlert = document.getElementById("auth-alert");
const demoLoginBtn = document.getElementById("demo-login-btn");

// Tab switching (Login vs Register)
const tabLoginBtn = document.getElementById("tab-login-btn");
const tabRegisterBtn = document.getElementById("tab-register-btn");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");

if (tabLoginBtn && tabRegisterBtn) {
  tabLoginBtn.addEventListener("click", () => {
    tabLoginBtn.classList.add("active");
    tabRegisterBtn.classList.remove("active");
    tabLogin.classList.add("active");
    tabRegister.classList.remove("active");
    hideAlert();
  });

  tabRegisterBtn.addEventListener("click", () => {
    tabRegisterBtn.classList.add("active");
    tabLoginBtn.classList.remove("active");
    tabRegister.classList.add("active");
    tabLogin.classList.remove("active");
    hideAlert();
  });
}

// Password visibility toggling
document.querySelectorAll(".password-toggle-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetId = btn.dataset.target;
    const input = document.getElementById(targetId);
    if (!input) return;
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    btn.textContent = isPassword ? "🙈" : "👁️";
  });
});

function showAlert(msg, type = "error") {
  if (!authAlert) return;
  authAlert.className = `alert alert-${type}`;
  authAlert.textContent = msg;
  authAlert.classList.remove("hidden");
}

function hideAlert() {
  if (authAlert) authAlert.classList.add("hidden");
}

function handleAuthSuccess(data) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("user_name", data.username);
  localStorage.setItem("user_email", data.email);

  showAlert(`Success! Welcome, ${data.username}. Redirecting…`, "success");
  setTimeout(() => {
    window.location.href = "/";
  }, 1000);
}

// 1. Login Submit
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();
    const usernameOrEmail = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;

    const btn = document.getElementById("login-submit-btn");
    btn.disabled = true;
    btn.textContent = "Authenticating…";

    try {
      const data = await loginUser(usernameOrEmail, password);
      handleAuthSuccess(data);
    } catch (err) {
      showAlert(err.message || "Invalid credentials.");
      btn.disabled = false;
      btn.textContent = "🔑 Sign In";
    }
  });
}

// 2. Register Submit
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAlert();
    const username = document.getElementById("reg-username").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;

    const btn = document.getElementById("register-submit-btn");
    btn.disabled = true;
    btn.textContent = "Creating Account…";

    try {
      const data = await registerUser(username, email, password);
      handleAuthSuccess(data);
    } catch (err) {
      showAlert(err.message || "Registration failed.");
      btn.disabled = false;
      btn.textContent = "✨ Create Free Account";
    }
  });
}

// 3. One-Click Demo Login
if (demoLoginBtn) {
  demoLoginBtn.addEventListener("click", async () => {
    hideAlert();
    demoLoginBtn.disabled = true;
    demoLoginBtn.textContent = "⚡ Signing in as Guest…";

    try {
      const data = await demoLoginUser();
      handleAuthSuccess(data);
    } catch (err) {
      showAlert(err.message || "Demo login failed.");
      demoLoginBtn.disabled = false;
      demoLoginBtn.textContent = "⚡ One-Click Demo Guest Login";
    }
  });
}
