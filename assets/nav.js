// Menu for the top nav (index.html and the docs layout). Below 1024px
// (style.css), where the links don't fit on one row, they fold behind the
// menu button; this script adds .has-toggle, so without JS the links
// simply stay visible, wrapped. The button opens/closes them; a link, Esc
// or a tap outside closes them.
(function () {
  const nav = document.querySelector(".topnav");
  const btn = nav && nav.querySelector(".nav-toggle");
  if (!btn) return;
  nav.classList.add("has-toggle");

  function set(open) {
    nav.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", String(open));
    btn.setAttribute("aria-label", open ? "Close menu" : "Menu");
  }
  btn.addEventListener("click", () => set(!nav.classList.contains("open")));
  nav.querySelectorAll(".navlinks a").forEach((a) => a.addEventListener("click", () => set(false)));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("open")) {
      set(false);
      btn.focus();
    }
  });
  document.addEventListener("click", (e) => {
    if (nav.classList.contains("open") && !nav.contains(e.target)) set(false);
  });
})();
