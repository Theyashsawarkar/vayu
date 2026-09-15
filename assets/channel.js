// Stable/Nightly channel toggle for the install snippet. Swaps the
// generated command -- install.sh now accepts "stable"/"nightly" as its
// own $1, skipping its interactive prompt entirely (see CHANGELOG.md) --
// and fetches each channel's real current version live from GitHub's
// tags API, the same live-fetch approach version.js already uses for the
// hero badge, kept as a separate script rather than folded into it:
// version.js has exactly one job (the single hero badge, Stable only);
// this one has a different one (two channels, two different tag-name
// shapes to match), matching this site's existing one-concern-per-file
// pattern (copy.js/version.js).
(function () {
  const COMMANDS = {
    stable: "bash <(curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/vayu/main/install.sh) stable",
    nightly: "bash <(curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/vayu/main/install.sh) nightly",
  };
  // innerHTML, not textContent -- these intentionally carry a real
  // <code> tag (already styled globally, see style.css's own generic
  // `code` rule) rather than plain branch-name text.
  const DESCRIPTIONS = {
    stable: "Stable tracks <code>main</code> — tagged releases only, the safest choice.",
    nightly: "Nightly tracks <code>development</code> — day-to-day work, may break.",
  };

  const codeEl = document.getElementById("install-cmd");
  const descEl = document.getElementById("channel-desc");
  const snippetEl = codeEl ? codeEl.closest(".install-snippet") : null;
  const toggleEl = document.querySelector(".channel-toggle");
  const thumbEl = toggleEl ? toggleEl.querySelector(".channel-thumb") : null;
  const buttons = Array.from(document.querySelectorAll(".channel-btn"));
  if (!codeEl || !buttons.length) return;

  // Sliding pill position -- measured in real px (offsetLeft/
  // offsetWidth) rather than a fixed 50%, since "Stable" and "Nightly"
  // are different widths, more so once their live version text below
  // fills in asynchronously (see the tags fetch further down).
  function positionThumb(btn) {
    if (!thumbEl) return;
    thumbEl.style.width = btn.offsetWidth + "px";
    thumbEl.style.transform = "translateX(" + btn.offsetLeft + "px)";
  }

  function setChannel(channel, opts) {
    const focus = opts && opts.focus;
    const active = buttons.find((b) => b.dataset.channel === channel);
    if (!active) return;

    // Quick cross-fade rather than an instant text jump -- fade out,
    // swap the actual content once it's invisible, fade back in.
    if (descEl) descEl.classList.add("fade");
    if (snippetEl) snippetEl.classList.add("fade");
    setTimeout(() => {
      // textContent, not innerHTML, for the command itself -- it's a
      // real shell command a real person is about to paste into a real
      // terminal; nothing here should ever be interpreted as markup.
      codeEl.textContent = COMMANDS[channel];
      if (descEl) {
        descEl.innerHTML = DESCRIPTIONS[channel];
        descEl.classList.remove("fade");
      }
      if (snippetEl) snippetEl.classList.remove("fade");
    }, 120);

    buttons.forEach((b) => {
      const isActive = b === active;
      b.classList.toggle("active", isActive);
      b.setAttribute("aria-selected", isActive ? "true" : "false");
      // Roving tabindex -- the real ARIA tab pattern: only the active
      // tab is in the normal Tab order, arrow keys move between them.
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

  // Version text (fetched below) can change each button's width after
  // the thumb was first positioned -- keep it in sync, plus on resize.
  window.addEventListener("resize", () => {
    const active = buttons.find((b) => b.classList.contains("active"));
    if (active) positionThumb(active);
  });

  setChannel("stable");

  // Real current version per channel, fetched live rather than
  // hardcoded (index.html isn't Jekyll-processed, so there's no
  // build-time templating available to inject it either way -- same
  // reasoning version.js's own comment already gives for the hero
  // badge). Stable is the highest plain "vX.Y.Z" tag (identical
  // comparison logic to version.js); Nightly is the highest
  // "vX.Y.Z-nightly" tag specifically -- matched by its own explicit
  // pattern, not just "any tag name containing -nightly", so an
  // unrelated differently-shaped tag can never get picked by accident.
  const stableEl = document.getElementById("version-stable");
  const nightlyEl = document.getElementById("version-nightly");
  if (!stableEl && !nightlyEl) return;

  function cmpParts(a, b) {
    for (let i = 0; i < 3; i++) {
      if (a[i] !== b[i]) return a[i] - b[i];
    }
    return 0;
  }

  fetch("https://api.github.com/repos/Theyashsawarkar/vayu/tags")
    .then((r) => (r.ok ? r.json() : []))
    .then((tags) => {
      let bestStable = null;
      let bestNightly = null;
      for (const t of tags) {
        const name = t.name || "";
        let m = /^v(\d+)\.(\d+)\.(\d+)$/.exec(name);
        if (m) {
          const parts = [Number(m[1]), Number(m[2]), Number(m[3])];
          if (!bestStable || cmpParts(parts, bestStable.parts) > 0) {
            bestStable = { name, parts };
          }
          continue;
        }
        m = /^v(\d+)\.(\d+)\.(\d+)-nightly$/.exec(name);
        if (m) {
          const parts = [Number(m[1]), Number(m[2]), Number(m[3])];
          if (!bestNightly || cmpParts(parts, bestNightly.parts) > 0) {
            bestNightly = { name, parts };
          }
        }
      }
      if (bestStable && stableEl) stableEl.textContent = bestStable.name;
      if (bestNightly && nightlyEl) nightlyEl.textContent = bestNightly.name;
      // Version text just changed each button's width -- the thumb was
      // already positioned against the old (shorter) width above.
      const active = buttons.find((b) => b.classList.contains("active"));
      if (active) positionThumb(active);
    })
    .catch(() => {
      // No network / rate-limited / offline -- leave version labels
      // empty rather than show something possibly wrong, same choice
      // version.js's own hero badge already makes.
    });
})();
