// Shared navigation bar — glass navbar with theme toggle and mobile menu
import { initTheme, toggleTheme, getTheme } from "./theme.js";

// Initialize theme immediately
initTheme();

/**
 * Render the navigation bar into the page.
 * @param {string} activePage - one of: "home", "review", "results", "history", "about"
 */
export function renderNav(activePage) {
  const nav = document.getElementById("main-nav");
  if (!nav) return;

  const links = [
    { id: "home", label: "Home", href: "/index.html" },
    { id: "review", label: "New Review", href: "/review.html" },
    { id: "history", label: "History", href: "/history.html" },
    { id: "about", label: "About", href: "/about.html" },
  ];

  const linkHtml = links
    .map(
      (l) =>
        `<li><a href="${l.href}" class="${l.id === activePage ? "active" : ""}">${l.label}</a></li>`
    )
    .join("");

  const userName = localStorage.getItem("user_name");
  const authActionHtml = userName
    ? `<div class="user-nav-badge">
        <span class="user-avatar">👤</span>
        <span class="user-name">${userName}</span>
        <button class="btn btn-ghost btn-xs" id="logout-btn" title="Sign out" style="padding: 2px 6px; font-size: 0.75rem;">Logout</button>
       </div>`
    : `<a href="/login.html" class="btn btn-secondary btn-sm" style="padding: 6px 14px; font-size: 0.8125rem;">Sign In</a>`;

  const themeIcon = getTheme() === "dark" ? "☀️" : "🌙";

  nav.innerHTML = `
    <div class="nav-inner">
      <a href="/index.html" class="nav-brand">
        <span class="nav-brand-icon">AI</span>
        <span>Project Reviewer</span>
      </a>
      <ul class="nav-center" id="nav-links">
        ${linkHtml}
      </ul>
      <div class="nav-actions">
        ${authActionHtml}
        <button class="theme-toggle" id="theme-toggle-btn" title="Toggle theme" aria-label="Toggle theme">
          <span id="theme-toggle-icon">${themeIcon}</span>
        </button>
        <button class="nav-mobile-toggle" id="nav-mobile-btn" title="Menu" aria-label="Menu">☰</button>
      </div>
    </div>
  `;

  // Logout listener
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_name");
      localStorage.removeItem("user_email");
      window.location.reload();
    });
  }


  // Theme toggle
  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    toggleTheme();
  });

  // Mobile menu toggle
  document.getElementById("nav-mobile-btn").addEventListener("click", () => {
    document.getElementById("nav-links").classList.toggle("mobile-open");
  });

  // Close mobile menu on link click
  document.querySelectorAll("#nav-links a").forEach((link) => {
    link.addEventListener("click", () => {
      document.getElementById("nav-links").classList.remove("mobile-open");
    });
  });

  // Navbar scroll effect
  let ticking = false;
  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        if (window.scrollY > 10) {
          nav.classList.add("scrolled");
        } else {
          nav.classList.remove("scrolled");
        }
        ticking = false;
      });
      ticking = true;
    }
  });
}
