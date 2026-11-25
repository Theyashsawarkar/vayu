// Shows the latest real released version next to the hero H1 -- fetched
// live from GitHub's tags API rather than hand-typed into index.html
// (which isn't Jekyll-processed at all, so there's no templating
// available to inject it at build time either way), so it never goes
// stale after a release the way a hardcoded string reliably would.
//
// Doesn't trust the API's own array order as "newest first" (not a
// documented guarantee) -- parses every "vX.Y.Z"-shaped tag name and
// picks the highest by real numeric semver comparison instead.
(function () {
  const el = document.getElementById("version-badge");
  if (!el) return;

  fetch("https://api.github.com/repos/Theyashsawarkar/vayu/tags")
    .then((r) => (r.ok ? r.json() : []))
    .then((tags) => {
      let best = null;
      for (const t of tags) {
        const m = /^v(\d+)\.(\d+)\.(\d+)$/.exec(t.name || "");
        if (!m) continue;
        const parts = [Number(m[1]), Number(m[2]), Number(m[3])];
        if (
          !best ||
          parts[0] > best.parts[0] ||
          (parts[0] === best.parts[0] && parts[1] > best.parts[1]) ||
          (parts[0] === best.parts[0] && parts[1] === best.parts[1] && parts[2] > best.parts[2])
        ) {
          best = { name: t.name, parts };
        }
      }
      if (best) {
        el.textContent = best.name;
        const wrap = document.getElementById("version-badge-wrap");
        if (wrap) wrap.hidden = false;
      }
    })
    .catch(() => {
      // No network / rate-limited / offline -- leave the badge empty
      // rather than show something possibly wrong.
    });
})();
