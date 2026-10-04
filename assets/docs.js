// Builds the sidebar table-of-contents from the real rendered headings in
// the article -- no hand-maintained list to go stale against the 50+
// sections in docs/ARCHITECTURE.md, no Jekyll plugin needed (GitHub Pages'
// plugin whitelist doesn't include jekyll-toc), just reads what's actually
// on the page. Also makes table rows that point at a section clickable.
(function () {
  const article = document.getElementById("docs-article");
  const tocList = document.getElementById("toc-list");
  if (!article || !tocList) return;

  const slug = (h, i) =>
    "s" + i + "-" + h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

  const h2s = article.querySelectorAll("h2");
  if (h2s.length === 0) {
    document.getElementById("docs-toc").style.display = "none";
  } else {
    // Short pages (Tools, Keybindings: a few sections with subsections) list
    // their h3s nested under each h2. Long ones (Architecture, Changelog)
    // stay h2-only, or the sidebar would be longer than the page.
    const nest = h2s.length <= 8;
    const headings = article.querySelectorAll(nest ? "h2, h3" : "h2");
    const ul = document.createElement("ul");
    let sub = null;
    headings.forEach((h, i) => {
      if (!h.id) h.id = slug(h, i);
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent;
      li.appendChild(a);
      if (h.tagName === "H3") {
        if (!sub) {
          sub = document.createElement("ul");
          sub.className = "toc-sub";
          (ul.lastElementChild || ul).appendChild(sub);
        }
        sub.appendChild(li);
      } else {
        sub = null;
        ul.appendChild(li);
      }
    });
    tocList.appendChild(ul);

    // Highlight whichever section is currently in view -- plain
    // IntersectionObserver, no framework needed for a page this size.
    const links = tocList.querySelectorAll("a");
    const byId = {};
    links.forEach((a) => (byId[a.getAttribute("href").slice(1)] = a));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const link = byId[entry.target.id];
          if (!link || !entry.isIntersecting) return;
          links.forEach((a) => a.classList.remove("active"));
          link.classList.add("active");
        });
      },
      { rootMargin: "0px 0px -80% 0px" }
    );
    headings.forEach((h) => observer.observe(h));
  }

  // Table rows with exactly one link to a section on this page (the Tools
  // overview: "vayu-elevate" -> its section) become clickable as a whole:
  // click or Enter scrolls there (smoothly, html has scroll-behavior) and
  // the target heading glows briefly so the eye lands on it.
  function go(hash) {
    const target = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (!target) return;
    history.pushState(null, "", hash);
    target.scrollIntoView({ block: "start" });
    target.classList.remove("flash");
    void target.offsetWidth; // restart the animation on repeat clicks
    target.classList.add("flash");
  }
  article.querySelectorAll("table tbody tr").forEach((tr) => {
    const inPage = Array.from(tr.querySelectorAll('a[href^="#"]'));
    if (inPage.length !== 1) return;
    const hash = inPage[0].getAttribute("href");
    tr.classList.add("row-link");
    tr.tabIndex = 0;
    tr.setAttribute("role", "link");
    tr.setAttribute("aria-label", "Go to " + inPage[0].textContent.trim());
    tr.addEventListener("click", (e) => {
      if (window.getSelection().toString()) return; // selecting text, not navigating
      e.preventDefault();
      go(hash);
    });
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        go(hash);
      }
    });
  });
})();
