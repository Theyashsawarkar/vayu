// Stable/Nightly filter for the Changelog page specifically -- a
// separate concern from assets/channel.js (that one swaps the install
// command on the homepage; this one hides/shows changelog sections).
// Kept as its own file for the same one-concern-per-file reason
// channel.js's own header comment gives.
//
// How the cut works: CHANGELOG.md is newest-first, with version-marker
// h2s (`## vX.Y.Z -- date` or `## vX.Y.Z-nightly -- date`) inserted
// above the dated entries they cover (see docs/VERSIONING.md). Since
// `development` (Nightly) is always even with or ahead of `main`
// (Stable), everything above the FIRST plain (non "-nightly") version
// marker -- reading top to bottom -- is content that hasn't shipped to
// Stable yet. Nightly shows the whole page; Stable hides that leading
// span and starts at that marker.
(function () {
  const article = document.getElementById("docs-article");
  if (!article) return;

  const NIGHTLY_RE = /^v(\d+)\.(\d+)\.(\d+)-nightly\b/;
  const STABLE_RE = /^v(\d+)\.(\d+)\.(\d+)\b/;

  const children = Array.from(article.children);
  const isVersionH2 = (el) => el.tagName === "H2" && STABLE_RE.test(el.textContent.trim());
  const isStableH2 = (el) => isVersionH2(el) && !NIGHTLY_RE.test(el.textContent.trim());

  // Real bug caught in testing: slicing from index 0 also hid the
  // toggle itself plus the page's own <h1>/intro paragraph, since
  // those sit before the first version marker too and a naive
  // "everything before the first stable h2" slice swept them up.
  // Only the actual version-marker span should ever be hidden -- start
  // at the first h2 that looks like a version marker at all, not at
  // the top of the article.
  const firstVersionIdx = children.findIndex(isVersionH2);
  const firstStableIdx = children.findIndex(isStableH2);
  // No plain version marker at all (e.g. nothing ever cut to Stable
  // yet) -- nothing to hide, both channels show the same thing, but
  // the toggle still renders so the choice is visible either way.
  const nightlyOnly =
    firstVersionIdx >= 0 && firstStableIdx > firstVersionIdx
      ? children.slice(firstVersionIdx, firstStableIdx)
      : [];
  if (!nightlyOnly.length) return;

  // docs.js builds the sidebar TOC from every h2 before this script
  // runs (it loads first), with no idea any of them are about to be
  // hidden -- without this, Stable's TOC would still list and link to
  // the nightly-only headings, scrolling to a display:none target that
  // visibly does nothing on click. Keep the same set of h2 ids hidden
  // in sync in both places.
  const nightlyOnlyIds = nightlyOnly.filter((el) => el.tagName === "H2" && el.id).map((el) => el.id);
  const tocList = document.getElementById("toc-list");

  const toggle = document.getElementById("changelog-channel-toggle");
  const descEl = document.getElementById("changelog-channel-desc");
  if (!toggle) return;
  const thumbEl = toggle.querySelector(".channel-thumb");
  const buttons = Array.from(toggle.querySelectorAll(".channel-btn"));

  const DESCRIPTIONS = {
    nightly: "Showing everything on <code>development</code>, including changes not yet released to Stable.",
    stable: "Showing only what's actually shipped in the latest tagged Stable release.",
  };

  function positionThumb(btn) {
    if (!thumbEl) return;
    thumbEl.style.width = btn.offsetWidth + "px";
    thumbEl.style.transform = "translateX(" + btn.offsetLeft + "px)";
  }

  function setChannel(channel, opts) {
    const focus = opts && opts.focus;
    const active = buttons.find((b) => b.dataset.channel === channel);
    if (!active) return;

    nightlyOnly.forEach((el) => {
      el.style.display = channel === "stable" ? "none" : "";
    });
    if (tocList) {
      nightlyOnlyIds.forEach((id) => {
        const link = tocList.querySelector('a[href="#' + id + '"]');
        const li = link ? link.closest("li") : null;
        if (li) li.style.display = channel === "stable" ? "none" : "";
      });
    }
    if (descEl) descEl.innerHTML = DESCRIPTIONS[channel];

    buttons.forEach((b) => {
      const isActive = b === active;
      b.classList.toggle("active", isActive);
      b.setAttribute("aria-selected", isActive ? "true" : "false");
      b.tabIndex = isActive ? 0 : -1;
    });
    positionThumb(active);
    if (focus) active.focus();
  }

  buttons.forEach((b, i) => {
    b.addEventListener("click", () => setChannel(b.dataset.channel));
    b.addEventListener("keydown", (e) => {
      let next = null;
      if (e.key === "ArrowRight") next = buttons[(i + 1) % buttons.length];
      else if (e.key === "ArrowLeft") next = buttons[(i - 1 + buttons.length) % buttons.length];
      else if (e.key === "Home") next = buttons[0];
      else if (e.key === "End") next = buttons[buttons.length - 1];
      if (next) {
        e.preventDefault();
        setChannel(next.dataset.channel, { focus: true });
      }
    });
  });

  window.addEventListener("resize", () => {
    const active = buttons.find((b) => b.classList.contains("active"));
    if (active) positionThumb(active);
  });

  // Defaults to Stable, matching the homepage install toggle's own
  // default -- Nightly (the fuller view, including unreleased changes)
  // is an explicit choice, not what a first-time visitor sees.
  setChannel("stable");
})();
