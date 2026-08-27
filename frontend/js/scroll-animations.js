// Scroll-reveal animations using Intersection Observer
// Elements with [data-animate] get .visible when they enter viewport

/**
 * Initialize scroll-reveal animations on the page.
 * Call once after DOM is ready.
 */
export function initScrollAnimations() {
  const elements = document.querySelectorAll("[data-animate]");
  if (!elements.length) return;

  // Respect reduced-motion preference
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
    elements.forEach((el) => el.classList.add("visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.1,
      rootMargin: "0px 0px -40px 0px",
    }
  );

  elements.forEach((el) => observer.observe(el));
}

/**
 * Add stagger classes to direct children of a container.
 * @param {string} selector - CSS selector for the parent container
 */
export function staggerChildren(selector) {
  const parent = document.querySelector(selector);
  if (!parent) return;
  Array.from(parent.children).forEach((child, i) => {
    child.classList.add(`stagger-${Math.min(i + 1, 8)}`);
  });
}

/**
 * Animate a counter from 0 to target value.
 * @param {HTMLElement} el - Element to update textContent
 * @param {number} target - Target number
 * @param {number} duration - Animation duration in ms
 * @param {string} suffix - Optional suffix (e.g. "%")
 * @param {number} decimals - Decimal places
 */
export function animateCounter(el, target, duration = 1200, suffix = "", decimals = 0) {
  if (!el || target == null || isNaN(target)) return;
  const start = performance.now();
  const initial = 0;

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = initial + (target - initial) * eased;
    el.textContent = current.toFixed(decimals) + suffix;
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}
