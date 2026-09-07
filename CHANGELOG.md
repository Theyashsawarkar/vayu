# Changelog

Notable changes to this setup, in human terms — what changed, why, and what broke
along the way. Newest first. Version markers (`## vX.Y.Z`) mark release
boundaries on top of the dated entries -- see `docs/VERSIONING.md` for the
full branch/release process.

## 2026-09-07 (waybar: fixed the clock/date pill's intermittently-vanishing left corner)

Reported bug: the time+date cluster in the center of the bar would
sometimes have its left corner just not render, then look normal again
after a while -- not constant, not reproducible on demand.

Root cause: `#clock` (the date pill) had `margin-left: -8px`, deliberately
pulling it left of its own allocated box to sit flush against `clock#time`
(the plain-text time to its left) so the pair would read as one unit. A
negative margin means GTK paints outside the module's own allocated
rectangle -- and `#clock` lives in `modules-center`, which waybar
re-centers on the bar every time `modules-left`/`modules-right`'s total
width changes. `network#speed` right there in `modules-left` already has
its own comment admitting its text width "changes digit count constantly"
(12KB vs 1.2MB vs 999B) -- so the center group was being re-laid-out
continuously, and the negatively-margined region only reliably repainted
on some of those passes, not all. That's exactly "sometimes doesn't
appear, then becomes normal" instead of a constant glitch.

Fixed by dropping the margin to `0` instead of `-8px` -- still tighter
than the shared `4px` every other pill gets, but never painting outside
`#clock`'s own box, so there's nothing left for a relayout to intermittently
clip. Restarted waybar for real to apply it (config/CSS edits don't
hot-reload -- confirmed again, same as the network#speed investigation
already noted elsewhere in this file); came back up clean, no CSS parse
warnings, bar configured normally. Visual confirmation of the fix itself
(whether the corner still ever vanishes) is still pending -- that part
needs eyes on the actual screen, not just a clean process restart.

## 2026-09-07 (music-search.py: play by default, mpv, audio/video toggle)

Mod+Shift+Y's Enter used to download an mp3 into ~/Music before you could
hear or see anything -- changed so it plays the result immediately
instead, via mpv (already installed, v0.41.0, ships its own yt-dlp hook
so a bare `mpv <youtube-url>` resolves and plays with no extra plumbing --
confirmed live, not assumed). Chose mpv over reusing MPD/rmpc
specifically because MPD's whole design center is a curated persistent
library, the wrong tool for "stream this one URL right now, don't add it
to anything".

Whether Enter plays audio-only or a real video window is controlled by a
new persisted toggle, `media-play-mode.sh` (Mod+Ctrl+Y) -- same
state-file pattern as `notification-mode.sh`/`theme-toggle.sh`. The
active mode is echoed straight into the wofi search prompt itself
("Search YouTube (audio)..." / "(video)...") so it's never a guess which
one is live. The original download-to-library behavior wasn't removed,
just moved off the default action: `--download` (now Mod+Shift+Ctrl+Y)
reuses the same search/pick code and does exactly what this script
always did.

A real bug caught during verification: mpv/yt-dlp's own "best" format
selection picked a 4K stream with zero regard for whether this machine
could actually decode it smoothly (dropped-frame count climbed
continuously in a live test) -- video mode now explicitly caps at 1080p
instead of trusting the untouched default.

Verified end-to-end through the actual sway keybinding's real code path,
not just raw mpv calls in isolation: `wtype` simulated real keystrokes
into the live wofi popups (typing a search query, picking a result) for
both audio and video modes and for `--download`, and mpv's own JSON IPC
socket confirmed real playback progress (`time-pos` actually advancing),
not just a process staying alive. Video mode's window was confirmed via
`swaymsg -t get_tree` mid-playback: real app_id `mpv`, floating,
correctly sized and centered per the new `for_window` rule. See
`docs/ARCHITECTURE.md`'s own entry on this for the full detail. MINOR
bump: a real new capability (play + a toggle that didn't exist before),
not just a fix.

## v1.5.1 -- 2026-09-04

Fixed two real flash bugs, each with a specific, identified cause rather
than a general polish pass: `background-attachment: fixed` was forcing a
full repaint of the body's (expensive, multi-gradient + noise-textured)
background on every scroll position change, visible as a white flash on
the Features anchor jump; and the carousel's transition animated `filter`
alongside `transform`/`opacity`, and unlike those two, `filter` isn't
compositor-only, so it forced a real repaint every frame. Also added
`scroll-behavior: smooth` for anchor links, `img.decode()` gating before
carousel autoplay starts, and the Cross-Document View Transitions API for
genuine cross-page navigation fades. PATCH bump: fixing real, reported
rendering bugs, not new capability.

## v1.5.0 -- 2026-09-04

Four direct fixes/additions: the screenshot carousel felt rushed (slower
dwell, gentler transition curve); clicking "Features" in the nav scrolled
past the section's own title, hidden under the sticky nav (fixed with
`scroll-margin-top`, applies to any future anchor-linked section too); a
live version badge next to the hero title, fetched from GitHub's tags API
at page load rather than hand-typed (real semver comparison, not just
trusting API array order); and the wind-emoji brand icon dropped for a
text-only wordmark (echoing the H1's own serif+gradient treatment), with a
real bug fixed along the way -- it was inheriting the site-wide link-hover
underline. MINOR bump: the version badge is genuine new capability, not
just a fix.

## v1.4.0 -- 2026-09-04

A full glassmorphism redesign of the hero, matching a shared reference
mockup's style (confirmed as a Gemini-generated AI image first, and
deliberately skipped the parts of its description that read as AI-mockup
filler unrelated to an actual website -- a fake OS status bar, a made-up
app name, gold/brass bars -- rather than implementing every literal
detail). Page-wide dark charcoal-to-amethyst gradient background with a
subtle grain texture; hero content now lives inside a real glass card
(background blur, inner highlight, deep shadow, ambient glow); wordmark
switched to a serif font with a purple-to-silver gradient; buttons got
real glow and a genuine frosted-glass ghost button; the screenshot gallery
rebuilt as an actual layered 3D card-deck instead of a flat single-image
swap. MINOR bump: a real new visual capability (the glass card system,
the card-deck carousel), not just a bug fix.

## v1.3.2 -- 2026-09-04

Direct follow-up: the scroll-pin from v1.3.1 felt sluggish, and tying page
scroll to the screenshot gallery was the wrong idea in the first place --
"let the scroll behave normally... if a user want to see the screenshots
then he can just do something there." Removed `.hero-zone`/`position:
sticky` entirely; page scroll is now completely untouched by the hero.
`assets/carousel.js` rewritten as a fully self-contained autoplay carousel
(3.2s timer, pauses on hover, real clickable dots) with no scroll listener
at all. Added a soft ambient gradient glow behind the hero content and a
subtle fade+rise entrance animation for a grander first impression, per
direct request. PATCH bump: fixing a UX regression just shipped, not new
capability.

## v1.3.1 -- 2026-09-04

Fixed two real bugs in the hero (copy button drifting on horizontal code
scroll, the page visibly scrolling while images changed underneath it) and
redesigned the layout to match direct feedback -- a real scroll-pin
carousel instead of a 3D wheel, eyebrow repositioned, install snippet
de-duplicated, two more screenshots. PATCH bump: fixes to real, reported
UX bugs plus refinement of an existing feature, not a new capability.

## 2026-09-04 (hero redesign: scroll-pinned slide carousel, real layout fixes)

Direct feedback on the hero: the copy button drifted toward the middle on
horizontal code-block scroll, the 3D image wheel made the page visibly
scroll down while images changed underneath it ("bad UX... the page should
stay put"), images crowded the text column, the eyebrow line competed with
the title for top billing, and the install snippet was redundant with the
one already in the #install section below.

**Copy button fix**: it's an absolutely-positioned child of `<pre>`, and a
scrolling `<pre>` (`overflow-x: auto`) drags its own absolutely-positioned
children along with the scrolled content. Moved `overflow-x` to the inner
`<code>` element instead, in both `assets/style.css` and `assets/docs.css`
-- `<pre>` itself stays static now, so the button never moves regardless of
how far the code scrolls.

**Real scroll-pin, not scroll-jacking**: `.hero-zone` (350vh) wraps the
actual hero, which is `position: sticky` -- while the user scrolls through
that extra height, the hero visually stays in place, and
`assets/carousel.js` (rewritten) maps scroll progress *within* the zone to
slide+fade transitions between the 5 screenshots via CSS class changes only
(`.active`/`.prev`). Never calls `scrollTo`/`preventDefault` -- the page
keeps scrolling completely normally the whole time, this only ever reads
`scrollY`. Once scrolled past the zone, the sticky pin releases on its own
(plain CSS behavior, no JS needed for that part) and the page continues
into Features. Disabled entirely below 860px -- mobile viewport height
isn't stable enough (address-bar collapse changes `100vh` mid-scroll on
most mobile browsers) for a pin effect to be reliable; falls back to plain
static flow showing just the first screenshot, via the same
`scrollableRange<=0` guard already in the carousel math rather than a
separate mobile code path.

**Layout**: eyebrow moved from above the title to below the tagline (no
longer fighting the title for attention), the hero's own install-snippet
code block removed entirely (kept only in #install below, no duplication),
CTA row pinned to the bottom of the text column via `margin-top: auto`.
Structure top-to-bottom now matches what was asked for directly: title
(bigger) -> tagline -> eyebrow -> CTA row, images on the right.
Hero-text/hero-image gap increased (3.5rem -> 5.5rem) and the image
column's flex-basis reduced (480px -> 400px) for real breathing room.

**Two more screenshots** (keybind-search's live fuzzy list, the emoji
picker) join the existing three for a 5-image gallery, each with its own
slide-dot indicator. Tried `notification-history.py` first but it was
empty on this machine (nothing to show) -- swapped for keybind-search
since it's guaranteed non-empty, real, colorful content instead of an
empty list.

Verified live the way every other site change this session has been:
pushed, waited for a real build, then pulled the actual served HTML/CSS
and confirmed the DOM structure (image order, eyebrow's new position
relative to the tagline and CTA row, the install-snippet's removal from
the hero, all 5 images and the fixed copy-button CSS deployed correctly).
The visual feel of the scroll-pin itself isn't something `curl` can verify
-- confirmed everything the tooling here can check (structure, CSS, JS
syntax, live deployment), but the actual in-browser scroll experience is
worth checking directly.

## v1.3.0 -- 2026-09-02

A new Keybindings page (generated from the same live config parsing the
desktop's own keybind-search tool uses), a real thumbnail-quality fix in
music-search.py, a hero redesign (multi-screenshot scroll-driven rotation,
a much shorter tagline, cleaner header and feature grid), copy-to-clipboard
buttons site-wide, and a deep, multi-round fix for the CHANGELOG/
Architecture pages' rendering -- what looked like one bug turned out to be
several, ending in a genuinely reusable lesson about how kramdown handles
angle-bracket text differently from GitHub's own renderer. MINOR bump: real
new capability (the keybindings page, the hero redesign, copy buttons) plus
real, previously-invisible rendering bugs fixed.

## 2026-09-02 (site polish: keybindings page, real bugs found and fixed, hero redesign)

A batch of direct site feedback: fix the CHANGELOG page's real bugs, add a
proper keybindings page with its own header entry, fix a pixelated thumbnail
in the music player, add copy buttons to code blocks, redesign the hero with
multiple screenshots in a scroll-driven rotating wheel, cut the tagline down
to one line, redesign the header (no bottom border) and the feature grid.

**docs/KEYBINDINGS.md**: new page, every Sway and Tmux keybinding, generated
from the same live parsing `scripts/.local/bin/keybind-search.py` already
does (real config lines + their own comments) rather than hand-typed
separately. Wired into the header nav and homepage doc-card grid on both
`index.html` and the shared `_layouts/docs.html`.

**music-search.py**: thumbnail pixelation fixed -- `mqdefault.jpg` (320x180)
swapped for `hqdefault.jpg` (480x360), confirmed reliably available the same
fixed-URL way the original was verified, a real (measured, not assumed)
quality-vs-latency tradeoff documented in the code.

**Hero redesign**: tagline cut from three sentences to one line, per direct
feedback ("small to the point and sweet"). Two new screenshots (wofi
launcher, power menu -- both safe to capture directly, no window content
exposed) join the existing desktop shot in a real CSS 3D "wheel"
(`assets/carousel.js`) that rotates with scroll position, pure scroll-read,
never scroll-jacks. Header switched to a floating pill nav with no hard
border-bottom (same rounded-module language `waybar` already uses on the
real desktop). Feature grid got a corner-glow accent, hover lift, and a
small icon badge per card instead of a plain left-border stripe.

**Copy-to-clipboard button** (`assets/copy.js`) on every code block
site-wide -- one script, works on the homepage's install snippets and every
doc page's real fenced code blocks alike.

**The CHANGELOG page's "real bugs" turned out to be much bigger than they
first looked**, and took several genuine wrong turns to fully resolve --
worth recording in full since each one taught something different about how
kramdown actually behaves, not just what the fix was:

1. A duplicate h1 heading (the layout rendered its own `page.title` *and* the
   content's own `# Title` line rendered a second one) -- straightforward,
   fixed by removing the layout's synthetic heading.
2. Fenced bash code blocks rendering as literal backtick text --
   `markdown: kramdown` / `kramdown: {input: GFM}` added to `_config.yml`
   (never explicitly set once the built-in Jekyll theme, which used to
   provide this implicitly, was replaced by the custom layout).
3. That config fix wasn't sufficient alone -- kramdown also requires blank-
   line separation between a fence and surrounding paragraph text to
   recognize it as a block at all (GitHub's own renderer is more lenient,
   which is why this was invisible reading the docs natively on GitHub).
   Fixed with a script that inserts blank lines around every fence --
   a first, buggier version of that script didn't track fence open/close
   state and inserted blank lines *inside* fences instead; caught via
   spot-check before it shipped, reverted, redone correctly.
4. Still 8 fences broken after that -- 3 more existed, indented 2 spaces as
   continuation content inside bullet list items, which the "starts with
   backticks" detection never matched (required column 0). Dedented all
   three to top-level fences rather than fight kramdown's exact nested-
   list-continuation indentation rules.
5. **The actual root cause of the page-wide cascading failure**, found only
   after all of the above still left entire sections rendering as
   completely raw, unprocessed markdown (not just fences -- bold, inline
   code, and headings too): a literal angle-bracket-wrapped placeholder
   inside backticks (`on-notify=exec paplay` followed by the word "file"
   wrapped in angle brackets), a notation this repo's prose uses
   throughout for "fill in your own value" (the words name, pid, id,
   etc., each the same way). Backticks do **not** protect against this
   the way they protect against Liquid tags -- kramdown's HTML-tag
   detection appears to run before code-span parsing fully isolates the
   content, sees the opening angle bracket as what looks like the start
   of a real tag, finds no matching closing tag anywhere in the rest of
   the document, and stops treating anything after that point as
   markdown at all. Confirmed by binary-searching the actual built HTML
   for the exact transition point between correctly-rendered and literal
   output, not guessed.
6. Fixed by removing the angle brackets from every genuine placeholder
   (just the bare word "file" instead of wrapping it) rather than entity-
   encoding them -- tried HTML entities first, which avoided the cascade
   but produced a *new*, different cosmetic bug: kramdown's code-span
   rendering correctly escapes its own content, including a literal
   ampersand, so the entity code itself became visible literal text in
   the browser instead of rendering back to a bracket character.
7. A handful of these weren't generic placeholders at all -- a real Rust
   generic type reference (`Property`'s song-typed variant) and rmpc's
   own angle-bracket RON keybind notation for its Escape and Ctrl-C
   entries (documented directly from its config.ron) lost real meaning
   when flattened the same way. Tried backslash-escaping the brackets
   next, which avoided the cascade but hit a third cosmetic bug:
   CommonMark spec says backslash escapes aren't processed inside code
   spans, so the literal backslash character itself showed up in the
   rendered page. Settled on plain English instead ("its Esc key entry",
   "the Song-typed Property::as_string variant") -- no bracket notation
   left to fight kramdown's parsing order over at all.
8. Also caught, separately: the earlier fix's regex only ever matched
   opening-tag-shaped patterns, so a quoted example of a real built page's
   title tag (opening and closing) had its opening half stripped while
   the closing half was left dangling, unmatched, in the text -- the
   exact same class of problem as the original bug, just self-inflicted
   this time. Reworded rather than re-escaped.

Every one of these eight was verified against the real, live-built HTML
after each fix -- not the source markdown, not assumed correct from the
config -- specifically because step 5's whole discovery only happened by
checking real output and finding it silently wrong days after step 2-4's
fixes had already shipped and looked fine from a cursory glance.

## v1.2.4 -- 2026-09-01

Direct feedback pointed at the live Architecture page: "optimize this ui and
make it more asthetic. instead of putting it in the table find other way to
better structure this page instead." The "Package map" table really was a
bad fit for its own content, not just visually plain -- 20 rows ranging from
a 6-character description to one over 2,400 characters, all forced into the
same fixed table columns.

Replaced it with a responsive card grid + native `details` for the five
genuinely long entries, entirely inside `docs/ARCHITECTURE.md` itself (one
source of truth, GitHub-native view benefits too) -- parsed the original
table with a small script rather than retype ~1,800 words by hand, verified
no content was corrupted or dropped before trusting it.

Added a real custom layout (`_layouts/docs.html`, `assets/docs.css`,
`assets/docs.js`) instead of the built-in Jekyll theme: a sidebar table of
contents built from the page's own real `h2` elements at view time (not a
hand-maintained list to drift out of sync with a 58-section document), with
scroll-based active-section highlighting, and the same Catppuccin Mocha
palette already used on the homepage. Applied via `_config.yml`'s
`defaults:` key (scoped per file path) rather than front matter in the
source files -- the same GitHub-native-rendering constraint hit once already
for `README.md` applies to `CHANGELOG.md`/`docs/*.md` too (all linked
directly from `README.md`), and `defaults:` assigns a layout/title with zero
change to the source file itself.

Considered a more complex transclusion-based alternative first (wrapper
pages + `include_relative`), built and started testing it, then discarded it
once `defaults:` was confirmed to solve the same problem with no new files
and no indirection.

Verified live: pushed straight to `main` specifically to get a real Pages
build to test against, polled for a real `"status":"built"`, then pulled the
actual built HTML for all three doc pages and grepped it directly -- correct
per-file titles, the new layout/cards present in the real output, all 20
package cards accounted for, and markdown processing inside the `details`
blocks confirmed via real `code`/`em` tags in the output, not literal
markdown characters.

## v1.2.3 -- 2026-09-01

Corrected a real inaccuracy in the previous release's own documentation,
found via the site's own live verification: `docs/ARCHITECTURE.md` claimed
`README.md` was reachable as a Jekyll-rendered page on the docs site --
`README.html` actually 404'd. Tried the standard fix and reverted it after
checking GitHub's own README renderer first (it renders unstripped front
matter as literal horizontal rules on the actual repo page). No content
change to `README.md` itself (net zero diff from v1.2.2). PATCH bump:
correcting a wrong claim in already-published documentation.

## v1.2.2 -- 2026-09-01

Renamed the repository to Vayu (after the Hindu god of wind -- Sway
tiles/moves windows the same way air moves) and replaced the docs site's
homepage with a real, custom, dark hero-layout page (name/tagline/install on
the left, a real desktop screenshot on the right) instead of the previous
stacked README-as-homepage layout, with the rest of the site switched to a
dark Jekyll theme to match. PATCH bump: identity/presentation and repo-
completeness work, not a change to how the desktop itself behaves.

## 2026-09-01 (renamed to Vayu, and a real custom dark hero-layout site)

Direct ask: rename the repo to something from Hindu mythology/history, make
the docs site dark instead of light, and redesign it around a specific
pattern -- name/headline on the left, a desktop image on the right, not the
previous stacked README-as-homepage layout.

**Renamed `arch_sway_setup` -> `vayu`** (`gh repo rename`), after Vayu, the
Hindu god of wind -- Sway tiles/arranges windows the same way air moves, and
"sway" itself means exactly that. Updated the local `origin` remote to the
new URL and confirmed a fetch actually works through it (not just assumed
the rename propagated). Propagated the new name everywhere it was actually
referenced: `install.sh`'s own curl one-liner and `REPO_URL`, and every
`github.com`/`raw.githubusercontent.com` link in `README.md` -- grepped the
whole repo for the old name first to find all of them, not guessed. Set the
repo's GitHub description and homepage URL to match.

**Replaced the stacked README-as-homepage site with a real custom
`index.html`** (repo root, no Jekyll front matter, so Pages serves it
untouched instead of wrapping it in a theme layout) -- a proper hero section
(name + tagline + install snippet + CTAs on the left, a real desktop
screenshot on the right), a feature grid, and links out to the full docs.
Dark by default, using this desktop's own Catppuccin Mocha palette directly
(the same colors already in `rmpc`'s own theme, `waybar/style.css`, etc.) so
the site reads as part of the same thing it documents rather than a generic
theme wrapper. Switched the Jekyll theme used for the *other* pages
(`CHANGELOG.html`, `docs/ARCHITECTURE.html`, `docs/VERSIONING.html`) from
`jekyll-theme-cayman` (light) to `jekyll-theme-slate` (one of GitHub Pages'
own built-in dark themes) so the whole site is consistently dark, not just
the new homepage.

**The desktop screenshot needed real care, not just a `grim` call.**
Checked the actual window tree first and found the real session had a
browser window with visible content on another workspace and a live tmux
pane on the currently-focused one -- a floating `rmpc` window doesn't cover
the full screen, so screenshotting it directly would have left tmux visible
in the margins. Switched to a genuinely empty workspace, moved `rmpc` there
via the scratchpad (confirmed via `swaymsg -t get_tree` that it was the
*only* thing on that workspace before capturing), then restored the
original workspace/window state afterward. Resized/compressed the result
(1920x1080 PNG -> 1600x900 JPEG, ~230KB) for a reasonable page weight.

Verified live the same way as every other change this session: pushed,
waited for the real Jekyll build to report `"status":"built"` (not just a
successful API response), then `curl`'d the actual homepage and every linked
doc page for real HTTP 200s and real content, not assumed correct from the
config alone -- caught one real miss this way: `README.html` 404'd (Jekyll
skips files with no front matter, same rule used deliberately for
`index.html`, just biting somewhere unwanted this time). Tried the standard
fix (empty front matter) and reverted it after checking GitHub's own README
renderer first -- it doesn't strip front matter, and rendered two literal
horizontal rules at the top of the actual repo page. Left `README.md` as a
plain passthrough instead; nothing on the site links to a local copy of it
anyway. Full reasoning in `docs/ARCHITECTURE.md`.

## v1.2.1 -- 2026-09-01

A real public GitHub Pages docs site (README.md as the homepage, CHANGELOG.md
and docs/*.md reachable from the same build), with README.md's own staleness
around mpd/rmpc fixed first since it was about to become that homepage. PATCH
bump: a documentation/repo-completeness gap fixed, not a change to how the
desktop itself behaves.

## 2026-09-01 (a real public docs site, and README.md fixing itself along the way)

Asked directly for a GitHub Pages site with an installation guide and detailed
docs. Confirmed it genuinely didn't exist yet (`gh api repos/.../pages` -> 404),
not assumed.

Checked `README.md` before building on top of it, since it was about to become
the site's homepage -- found it stale (no `mpd`/`rmpc` anywhere in the Desktop
Stack table, Repository Structure tree, or the manual `stow` example, despite
this session's whole termusic-replacement). Fixed all three.

No separate `docs/index.md` written -- Pages/Jekyll uses `README.md` as the
homepage automatically with no `index.md` present, and README.md was already a
complete install guide once the stale parts were fixed; a second site-only copy
would just be one more thing to keep in sync forever. `CHANGELOG.md` and
`docs/*.md` are reachable from the same build since Pages is sourced from the
repo root, not a `/docs` subfolder (`CHANGELOG.md` lives at the root, scoping to
`/docs` alone would have left it unreachable).

Added one file, `_config.yml` (repo root): `theme: jekyll-theme-cayman`, a
GitHub-Pages-supported built-in theme (no Gemfile, no extra build step,
confirmed via pages.github.com/themes) plus an `exclude:` list for every real
dotfile package directory so Jekyll only processes actual documentation.

Deliberately skipped taking a live screenshot for the README's existing
placeholder, even with the tooling right there -- checked what was actually on
screen first and found a real browser window with a personal email address in
its title and a live ngrok tunnel URL, part of the user's real session. A public
Pages screenshot is a published, hard-to-fully-reverse artifact; left the
existing honest placeholder rather than risk it unprompted.

Enabled Pages via the API once the content existed on `main` (source: `main`,
path `/`), then verified the actual build succeeded and the site was reachable
via a direct `curl`, not just a successful API response.

## v1.2.0 -- 2026-09-01

rmpc's theme went from a flat, two-color mapping to a richly-colored, deliberately
waybar-matched palette across three passes (playback header and toggles;
everything still left plain -- browser rows, table headers, preview metadata, tab
bar; then a request for a border-style selection instead of a filled background,
which surfaced and fixed a real bug where a malformed RON modifiers string
silently dropped rmpc's entire config back to built-in defaults). Also fixed a
real, reproducible-on-every-boot bug: `swayidle.service` staying dead after a
fresh reboot because systemd's own auto-start exhausts its restart budget before
the repo's own ordering fix gets a chance to run. MINOR bump: real new capability
(the richer theme) plus real fixes to things that were actually broken, found via
direct source-reading and a genuine post-reboot stability sweep, not assumed
correct from the config alone.

## 2026-09-01 (swayidle: fixed a real "dead on every boot" bug, found during a stability sweep)

Asked directly to check whole-system stability before cutting a release. A real
reboot had happened since the last check, which mattered: found
`swayidle.service` `inactive (dead)` on a completely fresh boot, not leftover
state. The existing idle-management entry already flagged this exact gap ("no
real reboot to verify against") -- the reboot found what the simulation missed.

Root cause: systemd's own auto-start (`WantedBy=default.target`) races
`dbus-update-activation-environment` and fails 4 times in ~7 seconds
(`WAYLAND_DISPLAY` not set yet) -- enough to hit systemd's default
start-limit-burst before `swayidle-startup.sh` (the script `sway/config`
already `exec`s later specifically to fix this ordering) ever runs. A plain
`systemctl --user restart` against a unit already in `start-limit-hit` is a
silent no-op -- no error anywhere.

Fixed with `systemctl --user reset-failed swayidle.service` added to the top of
`swayidle-startup.sh`. Confirmed the theory in isolation first (restart alone:
no effect; reset-failed + restart: active in under a second), then verified the
real fixed script in both its own branches (caffeine-on/off) live.

`sway-audio-idle-inhibit.service` has its own real crash history
(`coredumpctl`, several SIGABRTs on separate days) -- confirmed currently
healthy since this boot, not chased further since it isn't reproducing now.

## 2026-09-01 (rmpc theme, round three: no bg fill on selection, plus a real silent-failure bug found)

Direct follow-up: "the active item should not get the background
colorf but instead have a rounded colord border. and that quee
directories artists row elements should be colored each differentlly
right also same goes for that normal text as well." Pulled rmpc's own
Rust source this time rather than guess what's actually possible.

No per-item border capability exists in rmpc at all (confirmed from
source: `current_item_style` is a plain ratatui `Style`, fg/bg/
modifiers only, applied to a whole `ListItem`/`Row` -- no border
concept for individual rows anywhere, only around whole panes). Closest
honest substitute: dropped `bg` entirely, `current_item_style` is now
`fg: "#cba6f7"` with `Bold | Underlined` instead of a solid fill.

Found a real, serious bug building that: first wrote the modifiers as
`"Bold, Underlined"` (comma-separated) -- valid RON, wrong for how
`Modifiers` actually deserializes (rmpc uses `bitflags` v2, whose serde
support expects its own `Flag | Flag` format). This didn't just fail
that one field -- it silently dropped the **entire config** back to
built-in defaults, no error logged anywhere. Caught by comparing
`rmpc debuginfo` (correctly resolved every path standalone) against the
actual running instance's own log, whose `Resolved config` showed
`cache_dir: None` and every color as a plain ANSI name instead of any
real hex value. Fixed with the format the crate actually expects.

Also: traced `song_table_format`'s real row-rendering path and
confirmed (unlike the browser tabs) it genuinely applies per-column
`style` to actual row content, not just headers -- so Queue/Playlists/
Search table rows are now colored per column throughout, not only in
the header. And found a real, unfixable-via-config limit for the
browser tabs (Directories/Artists/Album Artists/Albums): their song
rows go through a different, style-blind render path
(the Song-typed `Property::as_string` variant discards `style` entirely,
confirmed in the function body) -- only the one-character type marker
per row is a real color lever there; left the inert per-field theme
values in place with a comment explaining why rather than deleting
them.

Verified live, including hitting the actual bug live before finding
its cause: relaunched, confirmed the full-default fallback via the log
comparison, fixed the modifiers syntax, relaunched again, confirmed
real hex values back in the resolved config, screenshotted the Queue
tab with a real song actually queued, and pixel-matched all four
column colors -- exact RGB matches. Ruled out a leftover background
block on the selected row via row-by-row pixel distribution, not a
single broad scan.

## 2026-09-01 (rmpc's theme, round two: colored everything still left plain)

Immediate follow-up: "can't we add some more colors to this tui and
make it more colorfull like our status bar?" The first theming pass
only touched the playback header and toggle cluster -- the file
browser, table column headers, preview metadata, tab bar, scrollbar,
and elapsed/bitrate line were all still plain default text. Went
through every remaining unstyled field, reusing the same waybar-matched
hues plus the two waybar colors nothing had used yet (Blue `#89b4fa` =
waybar's `#clock.time`, Rosewater `#f5e0dc` = waybar's wallpaper
button):

- Browser row markers (`symbols.song_style`/`dir_style`/
  `playlist_style`, all `None` before): Sky, Blue, Rosewater.
- Browser row text (Artist/Title, previously unstyled): Lavender and
  Sky, deliberately matching the playback header's own colors for the
  same fields.
- Table column headers (Artist/Title/Album/Duration, previously
  unstyled): Lavender/Sky/Rosewater/Peach -- header row only, actual
  song rows stayed mostly neutral so a long table stays scannable.
- `tab_bar.inactive_style` (previously empty): waybar's own off-gray
  `#6c7086` -- doubles as a real legibility fix, not just decoration.
- `preview_metadata_group_style` (was identical Yellow to its own
  label): Blue, now genuinely distinct from the label.
- `elapsed_and_bitrate` (had zero color): Green `#a6e3a1`.
- `scrollbar.ends_style` (previously empty): same off-gray as inactive
  tabs.

Verified the same way as before: relaunched, zero theme-parse errors,
screenshotted and pixel-matched. `dir_style`'s Blue only shows on the
Directories tab (Queue is the default), so switched tabs with a real
simulated keypress before screenshotting rather than treating a
zero-match result as evidence of a bug. Every color checked came back
an exact RGB match.

## 2026-09-01 (rmpc's theme: recolored by role, matched to waybar's own palette)

Direct feedback: "can we improve the theming of the music player here i
mean use some colors like our status bar and make it more asthetic."
The original theme was a literal, uniform string substitution (every
"blue" -> the same Mauve, every "yellow" -> the same Yellow, everywhere)
-- technically colored but nearly monochrome, Mauve+Yellow doing almost
every job. Read `waybar/style.css` first to see how it actually assigns
color (a different hue per module: Sapphire/dark-mode, Sky/wifi, Peach/
capslock, Teal/numlock, Maroon/pulseaudio, Lavender/notifications, a
literal `#6c7086` for every off-state), then recolored rmpc's theme by
UI role to match, not at random:

- Song title (previously no color at all): Sky `#89dceb`.
- Artist (was identical Yellow to the state badge above it): Lavender
  `#b4befe`.
- Volume number/%: Maroon `#eba0ac` -- literally waybar's own
  `#pulseaudio` color, the most direct possible match.
- Repeat/Random/Consume/Single toggles (all four previously shared one
  color pair): Teal/Peach/Sapphire/Lavender when active, waybar's own
  literal off-gray `#6c7086` when not, instead of a dimmed Mauve.
- `level_styles.info`: Mauve -> Sapphire, freeing Mauve to stay the
  one "selected/active" accent everywhere else in the theme (unchanged:
  `current_item_style`, `borders_style`, `tab_bar.active_style`).
- Every `#1e1e2e` (Catppuccin Base) -> `#11111b` -- grepped the repo
  first and confirmed `#11111B` is already the one shared dark surface
  across waybar, mako, wofi, nwg-bar, and sway's own border scheme;
  rmpc was the only thing still on the lighter Base tone.

Verified live: relaunched through the real keybinding, confirmed zero
parse errors in rmpc's own log, screenshotted the running window, and
pixel-matched specific coordinates against the theme's target hex
values -- title/artist/volume came back exact RGB matches, zero color
distance. Off-state toggles came back the right color family and
position, qualitatively confirmed (too fine-grained a target for exact
pixel matching on anti-aliased glyph edges).

## v1.1.0 -- 2026-08-31

termusic replaced entirely with mpd + rmpc (a real MPD daemon plus a
proper TUI client, zero third-party API dependency left in the music
stack), music-search.py gained real thumbnails in its results list,
rmpc's floating window got genuine compositor-level glass (SwayFX
blur, not opacity tricks) at a larger 60%/60% size, and every popup in
this desktop -- rmpc's window included now -- closes on Escape. MINOR
bump: new capability (mpd/rmpc replacing a whole subsystem), not just
a fix to something that was broken.

## 2026-08-31 (every popup closes on Escape -- rmpc's window was the one real gap)

Direct feedback: "all popup modals should also hide when esc key is
pressed as well." Audited every popup rather than guessing which ones
needed it: every wofi-based popup (`toggle-popup.sh`'s clients) already
closed on Escape natively, and nwg-bar (power menu) did too, confirmed
live with a real synthetic Escape keypress (`ydotool key 1:1 1:0`) after
opening each through its real keybinding.

rmpc's floating window was the actual gap -- tested the same way and it
stayed open. rmpc's own `config.ron` already binds its Esc key entry to
`Close`, but
that's an internal rmpc action (closes a modal *inside* rmpc), not
anything that knows about sway's scratchpad, so Escape was a no-op with
no internal modal open.

Fixed with a new script (`scripts/.local/bin/rmpc-hide.sh`, just the
same `swaymsg scratchpad show` rmpc-toggle.sh's second press already
runs) wired in via a per-window kitty keybinding override on rmpc's own
launch line -- rebinds Escape for that one instance only, before it
reaches rmpc's pty, `kitty.conf`'s global map table untouched. Verified
end-to-end through the real keybinding: window opened, focused,
Escape sent, `swaymsg -t get_tree` confirmed `visible: false`, rmpc
process and mpd.service both still alive throughout, then toggled back
open once more to confirm the existing show-path still works.

Known tradeoff, not a real loss: rmpc's own internal `Close` action is
also bound to its C-c key entry already, so it still has a working key, just
Ctrl+C instead of Escape for this window from now on.

## 2026-08-31 (rmpc: real compositor blur, not opacity tricks, plus a bigger window)

Direct, immediate follow-up to the entry right below: "lets make its
background glass like blury background and increase it size follow
the 60 percent width and increase the height accordinglly." The
opacity-only fix below turned out to be the wrong lever -- lowering it
just showed the wallpaper completely sharp through the window, which
reads as "see-through", not glass.

Real fix: this machine runs SwayFX (confirmed via `sway --version`),
which has genuine compositor-level blur already proven for wofi
(`layer_effects`). Added `blur enable` to rmpc's own `for_window` rule
in `sway/config` -- a plain `for_window`-settable property for ordinary
toplevel windows (no `layer_effects` block needed, that's layer-shell-
only), deliberately without `blur_xray` per SwayFX's own README
guidance for regular floating windows. The earlier per-window kitty
`background_opacity=0.3` override was removed once blur made it
unnecessary -- back to kitty's global 0.85, which turns out to match
wofi's own real working ratio (0.85 alpha + real blur) exactly.

Verified with a cleaner pixel test than the previous entry's: found the
highest-texture patch in a wallpaper-only screenshot, compared it
against the same screen region through the live window -- local
gradient energy dropped ~92% (9.85 -> 0.83), and the rendered pixels
were a smooth blended tone, not the sharp original or a flat color.
Text legibility reconfirmed intact.

Also resized: window was 1152x540 (60%/50% of the 1920x1080 output),
now 1152x648 (60%/60%) -- kept width as-is, grew height to match the
same percentage instead of a smaller, mismatched one. Confirmed live
via `swaymsg -t get_tree`.

## 2026-08-31 (rmpc's floating window: actually glass, not just technically transparent)

Direct feedback right after the mpd/rmpc migration below: "lets make
its background glass like." `background_color: None` was already set
in the theme (carried over proactively from termusic's own fix), and
kitty's global `background_opacity 0.85` was blending against it -- but
on a window this large (1152x540, over half the screen), that blend
wasn't perceptible enough to read as glass.

Fixed with a per-window kitty override on rmpc's own launch line only
(`-o background_opacity=0.3`, `scripts/.local/bin/rmpc-toggle.sh`) --
`kitty/kitty.conf`'s global 0.85 stays untouched for every other
terminal use.

Getting to a trustworthy number took a few wrong turns, worth recording
since they're easy to repeat: whole-window pixel averaging (comparing
against a same-position wallpaper-only screenshot) gave inconsistent,
sometimes backwards-looking deltas between opacity values, because the
average is skewed by however much text/UI happens to be on screen at
capture time, not just the background blend. Switched to sampling one
fixed, confirmed-empty patch of the window instead, at the real
toggle-triggered window position -- that gave a clean, reproducible
result: at 0.3, rgb(16.9, 15.0, 10.6) vs. a wallpaper-only rgb(24.0,
21.3, 15.1) for the identical region, a real ~7-9 point shift per
channel, in the same "dark glass" direction as every other translucent
surface in this desktop (waybar, mako, wofi, nwg-bar all read as
Deep-Midnight-tinted, not lightened). Confirmed text legibility held up
at 0.3 via a direct ASCII luminance dump of real rendered text, not
just the averages.

## 2026-08-31 (termusic removed entirely: mpd + rmpc instead)

Direct feedback: "termusic isn't of any use then, lets use a better tui
or cli local music player then and remove this damn termusic." Rather
than keep patching around its one real problem forever, swapped the
player out too.

termusic fully removed: package uninstalled, ~/.config/termusic/
deleted, termusic/ package and termusic-toggle.sh gone from this repo.
Every historical entry that talks about termusic is left as written --
real history, not rewritten.

mpd (official extra repo, mpd.service shipped by the package itself) is
the new backend -- zero third-party API dependency at all, just plays
real files. Confirmed its filesystem watcher genuinely works (dropped a
file into ~/Music with no clients connected, watched it get indexed
within seconds), a real improvement over termusic which had none.

rmpc (official extra repo, 3.3k stars, actively maintained) is the new
UI, an MPD client with no playback logic of its own. Validating find:
rmpc ships its own yt-dlp-based YouTube downloader too (confirmed
reading its source, real yt-dlp not Invidious) -- independent proof
music-search.py's own approach was the right one. Its own picker has no
thumbnails though, so music-search.py stays the actual search tool.

Theme/sizing/transparency/toggle rebuilt applying termusic's own
lessons instead of rediscovering them: rmpc theme dumped its real
default (one big RON structure with named colors threaded through the
whole layout, not a flat palette) and every color got substituted for
Catppuccin Mocha ("blue" specifically mapped to Mauve, matching its
role as this desktop's own "active" accent). background_color left
None from the start this time -- verified live, zero pixels of solid
background, Mauve dominant, glass worked on the first real launch, no
rediscovering the bug termusic needed a dedicated fix for.

Real scare resolved by finding the actual cause: rmpc debuginfo
reported the album-art protocol as the crude "Block" fallback instead
of "Kitty" -- traced to this session's own shell not being a real tty
(env vars inherited, not backed by a real terminal), not an actual
setup problem. Checked rmpc's own log from the real launch path instead
and found resolved_backend="Kitty", kitty_graphics="true" -- genuinely
active for the path that matters.

## 2026-08-31 (music-search.py: real thumbnails in the results list)

Reported directly: "only text doesn't make that much sense, show
thumbnail and title in each row." wofi's own img: dmenu markup handles
it (same mechanism notification-history.py already uses) -- just needed
a thumbnail source. YouTube's plain https://i.ytimg.com/vi/id/mqdefault.jpg
URL (confirmed directly with curl, not assumed) is simpler and more
reliable than the signed URLs in yt-dlp's own thumbnails JSON. Fetched
for all ~10 results concurrently (confirmed: ~0.4s together vs several
seconds serial), cleaned up after the picker closes either way.

Verified live: checked the temp directory's actual contents while the
real results popup was open (through the real keybinding, real typed
input) -- ten real, valid JPEG files, confirmed with `file`.

## 2026-08-31 (music-search.py: replacing termusic's broken search with our own tool)

Asked directly to build a replacement rather than live with the
URL-paste workaround. Checked ytfzf first (the obvious existing
alternative) and ruled it out -- read its source, its default search
path is a direct alias for Invidious search too, same dead network
already confirmed for termusic.

Built music-search.py on yt-dlp's own direct search instead (confirmed
independent of Invidious, ~2-3s for 10 results). $mod+Shift+y: wofi
prompt for a query, wofi list of results (title/uploader/duration --
duration shown after accidentally downloading a 3+ hour video once
during testing), downloads the pick as mp3 with embedded art/metadata
into ~/Music.

Two real bugs found and fixed while building this: (1) 2 of 3 real
test downloads hit YouTube's bot-check wall with yt-dlp's default
extraction -- fixed with --extractor-args
"youtube:player_client=android", confirmed directly that the same URLs
downloaded cleanly with it every time. (2) the completion
notification's icon (the track's own thumbnail) failed to load and the
thumbnail file was left undeleted -- yt-dlp sanitizes filenames
differently than the raw search-result title (a literal "|" becomes a
fullwidth "｜"), so reconstructing the filename from title silently
matched nothing. Fixed by finding the newest image file by mtime
instead of predicting yt-dlp's naming.

Verified fully live through the real keybinding with real typed input
(ydotool, not the script run directly): read actual search results
back via wofi's AT-SPI tree, downloaded a real track, confirmed with
ffprobe it's valid audio with embedded cover art, and confirmed via
termusic's own startup log ("1 created or updated") that it's genuinely
indexed by termusic's real library scanner. termusic's own `s` key is
left as-is; $mod+Shift+y is just the reliable path now.

## 2026-08-31 (every popup toggles now; termusic gets real glass, correct size, and a search diagnosis)

Three asks together: every keybinding-launched popup should toggle
(press the same key again to close it) and close on Escape; termusic
needs an actual transparent background and resizing to 60%/50% of the
output; and why doesn't termusic's YouTube search work at all.

Escape already worked for wofi and nwg-bar popups (both handle it
natively, confirmed rather than assumed -- nwg-bar's own Go source
calls gtk.MainQuit() on Escape release). Toggle needed real work: new
scripts/.local/bin/toggle-popup.sh, a marker-file-based wrapper every
wofi-based popup keybinding and the power menu now route through --
same key while its own popup is open closes it, a different key closes
whatever else is open first then opens the one requested. Verified live
for both a raw wofi process and nwg-bar (a different binary entirely)
to confirm it generalizes.

termusic doesn't use that script -- killing/relaunching it would stop
playback, since it's a real client/server app. New
scripts/.local/bin/termusic-toggle.sh uses sway's scratchpad instead:
verified directly (not assumed from sway's own ambiguous docs) that
`scratchpad show` on an already-shown scratchpad window genuinely hides
it again, and that the underlying process is untouched the whole time
(same PIDs, no disconnect logged, across a full hide/show cycle).

Real transparency bug found and fixed: kitty's background_opacity only
blends cells using the terminal's own default background -- termusic's
theme was painting an explicit opaque hex into every cell, defeating it
regardless of kitty's own setting (confirmed from termusic's own
source, not assumed). Fixed with termusic's own "native" theme value
(resolves to ratatui's Color::Reset, meaning "don't paint here"),
cascading through every panel in one edit since they all reference the
same field symbolically. Verified live: 0% of the window's pixels are
the old literal hex now; cross-checked the resulting dark blend against
a same-region wallpaper-only screenshot to confirm it's a real blend
against a coincidentally-dark wallpaper patch, not a failure to blend.

Resized to 1152x540 (60%/50% of the actual 1920x1080 output, computed
directly). A real bug hit building the toggle script: an early version
backgrounded kitty without detaching stdio, which could hang whatever
launched it -- fixed with setsid + redirected output.

YouTube search diagnosed to a real, external, unfixable-from-here root
cause: confirmed yt-dlp itself works fine (direct search succeeds), so
termusic's search specifically uses the public Invidious instance
network, not yt-dlp, for the search step. Tested every one of
termusic's five hardcoded fallback instances' actual search endpoints
directly: three return explicit errors (403 disabled, 401
unauthorized, anti-bot challenge page), two are unreachable. Checked
the live instance directory too -- zero of the 11 currently listed
instances have their public API enabled at all. Not a local network
issue, not fixable by upgrading termusic (checked upstream's current
changelog, still Invidious-based). Working mitigation: paste a direct
YouTube URL into the same search popup instead of a text query -- skips
the broken search step, goes straight to the already-confirmed-working
yt-dlp download path.

## 2026-08-31 (termusic: CLI music player, no local library or Premium needed)

Asked for a "beautiful CLI" music player with no local library and no
Spotify/YouTube Premium to lean on. Picked termusic -- its own README
says directly it downloads from YouTube/NetEase/Migu/KuGou for free, no
paid membership needed. Ruled out spotify-player/ncspot (both need
Spotify Premium to actually play anything, a restriction Spotify itself
enforces) and rmpc/cmus (both local-library-only, no cloud fetch at
all) directly against the constraint rather than assuming.

Confirmed the actual mechanic from its own source: `s` opens a
"Download url or search" popup, picks a YouTube result, downloads via
yt-dlp into ~/Music, plays -- works from a genuinely empty library.
Directly in Arch's official extra repo, no AUR/source build. Added
yt-dlp alongside it in packages/pacman.txt.

Real version mismatch found by checking: upstream master ships an
official Catppuccin-Mocha theme, but the installed package (0.13.2-1)
predates it -- confirmed directly by launching termusic and checking its
own bundled themes/ directory, genuinely missing. Copied the file in by
hand. Theme baked into tui.toml's [theme] section rather than left as a
manual step -- avoided guessing the TOML shape blind by launching once
with no config, reading termusic's own generated defaults, then writing
into that confirmed real shape.

Only tui.toml/server.toml/the one theme file stowed, not the whole
~/.config/termusic/ -- data.db/library2.db/playlist.log are runtime
state, same config-vs-state line this repo already draws for
~/.local/state/. Works because the directory already existed as real
(termusic creates it itself) before stowing -- confirmed with
`stow -n -v` that individual files get symlinked in, not the whole
directory.

$mod+Shift+m opens it in its own floating kitty window (sized/centered
via a for_window rule). Verified live: triggered the real keybinding via
simulated keypress, confirmed the floating window's position/size via
swaymsg, screenshotted it running -- 88.6% of its pixels are the exact
Catppuccin Mocha background hex, confirming the theme is genuinely
active in the real instance.

## v1.0.1 -- 2026-08-30

Patch release. The entire power-menu arc since v1.0.0 -- keybinding,
real per-action colors on the button chrome, glass+border on every
button, Tab-navigation fix, lean icon set, and this polish pass --
merged from `develop` in one fast-forward, tagged as a patch rather
than a minor bump per direct instruction. Everything below back to
v1.0.0 shipped in this version.

## 2026-08-30 (power menu polish: "Power off" label, thinner icons, real icon/label gap)

Three small asks together: rename Shutdown to Power off, thinner
icons, real space between icon and label -- nwg-bar stacks them with
zero gap of its own (SetImagePosition POS_TOP, nothing else).

Label changed in bar.json directly. Stroke-width dropped 2 -> 1.5
across all five icons, same Lucide path data. Icon size set explicitly
to 40px (-i 40) on both places nwg-bar launches from (waybar's
custom/power on-click, sway's $mod+Shift+p) -- nwg-bar's own 48px
default read as slightly oversized against the button padding. Actual
gap: image { margin-bottom: 10px; } in style.css -- image is the
element directly above the label in nwg-bar's own stack, no more
specific CSS node exists to target.

Verified live: read the padlock icon's rendered pixels back as ASCII
art before and after -- gap to the label went from ~9px to ~19px, a
real measured change. Confirmed via AT-SPI that the fifth button now
reports "Power off". Border colors from every earlier pass unaffected.

## 2026-08-30 (power menu, third icon pass: lean stroke icons, one family)

Direct feedback right after the Adwaita swap below: "older once were
better than this. i want lean icons just like the older once but just
different." The Adwaita set fixed meaning but lost the lean, thin-
outline look the originals had -- the actual ask was both at once.

Rebuilt all five from Lucide (a modern line-icon set, 24x24 grid,
consistent 2px stroke, no fill) -- found already vendored locally as an
npm dependency in an unrelated project on this machine, no network
fetch needed. lock/log-out/moon/rotate-cw/power path data copied
straight from Lucide's own per-icon source files into plain standalone
SVGs, same stroke weight across all five this time -- one coherent
family instead of a patchwork. Swapped stroke="currentColor" for a
hardcoded #CDD6F4 (same reasoning as every other icon fix this
session: raw file load, not icon-theme resolution, no reliable
currentColor context). Shutdown's `power` icon is functionally the same
ring+line symbol as before, just redrawn in the same lean style as the
other four.

Verified live: launched nwg-bar directly, read all five icons back as
ASCII art -- a genuinely hollow padlock, door+arrow logout, a thin
crescent moon, circular refresh arrow, power symbol, all at the same
visual weight. Confirmed the five border colors from the earlier pass
unaffected.

## 2026-08-30 (power menu: better icon shapes, four of five swapped for Adwaita's)

Reported directly: Suspend looked like "a circle with a vertical rod in
the middle", not meaningful -- asked for better icons generally.

Checked Papirus's own system-suspend-symbolic first and rejected it --
same ring-plus-dash concept already in use, wouldn't have fixed
anything. Used a crescent moon instead (Papirus's weather-clear-night
shape, recolored) -- the universal sleep symbol. Swapped Lock/Logout/
Reboot to Adwaita's own symbolic set too rather than leave a mismatched
patchwork next to one new icon. Shutdown untouched -- already correct
from the previous pass.

Every Adwaita source icon ships a hardcoded fill meant for light GNOME
toolbars (#2e3436) -- same issue already found and fixed for mako's
notification icons. Recolored to #CDD6F4 (this bar's own text color).
Full mapping in icons/README.md.

Verified live: launched nwg-bar directly, read all five icons' actual
rendered pixels back as ASCII art -- a real padlock, a clear exit
arrow, an unambiguous crescent moon, a circular refresh arrow, each
individually recognizable. Confirmed the five border colors from the
previous pass were unaffected.

## 2026-08-30 (power menu: keybinding, verified Tab nav without ever pressing Enter)

Added $mod+Shift+p to open the power menu (same gap every other
waybar-click-only picker already had fixed), and verified Tab/Shift+Tab
move focus between its buttons as expected.

Every action here (Lock/Logout/Suspend/Reboot/Shutdown) is disruptive or
hard to reverse -- couldn't safely press Enter just to check where focus
landed. Used nwg-bar's own AT-SPI accessibility tree instead (it's
already registered on the bus) to read back which button reports itself
focused after each simulated Tab/Shift+Tab -- read-only, same mechanism
screen readers use, zero risk of triggering anything. Confirmed the full
cycle both directions with wraparound.

Found a real gap doing this: focus was genuinely moving the whole time,
but nothing was styled to show it -- a before/after screenshot diff read
zero changed pixels. Fixed by giving :focus the same treatment as :hover
on every per-action border rule. Re-verified: the same diff now reads
35936 changed pixels for one Tab press, and AT-SPI confirms the actually-
focused button matches the one that visibly glows.

## 2026-08-30 (power menu, corrected: color on the pill not the icon, glass+border per button, real CSS bug fixed)

Direct feedback right after the entry below: wrong layer for color
("by colors i don't mean those icons"), and the card was missing
glass/border on every button, not just the outer frame.

Reverted icons to plain stock appearance -- color now lives on the
button itself instead, mirroring waybar's own per-module coloring: a
low-opacity border tint per action, brighter plus a glow on hover, keyed
off :nth-child since nwg-bar gives buttons no name/class to target
directly. Gave every button its own resting glass pill too (waybar's
exact rgba/radius/border formula), not just on hover -- the outer card
already had glass+border, individual buttons didn't, which is almost
certainly what read as missing entirely.

Real bug hit along the way: the first attempt at this silently failed
to apply at all -- nwg-bar's own log said "style.css file erroneous...
using GTK styling", falling back to bare default chrome. Diagnosed with
GTK's own CssProvider parsing-error signal: a comment mentioning
"icons/*.svg" broke CSS's no-nested-comments rule (`/*` inside prose
closes early). Fixed the wording, re-verified zero parse errors before
trusting it. Verified live end to end: log confirms style actually
loads now, zero pixels match the old icon-fill colors, all five button
border colors present and distinct in the card region.

## 2026-08-30 (power menu icons: invisible colors fixed, meaningful per-action palette)

Asked for the nwg-bar power menu to show meaningful, colored icons,
Shutdown specifically looking like a real power button. First change on
`develop` after tagging v1.0.0.

Root cause: nwg-bar's stock icons (`/usr/share/nwg-bar/images/*.svg`)
each have a colored circle whose fill is silently disabled by an inline
`style="fill:none"` on the same element -- every action rendered as a
flat white ring with nothing behind it, not a size/shape issue. Suspend
and Shutdown also shared the exact same stock red, no distinction even
if the fill had worked.

Made local copies (`nwg-bar/.config/nwg-bar/icons/`, `bar.json`
repointed) since nwg-bar gives buttons no CSS class to color per-action
at the stylesheet layer -- removed the fill:none override, recolored
each to this desktop's own Catppuccin Mocha palette (Sapphire/lock,
Peach/logout, Teal/suspend, Yellow/reboot, Red/shutdown -- full mapping
in that directory's README). Glyph shapes untouched -- Shutdown was
already the correct ISO power/standby symbol, just needed its color
back. Verified by launching nwg-bar directly and reading the rendered
pixels back as ASCII art, not color-tolerance sampling.

## v1.0.0 -- 2026-08-30

First tagged release. Marks the point this repo switched from "dated
entries with no version boundaries" to a real `main`/`develop` branch model
with tagged releases (`docs/VERSIONING.md`) -- not a specific technical
milestone on its own, but the desktop was given a full, direct stability
pass before drawing this line, not just assumed stable:

- **Processes**: exactly one each of sway, waybar, mako, swaybg running,
  confirmed via `pgrep -x`/`pgrep -a` (not just "a" process existing --
  checked for duplicates/stray instances from the session's own testing).
- **systemd**: `systemctl --user list-units --failed` clean (one stale,
  harmless `mako.service` failure reset -- a disabled, package-provided
  unit unrelated to how this repo actually runs mako, killed as a side
  effect of live testing earlier the same session, not a real fault).
  `wallpaper.timer` active and correctly scheduled; `swayidle.service`
  correctly inactive because caffeine mode is currently on (state file
  present) -- confirmed intentional, not a fault, by reading
  `swayidle-startup.sh`'s own logic rather than assuming.
- **Config validity**: `makoctl reload`, `swaymsg reload`, and a manual
  brace/bracket balance check on `waybar/config` all clean.
- **Scripts**: every `.sh`/`.py` under `scripts/.local/bin/` and
  `sway/.config/sway/scripts/` executable, `bash -n`/`python3 -m py_compile`
  clean across all of them.
- **Disk/state hygiene**: wallpaper archive correctly capped at 60 files,
  20M total, no stale locks, notification-mode state file consistent with
  live `makoctl mode`.
- **git**: working tree clean, `main` up to date with `origin/main`.

## 2026-08-30 (volume icon, third pass: dropped the glow)

Asked directly, once the icon was genuinely rendering again: why the
glow, make it normal. Fair -- the text-shadow was added to make an
*invisible* icon more noticeable, back when the problem looked like
"too small" rather than "not rendering at all". Once the real cause
(waybar's broken format-icons threshold form, previous entry) was fixed
properly, the glow had nothing left to justify. Removed it --
#pulseaudio is back to a plain resting color like every other module.
Verified with the same ASCII-dump method as the previous entry: icon
still renders fine at 80%, just without the shadow now.

## 2026-08-30 (volume icon, second correction: a real waybar bug, verification method overhauled)

Reported again after the text-shadow fix: "only when its muted does it
show the icon" -- the icon was invisible at every regular volume level
the whole time, not just small. My previous two verification passes
(color-tolerance pixel matching, both times) missed this entirely --
worth stating plainly rather than letting a third wrong "verified"
claim stand.

Stopped trusting color-heuristic sampling and switched to dumping the
actual screenshot as luminance-thresholded ASCII art, reading the glyph
shapes directly like a person would look at the bar. Immediately showed
the real picture: nothing between the icon's space and the percent
digits at any regular volume level; a genuinely new glyph appearing only
when actually muted.

Root cause, isolated by testing one variable at a time: waybar's
format-icons threshold-object form ({"icon":...,"max":N}, added to give
0% its own icon) -- real and documented, straight from waybar's source
-- silently renders no icon at all for pulseaudio's regular format
string in this waybar build (v0.15.0), confirmed by reverting to a
plain array (icon reappeared) and reapplying the threshold form alone
(gone again). format-muted kept "working" the whole time because it
never used format-icons at all -- a fully hardcoded string, unaffected
by the bug, which is exactly what made it look like proof the feature
worked.

Fixed by not depending on the broken path: volume_osd.sh now sets the
real PulseAudio mute flag whenever a scroll/keypress lands exactly on
0%, clearing it the moment volume moves back up -- so format-muted (the
one path already proven correct) picks it up naturally. 0% and muted
really are the same silence to the ear, so this is also just a more
honest model of the actual state, not a workaround. Known gap: only
covers 0% reached through volume_osd.sh itself, not pavucontrol or other
external tools touching the sink directly.

## 2026-08-30 (volume icon correction: span-size broke it, text-shadow fixed it)

Reported right after the entry below: icon not visible at all, muted
icon + "Muted" text not on the same line. Both real, both caused by
that entry's inline-span approach.

Isolated the cause step by step rather than guessing: reverted the
per-icon Pango span first (confirmed the separate format-icons
threshold-object change was fine on its own, icon rendered small but
correctly). Tried a uniform font-size bump on the whole module instead
-- hit a second, different bug: at 15px the three volume-level glyphs
stopped rendering entirely (0 pixels), while the mute glyph and percent
digits kept working fine at the same size. Reproducible, isolated,
genuinely strange -- a real font/Pango rendering quirk, not chased
further blind. font-weight: 700 (already proven safe elsewhere in this
file) changed nothing for these glyphs -- no breakage, but no visible
difference either.

Landed on text-shadow -- same paint-only technique already proven safe
in this file (#custom-capslock.locked's glow), doesn't touch layout or
font rendering at all. Verified properly this time: matched for a
Maroon-ish hue rather than "anything non-background" (which the first
pass at this wrongly picked up backlight's own Yellow icon bleeding into
the same crop). Consistent ~12x9px glow at every volume level (vs
~4-5px bare), icon and text on the same y-range, and the glyphs actually
render.

## 2026-08-30 (volume icon: muted look at 0%, consistent visible size)

Two things reported as one: 0% volume didn't look muted (design opinion
given directly: it should -- 0% and actually-muted are both silent, no
reason to look different), and the icon in general is hard to notice at
low volumes.

Measured the actual problem before fixing it: cropped a real screenshot
to just the icon and found ~4x5px of ink at every volume level,
regardless of which of the three glyphs was showing -- the whole icon
was just small, not a per-level issue.

- 0% fix: waybar's format-icons supports {"icon","max"} threshold
  objects, not just an evenly-bucketed array (confirmed from waybar's
  own source, src/ALabel.cpp) -- gives 0% its own exact bucket instead
  of sharing one with everything up to 33%. Reuses format-muted's
  existing crossed-out glyph rather than adding a new one.
- size fix: wrapped {icon} in its own Pango span
  (<span size='16384'>{icon}</span>), sizing only the icon, not the
  percent text -- a *static* size baked into the format template, not a
  CSS font-size or a state-conditional one. This repo already hit the
  state-conditional failure mode once (bumping font-size on
  #custom-capslock.locked visibly popped the whole bar taller at
  runtime) -- avoided here since the span size never changes, so
  there's nothing to jump between.

Verified live: restarted waybar for real (SIGUSR2 confirmed a no-op in
the entry above), measured the icon bbox again -- now a consistent
20x9px at every volume level, versus ~4x5px before. Confirmed 0%
renders the reused mute glyph, true-mute still works, no bar-height
pop from the change.

## 2026-08-30 (workspace indicator follow-up: brighter numbers, real waybar-reload gap)

Reported right after the occupancy feature below: the occupied-but-
unfocused number was "slightly hard to notice". Clarified intent: number
color should say "window here, or this is where I am" without
distinguishing the two -- the underline alone confirms "this one is
current". Bumped occupied's color from translucent (0.7 alpha) to
solid, identical to `.focused` -- the two states now differ only by
font-weight (secondary cue) and the underline.

Found a real gap while re-verifying: `pkill -SIGUSR2 waybar`, used to
"reload" waybar for the first pass on this feature, actually does
nothing by default (checked waybar's own source -- no `on-sigusr2-action`
configured here, and no CSS file-watching either), so that earlier
verification may have been screenshotting a stale render that happened
to look right. Fixed by actually restarting waybar outright
(`sway/config`'s `exec waybar` isn't a supervised exec, so a plain kill
needed a manual relaunch) rather than trusting an unconfirmed signal.
Re-verified after the real restart at full bar height (41px): both
numbers solid Red equally, underline present only under the focused
workspace's full width, nothing under the merely-occupied one.

## 2026-08-30 (workspace indicator: occupancy shown separately from focus)

Asked for workspace numbers to show which workspaces hold a window, not
just the focused one -- focused keeps number color + underline, any
other occupied workspace gets number color only, no underline.

waybar's sway/workspaces module already computes this itself: `.empty`
is its own class (confirmed from waybar's own source), toggled live
whenever a workspace's nodes+floating_nodes are both empty -- no
polling or extra script needed. New rule:
`#workspaces button:not(.empty):not(.focused)`, colored the same Red as
`.focused` but translucent rather than solid -- one hue at two
strengths reads as "same kind of signal, different degree" rather than
a fourth unrelated color, and keeps the underline as the sole "current"
signal. Placed before the existing `:hover` rule so hovering an
occupied-but-unfocused workspace still shows hover's Lavender on the
specificity tie.

Verified live: two real workspaces existed, one focused-with-a-window,
one unfocused-with-a-window -- screenshotted the bar and found 42 pixels
of solid Red (focused) and 25 of the translucent-Red blend (occupied,
unfocused), confirming both states render distinctly.

## 2026-08-30 (notification toast icons round two: invisible symbolic icons)

Reported right after the icon-path fix below: the notification-history
copy action "does not show the clipboard icon only text". The icon-path
fix was real and needed, but only fixed *resolution* -- this is a
second, separate bug about *visibility*.

Root cause, found by reading the actual SVG: every `-symbolic` icon in
Papirus (plus several plain `actions`-category ones like `edit-copy`,
`audio-volume-high`, `media-record`) uses `fill:currentColor` with a
`#444444` dark-gray default, meant for light UI chrome -- on this
desktop's near-black notification background that's barely
distinguishable from the background itself. Confirmed directly: diffed
two real screenshots pixel-by-pixel in the icon's own region (one with
`edit-copy-symbolic`, one with a deliberately nonexistent icon as
control) -- 7114 pixels genuinely differed, so something *was* drawing,
just nothing anyone would notice.

Fix: swapped every affected icon across every script in this repo for
Papirus's `status`/`apps`-category equivalent instead -- those use real
hardcoded fill colors (`grep -c currentColor` == 0, checked per icon
before using it), same style Docker's icon already used successfully.
Two (`process-stop`, `media-record`) have no real-fill version anywhere
in Papirus -- swapped for the closest real concept instead
(`dialog-warning` for "cancelled", `audio-input-microphone` for
"recording"). Also switched every one of these to an absolute file path
rather than a bare name -- several names resolve to more than one file
across Papirus categories (one currentColor, one real-fill) and mako
picks by size match, not category, so a bare name can't guarantee which
one wins.

Verified live: fired the exact copy-notification call, found
617/413 pixels of the clipboard icon's own real fill colors
(`#e4e4e4`/`#d3d3d3`) in the icon region, 4194 pixels different from a
no-icon control in the same spot. Separately confirmed a critical-icon
swap (`dialog-error`) with 1082 pixels of its real red fill
(`#f44336`).

## 2026-08-30 (notification toast icons: real mako icon-path bug fixed)

Asked for every toast's title to show the associated tool's icon
(clipboard for copy events, Docker's icon for Docker, etc.) -- every
notify-send call in this repo already passes a correct icon name, so
dug into why none of them ever actually rendered.

Root cause: mako only searches `/usr/share/icons/hicolor` and
`/usr/share/pixmaps` by default and does no GTK-style theme inheritance
-- confirmed directly with `find` that not one icon name used anywhere
in this repo (`docker-desktop`, `edit-copy-symbolic`,
`dialog-error-symbolic`, etc.) exists under `hicolor`; they all live
under the actual active theme, Papirus-Dark, which is itself nearly
empty and inherits from Papirus/breeze-dark in a way mako doesn't
follow. Every notification's icon was silently failing to resolve, full
stop, independent of how correct the icon name was.

Fix: `icon-path=/usr/share/icons/Papirus-Dark:/usr/share/icons/Papirus:
/usr/share/icons/Adwaita` in `mako/config` -- one line, covers every
icon in the repo since all of them already resolve under Papirus
(confirmed with `find` before committing to it). Verified live:
`docker-desktop` icon fired after `makoctl reload`, screenshotted,
716 pixels of Docker's exact brand blue found in the notification region
-- 0 in a negative-control test with a deliberately nonexistent icon
name, confirming the render is real and the test methodology holds.

## 2026-08-30 (notification bell: distinct icons back, alongside color)

Second follow-up in the same session: after dropping to one shared
bell glyph with color-only mode signal, asked to bring back distinct
icons per mode too, on top of the color (not instead of it).

Three bell-family glyphs, not the original mismatched set: `fa-bell`
(normal), `fa-bell-slash` (silent), `md-bell-sleep` (dnd -- a bell with
"zzz", replacing the original `md-minus-circle`, which wasn't a bell at
all and read as an unrelated icon rather than "the bell, in a different
state"). All three confirmed present in the installed Nerd Font via
`fc-list` before use. Hit the session's recurring PUA-glyph-transport-
corruption bug again writing these -- caught and fixed the usual way
(patch via Python `chr()`, verify by reading back `hex(ord(ch))`).

## 2026-08-30 (notification bell: one glyph, color-only mode signal)

Follow-up to the three-mode notification feature above. Asked for
white-only bell icons, then reconsidered mid-request and asked for
color instead, kept clear of the clock's own colors right next to it.

Dropped the three different glyphs (`fa-bell`/`fa-bell-slash`/
`md-minus-circle`) for a single `fa-bell` shared by all three modes --
color is now the only thing distinguishing normal/silent/dnd, kept from
the same three colors already in place (Lavender/dim gray/Red).
Confirmed with an exact-pixel-color screenshot count per mode that each
mode's own color actually dominates the bar while it's active, and that
none of the three share a single exact pixel match with `#clock`'s Blue
(time) or Maroon (date) in any mode -- not just eyeballed as "looks
different enough".

## 2026-08-30 (three notification modes: normal/silent/dnd)

Asked for three notification modes -- normal (popup + sound), silent
(popup, no sound), dnd (neither, but still logged to history) -- a
pleasant sound, a mode-dependent waybar bell icon, and both keybindings
and scroll for switching, "soft and flawless".

Built entirely on mako's own native mode system (`makoctl mode -s
name` + `[mode=name]` config sections) rather than anything custom
-- `invisible=1` suppresses the popup without touching history, exactly
what "dnd" needed. Picked
`/usr/share/sounds/freedesktop/stereo/message.oga` for the sound (the
shortest of the plausible freedesktop chimes by actual `ffprobe`
duration, not a filename guess, and the same file mako's own docs use
as their `on-notify` example) via `on-notify=exec paplay file`.

Three real bugs found by testing, not assumed:

- A global option placed after a `[section]` header silently scopes to
  that section only -- the sound line, first placed after
  `[urgency=high]`, only ever fired for high-urgency notifications.
  Moved above any section header.
- `invisible=1` does not also suppress `on-notify` -- `dnd` mode still
  played the sound until `on-notify=none` was added there too
  (confirmed with a marker-file side effect, decoupled from timing-
  sensitive audio playback). `on-notify=` (empty) is a hard parse error;
  `none` is the documented no-op value.
- mako's active mode resets to its own built-in "default" on every
  daemon restart, with nothing persisting it -- confirmed by killing and
  restarting mako mid-test. Fixed the same way `caffeine-toggle.sh`
  already handles this exact shape of problem: a state file
  (`~/.local/state/notification-mode/current`) plus a startup script
  (`notification-mode-restore.sh`) run after `exec mako` in
  `sway/config`, with the same bounded-retry pattern already used
  elsewhere for daemon-not-ready-yet races.

Switching: `notification-mode.sh normal|silent|dnd|next|prev`,
wired to `$mod+Ctrl+n/s/d` (direct jump), `$mod+n` and the waybar bell's
scroll wheel (cycle). The waybar `custom/notifications` module also
picked up a `"signal": 8` so `pkill -RTMIN+8 waybar` gives an instant
icon/color refresh on switch instead of waiting out the module's normal
poll interval -- confirmed via a screenshot taken immediately after a
keybinding switch, already showing the new color.

Not independently verified: the scroll-wheel wiring itself, same
`ydotool` absolute-mouse-calibration gap disclosed for
`notification-history.py`'s click handler last entry. The `next`/`prev`
cycling logic it calls is fully verified directly (both directions,
correct wraparound); the scroll binding calls the identical script the
verified keybindings call.

## 2026-08-30 (notification-history.py: new feature, plus a real docker-picker.py icon bug)

Asked for a real docker-branded icon on Docker notifications (reported
directly: "only has the docker name in it not the icon of it") and a
notification history viewer (waybar bell left of the clock, newest
first, full details).

Fixed `docker-picker.py`'s `notify()`: was `utilities-terminal` (a
generic terminal glyph, no connection to Docker) for its non-critical
case. Now `docker-desktop`, a real icon Papirus ships -- confirmed it
actually resolves via GTK's own icon theme lookup before using it, not
assumed from the filename.

`notification-history.py`: mako already has a real history buffer, just
needed `history=1`/`max-history=200` turned on (`mako/config`, off by
default). Two real bugs found and fixed while building this: mako's own
`makoctl history -j` ordering isn't reliable (one call came back
newest-first, a later one oldest-first) -- now explicitly sorts on `id`
descending rather than trusting it. And wofi's dmenu input splits on
newline into *separate entries* -- an embedded `\n` between a
notification's summary and body silently produced two unrelated dmenu
items instead of one two-line one, confirmed by testing the actual
selection round-trip. Fixed by keeping one line per entry (summary and
body joined with a separator, same pattern as `docker-picker.py`'s own
info rows) -- long ones still wrap naturally within that one entry.

"Shows full details on focus" isn't architecturally available in wofi's
dmenu mode (no focus-change hook exists) -- confirmed rather than
assumed, and built the honest equivalent instead: every entry already
shows its full summary and body up front. Selecting one copies it to the
clipboard.

Added `$mod+Shift+n`, matching every other waybar-click picker's keyboard
path, verified live via a real keypress. The waybar on-click itself
wasn't independently re-verified with a real mouse click this pass --
disclosed rather than assumed: `ydotool`'s absolute positioning has an
unmet calibration requirement in this environment, and a pixel-sampled
click reliably landed on a different module instead. It uses the
identical JSON pattern as every other already-verified picker, but that's
inference from precedent, not an independent click test. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full writeup.

## 2026-08-30 (Zen Browser confirmed not reacting to the portal signal -- fixed in its profile)

Reported Zen still stayed dark after the packages were actually
installed. Zen was genuinely running, so this got a direct answer:
screenshotted the desktop and pixel-sampled Zen's own toolbar/chrome
area, found it consistently near-black while `dconf read color-scheme`
reported `prefer-light` at that exact moment -- first-hand confirmation,
not just trusting the report.

Traced it to `widget.use-xdg-desktop-portal.settings`, defaulting to `2`
(auto-detect: GTK + Wayland + portal available). Every one of those
conditions is genuinely true here, but it evidently wasn't resolving to
"use it" in this Zen build. Fixed directly in Zen's actual active profile
(found via its `lock` file pointing at the real running PID, not
guessed): `user_pref("widget.use-xdg-desktop-portal.settings", 1);` in
`user.js`, forcing the portal on rather than relying on auto-detection.

Deliberately not added to this repo -- Firefox/Zen profile directory
names are randomly generated per install, not a stable path any stow
package could target. This fix lives only in that profile on this
machine; a fresh install or new profile would need it reapplied. Needs a
Zen restart to take effect (`user.js` is only read at startup) -- not
restarted automatically here, since closing someone's browser out from
under their open tabs isn't this repo's call to make. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full trace.

## 2026-08-30 (theme-toggle.sh: real bug found -- was writing theme names that don't exist yet)

Reported the toggle fires notifications but Zen Browser (set to follow
system theme) never actually switched to light. Verified every layer of
the mechanism directly rather than guessing: `dconf write` genuinely
changes the value; the XDG portal's `Settings.Read`
(`org.freedesktop.appearance`/`color-scheme`) reflects it immediately,
queried directly via `gdbus call`; and -- the layer that actually matters
for a live update with no restart -- the portal genuinely **emits a
`SettingChanged` signal** with the correct new value on both the legacy
and current namespaces, confirmed by monitoring the session bus with
`gdbus monitor` while triggering the toggle. All three layers check out.

The real bug: `catppuccin-gtk-theme-latte`/`papirus-icon-theme`/
`papirus-folders-catppuccin-git` were added to `packages/` when this
toggle was built, but never actually installed (`pacman -Q` fails for
all three -- the handed-off install command hadn't been run yet).
`theme-toggle.sh` was writing `gtk-theme`/`icon-theme` dconf keys
pointing at those names regardless, and a theme name that doesn't
resolve to anything installed fails silently -- apps just keep rendering
whatever they last loaded, indistinguishable from the toggle doing
nothing.

Fixed: now checks `/usr/share/themes/name`/`/usr/share/icons/name`
before writing either key, skips it (leaving the previous working value)
if missing, and notifies clearly naming what's not installed instead of
pretending it applied. `color-scheme` always writes regardless -- no
file dependency, and it's the one signal Firefox/Zen actually need for
their own dark/light CSS, since they don't render via system GTK theme
files the way a native GTK app does. Verified the fix directly with the
packages still missing: color-scheme and the already-installed dark GTK
theme switched correctly, the not-yet-installed light theme/icon-theme
were left alone rather than pointed at nothing.

Confirmed working but outside this repo's reach: whether an app
subscribes to the portal signal at all is up to that app. Firefox-based
browsers have a `widget.use-xdg-desktop-portal.settings` preference
(`about:config`) gating this -- worth checking there if a browser still
doesn't react after this fix. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full verification
trail.

## 2026-08-30 (incident: stow symlinks broken desktop-wide, recovered clean; docker gets a keybinding)

Reported the docker waybar click had stopped working, and asked for a
keybinding matching the other pickers. Chasing the click found something
much bigger: `~/.config/waybar/config`, both wofi files, sway, mako,
nwg-bar, kitty, tmux, every tracked `nvim`/`zed` file, and
`~/.config/systemd/user/tmux.service` had all silently stopped being
symlinks -- real disconnected files instead, `tmux.service` missing
outright (the exact symlink fixed in an earlier pass, broken again).
Almost certainly a well-known dotfiles-via-symlink gotcha, not specific
to this repo: any tool that saves "atomically" (write-temp-then-rename)
replaces a symlink with a real file the instant something saves a
symlinked config directly rather than through the repo path -- explains
why files this session never touched (`nvim`, `zed`) were affected too.

Checked before fixing anything: every affected file was content-identical
to its repo counterpart, safe to just re-link. A second, more serious
mistake happened while fixing it, disclosed in full: tried to fix several
packages at once with one combined `stow -R` call, which **deleted the
repository's own source files** for all of them (confirmed via `git
status` showing 32 files deleted in the working tree) -- GNU Stow's
directory-folding logic behaving unpredictably when several targets are
simultaneously in an inconsistent state within one combined restow.
**No data was lost** -- git history was untouched throughout, `git
restore .` recovered everything in one command, verified by checking
actual file content afterward (not just a clean `git status`). Fixed
properly the second time, one package at a time with verification after
each. Final state confirmed three ways: every `~/.config/pkg` is a real
symlink, `git status` clean, `stow -n` (dry-run) across every package
reports zero pending actions.

With everything reconnected, the docker click started working
immediately. Added `$mod+Shift+d` (`sway/config`) too, matching the exact
convention already used for Wi-Fi/Bluetooth -- `docker-picker.py` had
been waybar-click-only, the same gap those two had before their own
keybindings. Picked up by `keybind-search.py` automatically. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full incident
writeup and the lesson worth keeping in mind going forward.

## 2026-08-30 (docker-picker.py: tree-connector prefix so multiple containers don't blur together)

Asked whether multiple running containers would get confusing in a flat
list. Tested directly rather than reasoning about it in the abstract:
started two real containers (postgres, pgadmin) and generated the actual
menu -- 8 rows total, each container's 2 action rows sitting right below
its info row. Every action row already includes the full container name
("Restart postgres", not just "Restart"), so there's no real *ambiguity*
even out of context, and fuzzy-typing a container name already narrows
the list to just its 3 relevant rows -- but visually scanning a longer
list with several containers running could still blur which action
belongs to which container above it.

Added a `└─` tree-connector prefix to both action rows, so the
info-row-to-action relationship reads at a glance instead of requiring
you to read every line's full text to work it out. Verified by
regenerating the real menu with two containers running and confirming
each container's block reads as a clear group. Restored both test
containers to stopped afterward, matching the state they were in before.

## 2026-08-30 (docker waybar module: nwg-bar's static menu replaced with a real picker)

Asked to improve the docker waybar module -- clicking it opened an
nwg-bar modal (Stats / Stop All) with no visibility into what's actually
running, "of really no use". Same architectural fix already applied to
Wi-Fi and Bluetooth: nwg-bar can only render static buttons from a fixed
JSON file, no dynamic content at all, so `scripts/.local/bin/
docker-picker.py` replaces it with the same wofi `--dmenu` picker
approach.

Per running container: one Sky info row (name, image, status, ports --
view-only, selecting it just re-shows the same info, never destructive)
plus two action rows, Peach "Restart" and Red "Stop" -- two different
colors rather than one shared "command" hue, since stop and restart have
a real severity difference worth signaling on sight. "Open docker stats"
and "Stop all containers" stay available as top-level shortcuts either
way. Verified the actual actions work, not just that the menu renders:
started a real container, restarted it through the picker and confirmed
via `docker ps` its uptime genuinely reset, stopped it the same way and
confirmed via `docker ps -a` it exited -- left the system in the same
all-stopped state it was in before testing.

Removed the now-superseded `nwg-bar/.config/nwg-bar/docker.json` and
`scripts/.local/bin/docker-stop-all.sh` (docker-picker.py's own "Stop all
containers" replaces it) after confirming zero remaining references.

## 2026-08-30 (system-wide dark mode confirmed + waybar toggle + Papirus icon pack)

Asked to make sure dark mode is the default everywhere, add a waybar
toggle, and add a well-regarded icon pack. Dark mode itself was already
mostly in place (`gtk-application-prefer-dark-theme=1`, dconf
`color-scheme=prefer-dark` from an earlier `install.sh` pass) -- the real
gaps were no icon theme ever being set, and no way to switch modes
without hand-typed `dconf write` commands.

Added `papirus-icon-theme` (official `extra` repo -- the most widely-used
general-purpose Linux icon theme) + `papirus-folders-catppuccin-git` to
recolor its folders to this desktop's existing Mauve accent. Verified the
real AUR package name first -- an initial guess doesn't exist on the AUR
at all, found by querying the AUR RPC API directly rather than trusting
memory; the real package is maintained by the official `catppuccin` AUR
account. Also confirmed (by reading its own source) that
`papirus-folders`'s color-switch needs root *every single run*, so
folder recoloring happens once for both palettes in `install.sh` (where
`sudo` is already in use), never at runtime. Added
`catppuccin-gtk-theme-latte` too -- the light counterpart to the
already-installed `-mocha` package, without which the toggle would have
nothing real to switch to.

New waybar `custom/theme` module (left of the wallpaper button):
`theme-status.sh` + `theme-toggle.sh`, pure `dconf` reads/writes, no
state file (dconf already persists on its own). Verified the actual
toggle end-to-end: ran it, confirmed via `dconf read` that
color-scheme/gtk-theme/icon-theme all flipped, screenshotted and found
the waybar icon's color genuinely changed (Sapphire moon -> Yellow sun),
toggled back, left the system in dark mode afterward.

Scope stated plainly: this covers every app that reads the standard
GNOME/GTK dconf keys (file managers, browser GTK chrome, most GTK3/GTK4
apps) -- the actual mechanism behind "apps detect OS dark mode." Does
**not** touch this desktop's own hand-built waybar/wofi/mako/sway
styling, a deliberate scope decision, not an oversight. Qt theming
(qt6ct) left unconfigured -- no actual Qt GUI app in this setup to verify
against (`beekeeper-studio-bin`/`bruno-bin` are both Electron), disclosed
as a real gap rather than blind-configured. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full writeup.

## 2026-08-30 (wofi text readability: two dead ends, then the real fix)

Asked again to make text more readable ("black instead of white") after
the previous pass found the visible white patch was actually icon pixels,
not text. This time it genuinely was `#text`. Two direct attempts failed
before finding the real cause, both disclosed rather than silently
discarded: literal black text measurably backfired (this window's own
base tint is already near-black, so near-black text has ~zero contrast
against *it*, confirmed by screenshot); a subtitle-style dark outline
around bright text (the actual standard fix for this exact problem)
didn't work either because `text-shadow` parses without error in this
GTK/wofi build but doesn't render at all (confirmed with a stress test:
zero dark pixels anywhere when an outline should have produced plenty).

Real fix: raised window background opacity `0.62` -> `0.85` (less of the
blurred wallpaper's brightness variance can bleed through and wash out
text, without removing the blur itself) and text color `#A6ADC8` ->
`#CDD6F4` (Catppuccin "Text", same bright value mako already uses) for
extra margin. Real, disclosed tradeoff: less see-through glass than
before. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 2026-08-30 (app launcher: icon/name gap fixed; the "white" turned out to be real icon pixels)

Asked for a gap between the app icon and name (too close), and for the
color to be black instead of white. Gap: `#img` had zero spacing before
this, `margin-right: 10px` fixes it (confirmed `#img` is a real CSS node
by testing a temporary bright background first, not assumed).

The "white" investigation is worth recording since it looked like a bug
at first and wasn't one: found a near-white patch, assumed unstyled
`#text`, tested with `!important` (would beat any competing rule) and a
bare `label {}` type selector -- neither had any effect. Isolated the
patch by shape/position instead of guessing more selectors: it's real app
icon pixel data, not text -- raster icons aren't recolorable by CSS
`color` at all. Gave `#img` a dark rounded backing instead
(`rgba(17,17,27,0.5)`, matching how GNOME Activities/macOS Spotlight
handle the same problem), which helps icons with real transparency but
can't repaint pixels an icon already drew opaque -- disclosed as a real,
partial fix (near-white pixel count: 206 before, 209 after, i.e.
unchanged for opaque-background icons) rather than claimed as fully
solved. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 2026-08-30 (wofi color-palette consistency audit: one bug fixed, one gap filled)

Audited every wofi-invoking script for palette consistency plus a general
bug/improvement look. Most already matched (`wifi-picker.py`/`bluetooth-
picker.py` already share the exact Sky/Teal/Peach system and wofi's own
`#313244` surface color). Two real fixes:

- `bluetooth-picker.py`'s "Enable Bluetooth" entry had a hardcoded
  `#FAB387` span instead of reading `CATEGORY_COLORS["command"]` -- same
  value, but a second copy that would silently drift if the palette ever
  changed. Fixed to read from the shared dict.
- `keybind-search.py` had zero color-coding despite having two real
  categories (Sway/Tmux) to distinguish -- the one wofi popup in this
  desktop without it. Added Sky/Teal source-tag coloring (same hues as
  the other pickers) plus Peach for the `[scope]` suffix. Verified this
  doesn't break `--matching fuzzy` (the one flag none of the other
  pickers use) with a controlled test: piped markup-containing entries
  into wofi directly, searched a query that only matches one entry's
  visible text, confirmed via the actual selected output that fuzzy
  matching operates on rendered text, not the raw `span` tags.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full writeup.

## 2026-08-30 (keybind-search.py: truncate descriptions, fixing right-side overflow)

Reported the keybind search popup's right side overflows. Real cause: a
couple of the sway descriptions built by this tool are enormous -- the
exit-sway confirmation's swaynag message came to 243 characters,
~1750px at this font, well past the 1152px (60%) window. wofi has no
ellipsize/wrap control exposed for `--dmenu` entries (checked `--help`
and the binary's own exported symbols). Truncates in the script itself
now (`MAX_DESC_LEN = 78`, appends `…`) -- longest entry after the fix is
123 chars, was 243. Verified by pixel-checking the popup's right edge in
a screenshot: nothing beyond background level 2px past the window
boundary. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 2026-08-30 (wofi: fixed -- left border was invisible on every entry, always)

Reported left/right edges of rows/cells weren't visible properly. Real
bug: an earlier revision force-set `border-left: 2px solid transparent`
on every entry (reserving space for a selected-state accent bar without a
layout jump), which made the left edge invisible at rest on *every*
entry, not just unselected ones -- in the grid, one cell's visible right
border next to the next cell's invisible left border read as a broken,
asymmetric gutter. Fixed by dropping the override and keeping border
width constant (1px) in every state, differentiating selected by color
alone (`#CBA6F7`, full strength) instead of width -- simpler than what it
replaced, and needs no layout-jump guard since nothing changes size.
Verified by comparing a cell's right border against its neighbor's left
border pixel-for-pixel: now symmetric, not just present.

## 2026-08-30 (wofi: real gutters between entries, for every wofi tool)

wofi has no dedicated row/column-spacing option, so this is `margin: 5px`
on `#entry` itself -- the standard GTK-CSS way to create gaps between
FlowBox children. Shows up as real gutters in the app launcher's grid and
as breathing room between rows in every other wofi tool's list, since
they all share the one `style.css`. Verified with the same real-keypress
method the app-launcher-grid bug required (`ydotool`-simulated `$mod+d`
and `$mod+Shift+w`, not a manual shell reproduction): confirmed the grid
still fits 4 real columns with the new margin, and a real ~11px gap now
exists between list rows.

## 2026-08-30 (the real bug: a bare comma inside exec, silently dropping --columns 4)

Reported a second time that `$mod+d` still showed a single column. Every
prior check had tested the wofi command directly in a plain background
shell, which never goes through sway's own `exec` parsing at all -- the
real `$mod+d` keybinding does, and had never actually been tested that
way. Simulated a genuine keypress with `ydotool` (kernel-level input
injection, not a manual reproduction) and compared the actual running
process's command line against what was configured: real presses were
launching `wofi --show drun` -- no `--columns 4` at all.

Root cause: sway's config syntax uses a bare comma to chain multiple
commands on one `bindsym` line, and `exec`'s argument isn't exempt --
`wofi --show drun,run --columns 4` was being silently truncated to `wofi
--show drun` by sway itself before wofi ever saw it, dropping `--columns 4`
along with everything after the comma. This is exactly why the fix looked
correct at every prior check and still didn't work: the flag never reached
wofi in the first place, so no CSS/width change could have fixed it.

Fixed by dropping `",run"` from `$menu` -- `--show drun` alone has no
comma to trip sway's parser. "run" mode (arbitrary `$PATH` executable by
typed name) wasn't part of what was asked for anyway. Reverified with the
same real-keypress method, twice: `$mod+d` now genuinely launches `wofi
--show drun --columns 4`.

Also moved `width=60%` into the shared `wofi/config` per request (every
wofi popup in this desktop, not just two of them) -- removed the
now-redundant `--width 60%` that had been repeated on both `$menu` and
`keybind-search.py`'s own invocation, so there's exactly one place
controlling it. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full writeup,
including the general lesson: testing a command directly is not proof the
*same* command works when run through `exec` from a keybinding.

## 2026-08-30 (fix: app launcher grid wasn't actually 4 columns; entry borders were too faint)

Reported the app launcher still showed a single column. The earlier
verification pass was genuinely wrong: checked for "content blocks with
gaps" in a screenshot and called it done, but never counted actual
columns. Redid it properly (clustering content by x-position per row) and
found the real bug -- at the shared config's 600px default width,
`--columns 4` only ever produced 2 real columns, since real app names
("Beekeeper Studio") are wide enough that GTK's column count is a ceiling
that width constrains, not a forced number. Fixed by widening the
launcher specifically (`--width 60%`, only on `sway/config`'s `$menu`, not
the shared `wofi/config`) -- reverified with the same clustering check and
found 4 genuine, evenly-spaced columns this time.

Also added a real border to every entry, not just the existing left
accent bar on selection -- asked for so grid rows read as distinct tiles.
Same lesson repeated: first attempt (12% alpha) parsed cleanly but was
nearly invisible once actually screenshotted, not "properly aesthetic" as
asked just technically present. Raised to 28% at rest / 35% hover / 45%
selected, confirmed this time by finding a real brightness jump at each
entry's border row in a screenshot rather than trusting the CSS had no
syntax errors as proof it looked right.

## 2026-08-30 (wifi/bluetooth pickers get keybindings; keybind search resized; app launcher grid)

Three follow-ups to the wofi glass work above:

- `$mod+Shift+w` (Wi-Fi picker) and `$mod+Shift+b` (Bluetooth picker) --
  both scripts already existed and worked fine, just had zero keyboard
  path, waybar-click-only. Automatically shows up in `keybind-search.py`
  with no extra work (the whole point of reading live config), but hit
  the same multi-line-comment gotcha its own entry did earlier -- fixed
  the same way, clean one-line description directly above each `bindsym`.
- `keybind-search.py`'s wofi popup: `--width 60%` (percentage width is
  real, confirmed via `swaymsg -t get_outputs` echoing back the literal
  pixel math, 1152 on this 1920px output) and `--lines 15` -> `12`
  (measured extent 647px -> 536px tall, ~17% shorter).
- `$mod+d`'s app launcher: `--columns 4`, added only to `sway/config`'s
  `$menu` variable, not the shared `wofi/config` -- every other
  wofi-backed tool in this desktop is a single-column list and a grid
  would break it. Confirmed live that wofi's grid genuinely reads as
  uneven/organic (GtkFlowBox sizes each entry to its own content, not a
  fixed cell) rather than a uniform card grid, by screenshotting and
  checking for real gaps between discrete content blocks at multiple row
  heights.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full writeup.

## 2026-08-30 (wofi: real glass -- compositor blur, not just a tinted box)

Asked to make wofi look more "glass", better UI/UX generally. Recognized
first that a semi-transparent `background-color` alone (0.95 alpha before
this, basically opaque) was never going to read as real glass, and that
GTK3's CSS engine has no `backdrop-filter` -- that's not achievable in
wofi's own stylesheet at all. The actual fix: this desktop's own sway build
is SwayFX (`scenefx0.4`, already in `packages/aur.txt`, already used for
window shadows/corner-radius), which supports real compositor-level blur
on specific layer-shell surfaces by namespace -- just never wired to wofi.
Confirmed wofi's real namespace live (`swaymsg -t get_outputs` while it was
open) rather than assumed, added `layer_effects "wofi" { blur enable;
blur_xray enable; corner_radius 16; shadows enable; }` to `sway/config`.
Verified it's actually applied two ways: the compositor's own IPC echoes
back `"blur": true`, and a direct pixel test found the screen region behind
an (temporarily near-transparent, for testing) wofi window rendered 4x
smoother than the same region without it open.

With real blur behind it, rebuilt `wofi/style.css` to let it show through
instead of hiding it: background alpha 0.95 -> 0.62, a faint top-edge sheen
gradient (the light-catching highlight a real glass panel shows), a
brighter hairline border on the search input than the outer window so it
reads as sitting closer to you than the glass pane behind it, and a
properly restyled scrollbar (was completely unstyled GTK-default light
gray before -- about as glass-breaking a seam as it gets). Also real UX
gaps, not just look: `#entry:hover` didn't exist at all before (zero mouse
feedback, only keyboard `:selected`), and selection gained a left accent
bar alongside its existing background wash. `wofi/config`'s `image_size`
24 -> 32 for better icon hierarchy in `drun`. Every wofi-backed tool in
this desktop (launcher, wifi/bluetooth pickers, calculator, emoji picker,
cliphist, networkmanager-dmenu) shares this one stylesheet, so all of them
get this at once. Tested both `--show drun` and `--show dmenu` directly,
checked stderr for CSS parse warnings on each (none) before trusting any
of it. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full
writeup.

## 2026-08-30 (notification beautification: real icons on every notify-send call)

Asked to make notifications more aesthetic, specifically with icons for
whatever triggered them. Audited every `notify-send` call in the repo
(`grep -rn notify-send scripts/ sway/`) -- several already had one (docker,
caffeine, the wallpaper/screenshot success cases use the actual resulting
image), most didn't, including two that fire constantly: volume and
brightness OSDs had no icon at all.

Added a real freedesktop icon-theme name to every remaining call, each
confirmed present in the actually-installed icon theme first (only
`adwaita-icon-theme`/`hicolor-icon-theme` are installed here -- no
Papirus/Catppuccin icon pack, so stuck to what's real rather than assuming
a name exists). Volume got the same "tiered by actual state" treatment as
waybar's battery icons (`audio-volume-{muted,low,medium,high}-symbolic`
by percentage) instead of one static glyph; also dropped a redundant inline
Nerd Font mute glyph from the notification body now that a real icon
carries that signal. Bluetooth's icon follows urgency (error vs. active).
Wallpaper's fallback/failure notifications now visually distinguish soft
warnings from hard failures, matching their actual urgency levels which
were already different but only readable in the text before.

`mako/.config/mako/config` got `max-icon-size=48` + `icon-border-radius=8`
to match the rounded-pill look used everywhere else in this desktop --
mako's icons render sharp-cornered at native size by default otherwise.

Verified live, not just by reading mako's docs: fired real test
notifications after each change, screenshotted, and confirmed real
non-background pixel content actually appears in the icon's expected
position -- an icon name that fails theme lookup fails silently (blank
space, no error), which is exactly the kind of thing that looks fine in
the config file and wrong on screen. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full icon-by-icon
breakdown.

## 2026-08-30 (new feature: fuzzy keybinding search, `$mod+Shift+slash`)

Asked for a wofi popup to fuzzy-search every keybinding on the system (sway +
tmux, deliberately excluding Neovim -- it already has its own keymap search)
by name/keyword, case-insensitive.

`scripts/.local/bin/keybind-search.py`, bound to `$mod+Shift+slash` (matches
the near-universal ? / Ctrl+/ "show shortcuts" convention -- Slack, Discord,
GitHub, GNOME). Both sources are re-parsed from the real live config on every
run rather than a separate hand-maintained list -- picked this over the
alternative specifically because a second list is exactly the kind of thing
that quietly drifts out of sync with reality, the same failure mode as the
TPM plugin-path split found in an earlier audit pass. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design writeup,
including two real parsing bugs found and fixed by checking actual command
output instead of trusting the documented format (tmux's `-N` compact view
mislabeling root-table binds as needing the prefix; an early version's
custom-note lookup bleeding a prefix-table note into an unrelated same-letter
copy-mode binding), a fuzzy-search gap fixed along the way (bare-comment
descriptions like "Switch to workspace" couldn't match a query typed as
"workspace 1" since the "1" only existed *before* the word in that entry --
now every entry appends its actual command for exactly this reason), and why
the final `wl-copy` call is a detached `Popen` rather than `subprocess.run`
(confirmed directly: wl-copy sets the clipboard instantly but the process
itself lingers afterward by design, to keep serving the selection -- waiting
on it would hang the script pointlessly after every use).

Gave tmux.conf's own custom binds real `-N` notes as part of this (was `bind
s display-popup ...`, now `bind -N "Fuzzy-find and switch tmux session" s
...`) -- a genuine side benefit, not just plumbing for this script: tmux's
own `prefix + ?` (list key bindings) now describes this repo's custom binds
too, not just its stock ones.

Also fixed, unrelated but found along the way while testing: this repo's
`~/.local/bin/wl-paste --type text --watch cliphist store` background
watcher had been killed (by an earlier debugging step in this same session,
chasing what turned out to be the wl-copy lingering-process behavior above,
not a real bug) and not restarted -- caught and fixed immediately, since it's
a real, already-established feature ($mod+m clipboard history) this
shouldn't have been left broken.

## 2026-08-29 (full repo audit: tmux plugin path split fixed)

Broadened the previous audit to the whole repo. First finding: `tmux/.config/
tmux/plugins/` was sitting untracked in the repo tree (`tmux-continuum`,
`tmux-resurrect`, and a second copy of `tpm`, each with their own nested `.git`
dirs) even though `install.sh` clones TPM to `~/.tmux/plugins/tpm` and nothing
in this repo ever mentions `~/.config/tmux/plugins/`. Almost deleted it outright
as accidental vendored content, matching the `lock.sh` pattern from the previous
audit -- caught the mistake by tracing *why* `install_plugins.sh` reported
"Already installed" for plugins that didn't exist at `~/.tmux/plugins/`: TPM's
own bootstrap script auto-redirects `TMUX_PLUGIN_MANAGER_PATH` to `~/.config/
tmux/plugins/` whenever it detects an XDG-style `tmux.conf` -- which this repo's
stow layout always produces. The content was real and live (`tmux.service`'s
`ExecStop` was already correctly pointing at it), not dead code.

Fixed at the source instead of papering over it: pinned `TMUX_PLUGIN_MANAGER_PATH`
explicitly in `tmux.conf` (TPM's own documented override, placed before the
`@plugin` lines) to `~/.tmux/plugins/`, migrated the real `tmux-resurrect`/
`tmux-continuum` content there, discarded the redundant duplicate `tpm` clone
(the real one already lives at `~/.tmux/plugins/tpm`), removed the now-empty
`tmux/.config/tmux/plugins/` from the repo, and updated `systemd/.config/
systemd/user/tmux.service`'s `ExecStop` path to match. Verified with a real
tmux session: `TMUX_PLUGIN_MANAGER_PATH` resolves correctly, `install_plugins.sh`
finds all three plugins in the new location without re-cloning, and
`tmux-resurrect`'s `save.sh` runs cleanly from it. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full writeup.

## 2026-08-30 (network speed indicator: real bug found in how I'd been "verifying" it)

Reported the previous pass's 160px change hadn't actually changed anything visible.
Investigated rather than re-guessing a number, and found a real process bug in my
own verification, not just the CSS: **waybar had been running the same PID since
23:27 the entire time** -- every earlier "reloaded live, same PID, no crash" claim
in this session's changelog was actually confirming the *opposite* of what it
said. Waybar does not hot-reload config/style.css from a file-watcher (that was
an unverified assumption, stated as fact); it needs an actual process restart.
Every style/font/padding change from the last two passes had been sitting correct
in the files but never live on screen until now.

With that fixed (`pkill waybar` + relaunch, confirmed via a fresh PID each time),
re-measured the network speed module for real instead of estimating: temporarily
forced its format to a literal `123.12KB` on both sides (the exact worst case
asked for), screenshotted, and located the true rendered bounds by color-matching
the format string's own Green (`#A6E3A1`)/Peach (`#FAB387`) span colors pixel-by-
pixel rather than eyeballing -- download span 386-454px, upload span 470-538px,
153px of real content between them. With the shared 12px/side padding this
module's id also picks up, natural pill width at that exact worst case is
12+153+12 = **177px** -- bigger than the previous 160px guess, meaning 160 was
actually too narrow for "123.12" on both sides, not too generous.

Set `min-width: 177px` -- fits the stated worst case exactly, no slack beyond it.
Re-measured current *real* traffic the same way afterward: 124px of content right
now (148px natural width), meaning there will still be visible empty space during
normal/light traffic, since a fixed min-width is a floor that can't shrink below
itself -- that's what reads as "too much padding" day-to-day, and it's the
necessary cost of the pill never growing/jittering when traffic actually reaches
three-digit KB values on both sides, which was the explicit requirement. Flagged
this trade-off directly rather than picking a number that quietly abandoned one
side of the request.

## 2026-08-30 (network speed indicator narrowed to match the new smaller font)

`#network.speed, #network-speed`'s `min-width: 200px` -> `160px`. That value was
originally set by measuring the module's actual live rendered width at the bar's
old 15px font (177px) and adding headroom to stop it jittering as digit counts
change (12KB vs 1.2MB vs 999B). Rather than re-measuring from scratch, scaled it
by the same ratio the font-size change in the previous pass introduced: JetBrains
Mono is monospace, so glyph advance width scales ~linearly with font-size --
200 * (12/15) = 160. Reloaded live (waybar's own file-watcher, same PID
afterward, no crash) rather than assumed.

## 2026-08-30 (narrower workspace buttons, one font size across the whole desktop)

- **`#workspaces button` padding**: `0 8px` -> `0 5px`. Same three states (idle
  gray / hover Lavender / focused Red underline) and layout-jump guard
  (transparent `border-bottom` reserving space so nothing shifts on hover),
  just narrower chips -- the ask was width, not anything else about them.
- **One font size (12) across every config that sets one explicitly**, instead
  of each app carrying whatever its own default happened to be:
  - `kitty` 15 -> 12 (this one was already sitting as live, uncommitted drift
    from before this session touched anything -- formalized it into the repo
    rather than fighting it, since it's exactly the value being standardized
    on anyway)
  - `waybar` (global bar text) 15px -> 12px
  - `zed` `ui_font_size`/`buffer_font_size`/terminal `font_size` 15.0 -> 12.0
  - `wofi` 16px -> 12px
  - `nwg-bar` (power menu) 15px -> 12px
  - `mako` (notifications) 10 -> 12
  - `sway` (`font pango:`, window title text) 10 -> 12

  **Deliberately left untouched**: `sway/.config/sway/lockconfig`'s
  `font-size=80`. That's swaylock's big on-screen clock/PIN-attempt display,
  not body text -- a fundamentally different UI role (glanceable from a few
  feet away, not read up close), and normalizing it to 12 would make the lock
  screen's whole reason for a large font pointless. No GTK-wide font-name
  override exists in this repo for either `gtk-3.0`/`gtk-4.0` `settings.ini`,
  so nothing there needed changing.

  12 isn't an unreasonable size on its own -- it's a common, legible terminal/
  UI size and matches what was already live in kitty -- but it is on the
  smaller side for extended reading specifically in `zed`'s buffer font and
  the waybar text glanced at across a room; worth a quick look after this
  lands and bumping just those two back up first if it feels cramped, rather
  than assuming the whole set needs to move together again.

Reloaded live to verify nothing crashed: `swaymsg reload` (font pango line),
waybar (auto-reloads config/style.css via its own file-watcher, still running
same PID afterward), `makoctl reload`. No visual regression tooling available
in this session to pixel-verify beyond that, but every change here is a plain
numeric font-size/padding value, not a codepoint or anything else with a
history of silent corruption in this repo.

## 2026-08-29 (docker cruft reclaimed; .pacnew/.pacsave files analyzed)

Followed up on the two items flagged earlier.

**Docker**, done directly (no sudo needed, `yash` is already in the `docker` group):
inspected exactly which volumes each stopped container actually references before
touching anything -- `postgres` -> named volume `postgres-data`, `pgadmin` -> one
anonymous volume, both still "in use" from Docker's own point of view even while
their containers are stopped, so neither `docker volume prune` nor manual removal
would ever touch them. The other 5 volumes had zero container references at all
(running or stopped) -- confirmed, then removed. Same check for images: `alpine`
and `nginx` had zero containers referencing them (not even a stopped one), while
`postgres:18`/`postgres:latest` (same image ID) and `dpage/pgadmin4:latest` are
still the exact images the stopped containers point to. Removed `alpine`/`nginx`
(~254MB) and the 5 orphaned volumes (~66MB). Containers, their real volumes, and
the images they actually reference are all untouched -- `docker start postgres`/
`docker start pgadmin` still works exactly as before.

**`.pacnew`/`.pacsave` files**, diffed and analyzed (system has no `pacdiff` --
`pacman-contrib` isn't installed -- so diffed each manually against its live
counterpart):
- `/etc/pacman.d/mirrorlist.pacnew` -- **do not apply**. The live file has real,
  working, hand-picked India-region mirrors; the `.pacnew` is upstream's blank
  template with every server commented out. Applying it would leave pacman with
  zero usable mirrors. Recommendation: just delete the `.pacnew`.
- `/etc/bluetooth/main.conf.pacnew` -- safe to apply. Only real live customization
  is an explicit `AutoEnable=true`; the `.pacnew` comments that same line out, but
  its own documented default is also `true`, so behavior is unchanged either way.
  Everything else added is a new, fully-commented `[ChannelSounding]` section --
  inert until someone opts in. Recommendation: adopt the `.pacnew`.
- `/etc/locale.gen.pacnew` -- **do not apply**. It comments out `en_US.UTF-8`,
  which the live file has active and generated. Applying it wouldn't break
  anything immediately, but a future `locale-gen` run would stop regenerating
  that locale. Recommendation: delete the `.pacnew`, keep the live file as-is.
- `/etc/greetd/config.toml.pacsave` -- fully orphaned. `greetd` isn't even
  installed anymore (`pacman -Q greetd` -- not found) and `sddm` is the actual
  enabled display manager; the live `config.toml` this `.pacsave` was saved
  alongside doesn't exist either. Recommendation: `sudo rm -rf /etc/greetd`.

Handed off as exact commands (see below) rather than applied -- all four live
under `/etc`, root-owned, outside this session's access.

## 2026-08-29 (verified: the handed-off sudo cleanup ran clean)

User ran the two hand-off commands from the pass above (`pacman -Rns` on the 12
orphans, `pacman -Sc`). Verified the result rather than assuming it went fine:
`/var/log/pacman.log`'s transaction shows exactly the 12 flagged packages removed
plus 4 of their own now-orphaned sub-dependencies (`wayland-protocols`,
`python-tqdm`, `ninja`, `libmfx`), zero errors/warnings, clean completion. Disk
38G -> 24G used. `pacman -Qdtq` (orphans), `pacman -Qk` (missing package files),
and `pacman -T $(pacman -Qqe)` (unsatisfied deps) all come back clean. Confirmed
the non-debug counterpart of every removed `-debug` package is still installed
and actually running (`swayfx`, `swaylock-effects`, `sway-audio-idle-inhibit-git`,
etc. -- `-debug` packages only ever contained split-out debug symbols, never the
real binary). `systemctl --failed` clean at both system and `--user` scope. Repo/
stow state unchanged. Docker was untouched, as recommended -- still needs a
manual look before anything there gets pruned.

## 2026-08-29 (broader cleanup: empty repo dir, npm cache, system cruft surveyed)

Asked to look at the whole setup for stability/reliability again and remove anything
unnecessary. Repo/stow/systemd health re-checked clean (no regression since the
stability pass above). Widened the sweep to actual disk/package cruft this time,
not just config correctness:

**Fixed directly (safe, no data loss possible):**
- `zed/.config/zed/themes/` was an empty directory sitting in the repo tree,
  genuinely untracked by git (git can't represent empty dirs, so `git status` never
  showed it) -- a fresh clone + stow would never recreate it, meaning it did
  nothing for anyone; almost certainly leftover from Zed's own first-run config
  scaffold getting vendored wholesale when the `zed` package was created. Removed.
- `~/.npm` cache was 312M, entirely regenerable. Cleared with `npm cache clean
  --force`, down to 124K.

**Surveyed, not touched -- needs `sudo` (outside this session's access) or a
judgment call about real data this session can't make safely:**
- **12 orphaned pacman packages** (`pacman -Qdtq`): `bruno-bin-debug`, `ffmpeg4.4`,
  `go`, `meson`, `mongosh-bin-debug`, `scdoc`, `sway-audio-idle-inhibit-git-debug`,
  `swayfx-debug`, `swaylock-effects-debug`, `wlogout-debug`, `wlroots0.20`,
  `yay-debug` -- installed as dependencies, nothing currently requires them.
  `sudo pacman -Rns $(pacman -Qdtq)` removes them; worth a quick skim of the list
  first since "orphaned" means "nothing depends on it right now," not "definitely
  never wanted."
- **`/var/cache/pacman/pkg/` is 8.6G**, including a couple dozen `download-*`
  temp directories this session couldn't even read (root-owned) -- normal pacman
  cache accumulates every version ever installed, not just the current one.
  `sudo pacman -Sc` clears everything except currently-installed versions; `yay
  -Sc` for the AUR cache too. Installing `pacman-contrib` gets you `paccache -d`
  (dry-run preview) if a look-before-you-leap pass is preferred over pacman's
  built-in prompt.
- **Docker has real reclaimable space, but some of it may be wanted data**:
  `docker system df` shows 2 stopped containers (`postgres`, exited 2 weeks ago;
  `pgadmin`, exited 2 months ago -- both clean exits, not crashes) and 2 fully
  dangling images (`alpine`, `nginx` -- zero containers using either). `docker
  image prune` is safe (only removes untagged/dangling images, and none of the
  5 images here are actually dangling in that sense -- so it'd be a no-op; the
  reclaimable size docker reports is against currently-unused-but-tagged images,
  which needs `-a` and is exactly the kind of thing worth a manual look first).
  Deliberately did **not** run `docker container prune` or `docker volume prune`:
  5 of 7 docker volumes are unattached, and at least one is very likely the
  `postgres` container's actual database files -- pruning containers/volumes
  blindly could permanently delete a real local database with no backup. Left
  for the user to review with `docker volume ls` / `docker inspect postgres`
  before deciding.

Journal (322.7M total, 103.5M user-level) and the wallpaper archive (60/60 files,
self-capped at `MAX_ARCHIVE_FILES`, 20M total) were both already within normal,
self-managed bounds -- nothing to do there.

## 2026-08-29 (stability pass: missing symlink, dead archive symlinks, a false alarm chased down)

Asked to check for "corrupt files" and confirm the whole system is stable. Checked
systematically rather than guessing: `git status`, a repo-wide broken-symlink scan
(`find ~ -xtype l`), every `systemctl --user` unit's actual state + journal, and
system-level failed units / disk / memory. Two real, fixed issues, and one thing
that looked broken but wasn't:

- **`tmux.service`'s stow symlink was simply never created.** `~/.config/systemd/
  user/tmux.service` didn't exist at all, even though `systemd/.config/systemd/user/
  tmux.service` is a real, correct file in this repo (and got edited earlier today
  for the plugin-path fix above) -- `stow -n -v -t ~ systemd` confirmed it as a
  pending `LINK`, not a conflict, so it had just never been linked, probably because
  `stow systemd` was last run before this particular unit file existed in the
  package. Harmless while the unit stays intentionally un-enabled (per `install.sh`),
  but `systemctl --user enable --now tmux.service` would have failed outright with
  "unit not found" if anyone tried it. Fixed with `stow -R -t ~ systemd`; confirmed
  `tmux.service` now shows `Loaded: loaded ... linked` (still correctly not
  `enabled` -- the restow only fixes the missing symlink, doesn't opt it in).
- **Five dead, broken symlinks inside `~/Pictures/Wallpapers/Archive/`** (dated Jun 7,
  Jun 14, Jun 15, Aug 12, Aug 23 -- clearly debris from earlier iterations of
  `fetch_wallpaper.sh`'s archiving logic, predating the current `-type f` guard in
  the archive `find`/`mv` step, which correctly excludes symlinks going forward).
  Each pointed at a plain-date-named file (`Active/wallpaper-20260607.jpg` etc.)
  that no longer exists there, since `Active/` only ever holds the current day's
  file. Confirmed genuinely dead via `readlink -f` before deleting, and confirmed
  no *other* corruption in the wallpaper pipeline while at it: scanned every real
  archived `.jpg` with `file --mime-type` for the historical "JSON blob saved as
  .jpg" bug (documented above) -- none found, `is_valid_image()` is doing its job.
  Deleted the 5 dead links; 55 genuine archived wallpapers untouched.
- **False alarm, chased down rather than assumed**: `swayidle.service` showed as
  crash-looped in the journal (`status=253`, "Unable to connect to the compositor")
  right after this boot, then landed `inactive (dead)`. Looked like a real bug at
  first glance. Traced it fully: the crash-loop itself is the already-documented,
  harmless startup race (`swayidle.service` is `WantedBy=default.target` so systemd
  auto-starts it before sway's own `dbus-update-activation-environment --all` has
  run) -- and the reason it's *staying* stopped afterward isn't a bug at all:
  `~/.local/state/caffeine/enabled` exists (caffeine mode has been ON since
  2026-08-28 16:37), so `swayidle-startup.sh` is correctly stopping it every login,
  exactly as designed. Confirmed via `WAYLAND_DISPLAY` being present in
  `systemctl --user show-environment` and a clean manual `swayidle -C ...` run
  succeeding outside the race window. **Not fixed, because it isn't broken** --
  flagged to the user instead: caffeine mode has quietly been on for over a day,
  meaning idle lock/dim/suspend have been off that whole time, which may or may not
  be intentional.

System-level check: no failed system units, 406G free disk, no swap pressure,
9.6G RAM with 7.8G free. Nothing else needed attention.

## 2026-08-29 (full repo audit, continued: docs staleness, a second dead ordering directive)

Read through every remaining config in the repo (mako, wofi, nwg-bar,
networkmanager-dmenu, zed, gtk, xdg, docker security docs, all systemd units, every
script under `scripts/.local/bin/` and `sway/.config/sway/scripts/`) looking for the
same two things as the tmux fix above: redundant/uncoordinated config, and stale docs.
Most of it checked out clean -- well-commented, internally consistent, no dead code.
Two real findings:

- **README.md's repository-structure tree and manual `stow` command example were
  missing `networkmanager-dmenu`** -- a fully-wired package (confirmed correct in
  `docs/ARCHITECTURE.md`'s package-map table and `packages/pacman.txt` already), just
  never added to these two illustrative lists when the package was introduced. The
  "stow everything" catch-all command in the same section already picks up new
  packages automatically (`find . -maxdepth 1 -mindepth 1 -type d ! -name packages
  ! -name docs ...`), so this was cosmetic/doc-only, not a functional gap -- but a
  reader following the manual per-package example would've missed it. Added it to
  both lists.
- **`wallpaper.service`'s `After=network-online.target` is itself a no-op** for the
  same underlying reason `graphical-session.target` was found to be one in the
  previous audit pass: `systemctl --user list-unit-files network-online.target`
  returns zero unit files -- it's a system-level target never instantiated in the
  `--user` manager's namespace, so ordering against it is accepted but enforces
  nothing. Not a functional bug in practice -- `fetch_wallpaper.sh`'s own `nmcli`
  connectivity check, download timeouts, and three-tier fallback already fully cover
  "network isn't up yet" -- but the unit file's own ordering directive was
  misleading about where that protection actually comes from. Documented in
  `docs/ARCHITECTURE.md` rather than deleted, since it costs nothing and still states
  the intent even though it doesn't enforce it.

## 2026-08-29 (desktop audit: dead lock script removed, wallpaper boot race fixed)

Asked to audit the wallpaper/lock screen setup specifically for redundancy and
boot reliability. Two real, concrete findings, not just a general tidy-up:

**Dead code**: `sway/.config/sway/scripts/lock.sh` was a second, completely
different swaylock invocation (small plain ring, no theming, no clock) sitting
next to the real one (`lockconfig`, Catppuccin-themed, used by all four actual
lock trigger points: the manual keybind, the idle timeout, before-sleep, and the
power menu's Lock button). Confirmed it was referenced nowhere with an exact grep
for the literal filename -- an earlier sloppier attempt with an unescaped `.` in
the pattern had falsely matched prose like "padlock shape" in this very
CHANGELOG, which is exactly the kind of false-confidence a lazy grep produces.
Deleted, re-stowed to clean up the dangling symlink it left in `~/.config/sway/
scripts/`.

**Wallpaper boot race**: `wallpaper.timer`'s `Persistent=true` catches up a
missed daily run on boot, but `wallpaper.service` is only ordered `After=
network-online.target` -- nothing ties it to sway actually being up yet.
`graphical-session.target` looked like the fix, checked before assuming it'd
help (`systemctl --user status graphical-session.target`): real loaded unit,
stays `inactive (dead)` the entire session, since nothing in this sway config
ever activates it -- would've been a no-op dependency. A boot-time catch-up run
could genuinely race sway's own startup and hit `apply_background()`'s single
instant socket check before the IPC socket exists -- `current.jpg` still gets
updated on disk either way, but the live `swaymsg` apply would silently give up,
leaving yesterday's wallpaper showing until a reload that never happens on its
own. Fixed with a 20s retry loop instead of one check -- costs nothing in the
normal case (manual click, or the timer's ordinary daily run well after login),
where the socket's already there and it returns on the first try.

Also traced whether a genuinely from-scratch install would work at all:
`install.sh` enables the wallpaper timer before sway has ever started, but
`Persistent=true`'s standard systemd semantics fire an immediate catch-up run in
that case, which reaches `current.jpg`'s symlink creation regardless of whether
the live apply succeeds -- so sway's static `output * bg current.jpg fill` line
should find a real file on its very first startup, not a dangling reference. Not
independently verified with an actual fresh install (same documented gap the
rest of `install.sh` already has) -- rests on documented systemd behavior, not a
fresh empirical test.

## 2026-08-29 (wallpaper button was always fetching the exact same image)

Reported clicking the wallpaper icon repeatedly always produced the same
wallpaper. Verified the actual cause rather than assuming the script was
broken: curled the fixed API URL (`index=0`, `mkt=en-US`) twice a few seconds
apart and compared md5sums -- identical. Bing's "wallpaper of the day" for a
given index+market is genuinely static for the whole day; `WALLPAPER_URL`
being one hardcoded URL meant every click just re-downloaded the same bytes
no matter how many times it ran.

Also verified what actually *does* vary it before building a fix around
assumptions: `index` (0-7ish, recent past days) changes the photo, and so
does `mkt` (country/locale) -- tested six real markets for the same real day
and got three distinct images (en-US/de-DE/fr-FR shared one, en-GB had a
different one, ja-JP/zh-CN shared a third). Matches what was actually asked
for -- "wallpaper of the day... from other countries."

Replaced the fixed URL with `wallpaper_url()`, called with a random recent
index (0-3, stays fresh rather than reaching deep into Bing's archive) and a
random market from a list of ~20 real ones. Re-rolled on every retry
attempt too, not just once per run, so a validation failure doesn't waste
three attempts hammering the same bad combination.

Verified live with three real consecutive runs (not just reasoning about the
code): got index=3/mkt=ja-JP, index=2/mkt=ja-JP, and index=2/mkt=it-IT --
three different combinations producing three different md5sums between
them, versus the old behavior's one fixed hash that would've stayed
identical all day regardless of how many times it was clicked. Filenames
now include the chosen index+market too, so multiple fetches in one day
land as distinct archived files instead of colliding on a date-only name.

## 2026-08-28 (wallpaper icon padding: fa-image sits off-center in its own cell)

Reported the icon had visibly more space on its left than its right. Measured
rather than guessed, same discipline as the caffeine icon's own asymmetric
padding fix earlier in this repo: at the shared symmetric 12px/12px padding
every module gets by default, the glyph's actual ink sat with a 12px gap on
its left but only 7px on its right (pixel-sampled the pill's background
boundary against the glyph's own ink boundary) -- `fa-image`'s glyph has
more built-in left-side bearing than right in this font, same class of issue
as the caffeine coffee-cup icon, just the opposite direction.

Shifted to `padding-left: 9px` / `padding-right: 15px` (a 3px correction each
way off the 12/12 midpoint, close to the ~2.5px an even split of the
measured 5px imbalance would call for). Verified the shift moved in the
right direction: re-measured after, the ink moved left by exactly 3px,
matching the padding-left reduction precisely -- confirms the mechanism is
working as intended. Couldn't get a fully clean final left-gap-vs-right-gap
verification, though -- this module sits close enough to the docker pill
right next to it (2px margin, deliberately tight) that a background-color
scan picks up both pills as one contiguous region with no way to
automatically tell where one ends and the other begins. Flagged as a real
measurement limitation rather than claiming a precision this method
couldn't actually deliver -- the direction and rough magnitude are verified,
not a pixel-perfect final balance.

## 2026-08-28 (wallpaper icon swap: fa-image instead of md-wallpaper)

`md-wallpaper` didn't look good -- swapped for `fa-image`/`fa-picture-o`
(`f03e`), the classic mountain-and-sun-in-a-frame glyph. Simpler than the
MDI wallpaper icon, and matches the FontAwesome convention most of this
bar's other icons already use (wifi, bluetooth, lock, battery) rather than
introducing yet another icon family for one button. Verified present in the
font first, same discipline as every other icon in this repo.

Verified live: pixel-sampled the pill boundary again at the same position
(x1430-1444) -- still a clean dark pill bounded by real wallpaper colors on
both sides, Rosewater renders correctly, higher pixel count than the old
icon (59 vs 24), consistent with a simpler, bolder glyph.

## 2026-08-28 (wallpaper refresh icon in waybar, left of docker)

New `custom/wallpaper` module, placed right before `custom/docker` in
`modules-right` as asked. Reuses the existing `fetch_wallpaper.sh` pipeline
directly rather than writing a new one -- it already had everything needed
(download, retry, real image validation, safe fallback, `flock` so a manual
click can't race the daily timer), just needed a trigger and some feedback.

Added `notify-send` calls at the points that matter -- start ("Fetching a
new one..."), success (using the new wallpaper itself as the notification
icon via `-i`), fallback used, and total failure -- since the script used to
be silent, log-file only. Fine for an unattended daily timer, not fine for a
manual click that gives zero feedback for the several seconds a real
download takes. Benefits the daily timer too, not just this new button.

Icon is `md-wallpaper` (`f0e09`), a genuine dedicated "wallpaper" glyph,
colored Rosewater -- the one hue in this palette that was still completely
unused anywhere in the bar, fitting for a personalization action rather than
reusing a status color that already means something else. No `exec`/
`interval` on the module at all -- confirmed via `man waybar-custom` that
`exec` isn't mandatory, a static `format` + `on-click` is a valid custom
module on its own, since there's no changing state to poll for a plain
action button.

Caught the same recurring codepoint-corruption issue immediately (`"format":
""` landed empty from a raw pasted glyph) and forgot the module wasn't in
any of the shared pill-styling CSS selector lists at first, which left it
rendering as bare unstyled text -- added `#custom-wallpaper` to the
background/border list, the padding-override list, and the hover-accent
list, matching every other module.

Verified thoroughly: pixel-sampled the pill's actual background boundary
(clean dark tone x1430-1444, real wallpaper colors immediately outside on
both sides -- not just eyeballing a noisy full-height ASCII render, which
initially looked ambiguous), and ran the on-click script exactly as waybar
would invoke it (`sh -c`) -- real download succeeded, wallpaper genuinely
changed live on the machine, log confirms the full pipeline ran clean.

## 2026-08-28 (active workspace matches the focused window border: both Red)

Asked to make the workspace indicator match the focused window border's
color, changing the workspace side. `#workspaces button.focused` switched
from Sapphire to Red, matching `client.focused` in `sway/config` -- both
"this is the active one" signals now use the same hue instead of two
different "active" colors in different parts of the setup. Mauve stays
untouched as the bar's one hover/interactive accent elsewhere.

Verified live: switched to workspace 1, pixel-searched the workspace
region -- Red present at exactly the number-glyph and underline positions
(y13-33), Sapphire completely gone from that area.

## 2026-08-28 (backlight icons: real empty-to-full pie fill, not MDI's sun-ray set)

User reported the dimmest icon (1% brightness) looked like a full circle --
checked this for real rather than assuming the percentage-tiering math was
wrong (it wasn't): set brightness to a genuine 1% via `brightnessctl`,
screenshotted, and rendered the actual icon as an ASCII brightness map. It
really was a solid, densely-filled disk with zero rays or partial elements --
confirmed the root cause is the icon choice itself, not a tiering bug.
`md-brightness_1` (the MDI "sun ray count" icon this repo picked earlier) is
apparently just a plain solid dot in MDI's own design language (the "base," no
rays yet) -- reads as "complete/full" to anyone who doesn't already know that
convention, the opposite of what a status icon should communicate.

Switched to `md-circle_slice_1` through `_8` (picked 1/3/5/7/8 for a 5-tier
spread) -- a genuine pie-chart fill progression, same visual language as
battery/volume/wifi's own "empty container gradually fills up" icons already
used elsewhere in this bar, instead of a ray-count metaphor that doesn't read
the same way.

Verified live, not just by eye: rendered the actual icon as a detailed ASCII
brightness map at real 1% (mostly hollow ring, one small filled wedge visible,
pixel count dropped from 104 to 10 compared to the old icon at the same
brightness) and real 90% (densely filled disk, just a thin unfilled outline
remaining) -- a genuine, intuitive empty-to-full contrast between the two,
confirmed from the actual rendered pixels rather than assumed from the icon
names.

## 2026-08-28 (focused window border: Red, the actually-dominant pick)

Clock time/date (Blue/Maroon) landed well; the border's Mauve didn't --
asked for something more "dominant." Red is the single boldest, most
commanding hue in this palette. Named the real trade-off before shipping it
rather than after: Red is reserved everywhere else in this setup for actual
alerts (network disconnected, battery critical, the power button), and this
is the fourth different border color tried in a row (Mauve -> Sapphire ->
Lavender -> Mauve -> Red) -- worth being explicit that a persistent "this
window is focused" fixture reads differently from a transient alert pill,
rather than silently hoping that distinction holds.

Verified live against the same real window as every prior border-color
entry: Red renders at 1245 pixels along the top border (consistent with the
1244 every previous color measured at), Mauve completely gone from that
position.

## 2026-08-28 (royal color trio: window border, clock time, clock date)

Asked for "royal colors" specifically across the window border, clock time,
and clock date, and to stop iterating on Lavender for the border. Went with
an actual regal color story instead of three unrelated picks:

- **Window border** -> Mauve. This repo's own earlier comments already
  nicknamed it "Royal Mauve" -- it's the literal royal purple of this
  palette. Overrode the earlier concern about it double-booking waybar's
  universal hover accent -- that reasoning was about avoiding meaning
  overload, not about beauty, and beauty is what was asked for this time.
  The two contexts (a persistent window border vs a brief waybar hover
  flash) don't actually read as confusable in practice.
- **Clock time** -> Blue, not Sapphire. Sapphire was already tried once on
  the *date* in an earlier pass and rejected specifically for reading too
  close to Sky (network.wifi) despite not sitting adjacent to it -- reusing
  it here would've repeated a mistake this repo already learned from. Blue
  is a properly saturated, distinct "royal blue" without that problem.
- **Clock date** -> Maroon. Burgundy/wine, historically a royal-robe color,
  already used elsewhere in this bar (pulseaudio, bluetooth.on) without
  issue since neither sits near the center clock.

Verified live: pulled the real focused window's rect again (same window,
same x17/y58 as the last two border-color entries), confirmed Mauve renders
at exactly the same 1244 pixel positions Lavender and Sapphire occupied
before it. Confirmed Blue and Maroon both land at the clock's established
x-positions (time ~x830+, date ~x928+, matching every prior clock-color
verification in this file).

## 2026-08-28 (focused window border: Lavender, take two on "beautiful")

Asked to just pick something beautiful for the focused window border, rather
than continuing to iterate on Sapphire. Considered Mauve first -- it's
Catppuccin's own flagship accent and the most common community choice for
exactly this -- but it already has a specific job as waybar's one universal
hover/interactive signal, and doubling it here would blur that meaning even
though window borders and waybar hovers are physically separate contexts.
Landed on Lavender: barely used anywhere else (just the clock's time text and
one workspace hover state), genuinely one of the more elegant hues in this
palette, and free to mean one clean thing here -- this is the active window.
Sapphire stays workspace-only in waybar, untouched.

Verified live against the same real open window as the previous entry (same
rect, x17/y58/1886x1005): Lavender now renders at the exact same 1244 pixel
positions Sapphire occupied at the top border, and Sapphire itself is
completely gone from that location (0 matching pixels) -- confirms a clean
swap, not a partial/leftover state.

## 2026-08-28 (focused window border: Sapphire, tighter gaps)

Real sway window borders this time (`client.focused` in `sway/config`), not
waybar -- distinct from the workspace indicator's own earlier Mauve ->
Sapphire change. Same reasoning applied here too: Mauve stays waybar's one
universal hover/interactive accent, so the focused window (same "this is
where you are right now" meaning as the focused workspace) gets its own
color instead of sharing Mauve for both. `client.focused`'s border,
indicator, and child_border all switched to Sapphire (`#74C7EC`);
background/text left alone.

"Margin" read as gaps -- the config's own existing comments already use
"Margins / Gaps" interchangeably (`### Window Geometry (Margins / Gaps)`,
and a later comment about outer gaps: "there's always a visible margin to
the screen edge"), so that's the established vocabulary in this repo, not
a guess. Reduced both `gaps inner` (8 -> 4) and `gaps outer` (9 -> 4).

Verified live against a real open window, not just a clean reload: pulled
its actual rect via `swaymsg -t get_tree` (x17,y58, 1886x1005), screenshotted,
and pixel-searched right at those exact boundary coordinates -- found Sapphire
solidly along both the top edge (1244 matching pixels at y58) and the left
edge (400 matching pixels at x17), confirming the real border color, not just
that the config parsed.

## 2026-08-28 (battery: real charging icon with the lightning bolt built in)

Follow-up: wanted the charging icon to actually show a bolt again, from "the
same family" as the plain battery icon, not just rely on color. Previous entry
concluded this wasn't possible because `format-icons` looked like a single flat
array shared by every format variant -- wrong, caught by reading waybar's
actual source (`ALabel::getIcon`, `src/ALabel.cpp`) rather than trusting the
man page summary alone this time: `format-icons` can be an **object**, and the
battery module builds a lookup-key list `{status+"-"+state, status, state}`
(confirmed `status` gets lowercased with spaces turned into dashes before this,
matching the `#battery.charging` CSS class already in use) -- falling back to
a `"default"` key. Critically, each value in that object can *itself* be an
array, independently capacity-tiered exactly like the flat form. So
`{"charging": [...5 icons...], "default": [...5 icons...]}` genuinely works:
whichever status is active picks its own tiered set.

Used a real "battery with a bolt inside" icon family (`md-battery_charging_10`
through `_100`, verified present in the font) for the `"charging"` key, and
switched `"default"` to the matching plain `md-battery_*` set instead of the
old FontAwesome one, so charging/non-charging read as the same visual family
with just the bolt as the distinguishing detail, not two unrelated icon styles
stitched together.

Hit the raw-glyph corruption bug again, but in a new form -- `\U000fXXXX`
8-digit escapes (needed for these supplementary-plane codepoints, all above
`U+FFFF`) got silently truncated in transport this time: `\U000f089c` landed
as `\uf089` (4 digits) plus a stray literal `c` character, valid JSON but
wrong content, caught only by checking codepoints after writing -- the same
discipline that already caught the plain raw-character version of this bug
several times earlier in this session. Confirmed via an isolated `python3 -c`
call that the escape syntax itself is correct in isolation; something in this
specific heredoc's transport mangled it. Fixed by sidestepping escape-literal
parsing entirely -- built the strings with `chr(0xf089c)` etc. instead, which
can't be misinterpreted the way a backslash sequence can.

Verified live: valid JSON, clean waybar reload with no errors (confirms the
object-keyed `format-icons` syntax parsed correctly), and the battery pill
still renders Green at the real current capacity (90%, discharging) with a
comparable icon pixel count to prior checks -- consistent with a real glyph
rendering, not a blank/missing one. Could not force an actual charging session
to visually confirm the bolt icon itself renders -- same real limitation as
the previous entry, still resting on the mechanism being correctly wired
rather than a live A/B screenshot of it charging.

## 2026-08-28 (battery: real percentage gradient, icon now tiers while charging too)

Checked the actual live state first rather than guessing: real capacity 93-94%,
genuinely `Discharging`. Confirmed via pixel search it *was* already rendering
correctly (Green, the healthy-discharging color from an earlier pass) -- so the
color mechanism itself wasn't broken, but two real gaps explain what looked like
"not changing": color only had two emergency breakpoints (warning at 30%,
critical at 15%) with everything from 31% to 100% rendering the exact same flat
Green, and the icon was completely static (`format-charging`/`format-plugged`
had a hardcoded bolt glyph, no `{icon}`) whenever actually plugged in --
capacity-tiering only ever worked while discharging.

**Color**: `states` turns out to accept arbitrary names, not just
warning/critical (`man waybar-states`: "Every entry consists of a `name` and
a `value`"). Added a third tier, `"moderate": 60` -> Yellow, between the
existing warning (Peach) and critical (Red), positioned in the stylesheet
between `.full` and `.warning` so a genuinely low battery still overrides it via
the same source-order logic already used for the other states. Now: >60% Green,
31-60% Yellow, 16-30% Peach, <=15% Red -- an actual gradient instead of two
thresholds plus one flat color for the other 70 points of range.

**Icon while charging**: `format-icons` turns out to be a single array shared
by every format variant (confirmed: no per-status icon set exists in the
battery module's schema) -- so a dedicated MDI `battery_charging_10..100` tiered
set (found and verified present in the font, but not usable here since waybar
can't switch icon arrays by status) wasn't the fix. Real fix:
`format-charging`/`format-plugged` now use `{icon}` too, pulling from the same
tiered array `format` already used -- same "icon shape = one concept (capacity),
color = another (status)" split already used elsewhere in this bar (e.g. the
volume mute icon). Trade-off: lost the static bolt glyph's obvious "this is
charging" shape, but color already carries that signal clearly (Yellow while
charging, Teal when full) -- flagged in case that trade isn't wanted back.

Verified live: reloaded clean, pixel-confirmed battery still renders Green at
the real 93% capacity (correctly *not* falsely triggering the new 60% Yellow
tier). Couldn't verify the moderate/warning/critical Yellow/Peach/Red bands or
the charging icon's tiering with real live A/B tests -- would need the actual
battery to drain into those ranges or to actually be plugged in, neither of
which could be forced from here -- this rests on the states mechanism already
being independently proven correct in an earlier pass, not a fresh live test
of every band.

## 2026-08-28 (whole bar reorganized: status indicators left, controls right)

Full layout reorder, requested as a coherent principle rather than a one-off
tweak: status/indicator modules (workspace, bluetooth, wifi, network speed)
read left to right on the left side, clock stays centered, and everything you
actually click or toggle (lock states, docker, caffeine, brightness, volume,
battery, power) lives on the right, in that order. Caps/num lock explicitly
placed right before docker per the request.

```
Left:   [workspaces] · [bluetooth][network][network#speed]
Center: [time][date]
Right:  [caps/num lock][docker][caffeine] · [backlight][pulseaudio] · [battery] · [power]
```

Just reordering `modules-left`/`modules-right` wasn't enough on its own --
several margin/grouping CSS rules were written assuming the *old* adjacencies
(docker used to mark "start of the left status group", bluetooth used to mark
its end). Re-derived the grouping margins for the new clusters: bluetooth now
starts the left connectivity cluster (was docker's old role), caffeine now
ends the new device-controls cluster on the right (docker+caffeine+lock
states tight together, gap before brightness/volume) instead of bluetooth
ending a group that no longer exists in that position.

Verified live rather than trusting the reorder on paper: screenshotted the
reloaded bar and pixel-searched for six different modules' known colors
across the full bar width. Every ordering signpost landed where it should --
workspace (Sapphire) at the far left (x12), wifi (Sky) starting only after a
gap consistent with bluetooth preceding it (x242+), time/date centered
(x830-1078), docker (Blue) now clearly in the right portion (x1480-1492), and
the power button (Red) as the absolute rightmost element, right at the
screen edge (x1894-1904).

## 2026-08-28 (capslock/numlock: hidden entirely when off, not just dimmed)

Wanted them to disappear completely (zero bar space) when off, each
independently -- only one showing if only one is locked. Found the exact
mechanism in `man waybar-custom`: `hide-empty-text` ("Disables the module
when output is empty") removes the whole module from the layout, not just
blanks its text. Added it to both `custom/capslock`/`custom/numlock`, and
`keylock-status.sh` now outputs `"text":""` for the normal unlocked state
(previously a dim gray icon+badge). A genuine error case (no LED device
found at all) still shows something rather than silently vanishing --
that's a real problem, not an "off" state.

This broke the "one merged pill" look from two entries ago -- that treatment
(capslock rounded-left-only, numlock rounded-right-only, touching with no
seam) assumed both are always present. With either now able to disappear on
its own, a half-rounded pill with its open edge flat would look visibly cut
off whenever only one shows -- the common case now, not an edge case.
Reverted to two independent full pills rather than attempting fragile
sibling-aware CSS to conditionally re-merge them only when both happen to be
visible, which wasn't practical to verify reliably. Correctness over keeping
a cosmetic that no longer fits the new behavior.

Hit the same raw-glyph-paste corruption bug again while editing
`keylock-status.sh` -- `ICON=$''` landed as a genuinely empty string,
caught by checking `hex(ord(ch))` codepoints immediately after writing
rather than assuming the paste worked (established discipline in this repo,
paid off again). Fixed using bash's own `$'\uXXXX'` ANSI-C-quote escape
syntax instead -- plain ASCII text in the file, bash itself decodes it to
the real character at runtime, so there's nothing for the paste to corrupt.
Verified directly: `bash -c "echo -n \$'\uf023'"` piped through Python
confirmed the exact right UTF-8 bytes.

Verified live: pixel-sampled the row from workspaces through where
capslock/numlock used to sit -- one continuous dark pill-background tone
the whole way, transitioning directly into docker's own small intended gap,
instead of the ~150px both indicators used to occupy together.

## 2026-08-28 (network speed fixed width; capslock recolored off pale Yellow)

Two separate asks. First: battery was checked and turned out fine -- at the
time (38%, genuinely `Discharging` per `/sys/class/power_supply/BAT1/status`,
not charging), neither the warning (30%) nor charging color applied because
neither condition was true; it should render Green (the healthy-discharging
state added earlier), not nothing.

**Network speed**: `{bandwidthDownBytes}`/`{bandwidthUpBytes}` change digit
count constantly (12KB vs 1.2MB vs 999B), which was making the whole pill
visibly grow and shrink every couple seconds. Measured the actual live
rendered width first (177px) rather than guessing, then set `min-width:
200px` on `#network.speed`/`#network-speed` for real headroom. Verified live:
pixel-sampled the pill's background boundary after reload, found it now
spans ~204px, matching the new fixed width instead of the old content-only
177px.

**Capslock color**: was Yellow (`#F9E2AF`), read as washed-out/whitish --
Catppuccin Mocha's whole palette is pastel by design and Yellow specifically
is one of its palest members, and the glow's blur softened it further.
Switched to Peach (`#FAB387`) -- meaningfully more saturated (warm orange,
not pale cream) while keeping the same "warm heads-up, not alarming" feeling
Yellow was going for. Num Lock's Teal is unchanged (not pale in the same way,
no complaint raised about it).

## 2026-08-28 (capslock/numlock: merged into one pill instead of two)

Asked to put both in a single group rather than two separate pills sitting
side by side. Kept them as two independently clickable custom modules
underneath (merging into one module would lose per-key on-click, the thing
just added) but made them visually read as one: capslock is the left half
(rounded left corners only, no right border), numlock is the right half
(mirror image), touching with no seam. Needed the same negative-margin trick
already used for the clock/time pair -- config's top-level `"spacing": 5`
puts 5px between every pair of sibling modules regardless of their own
margins, so `margin-left: 0` alone would've still left a visible gap.

Verified properly this time rather than trusting a single noisy scan: the
wallpaper bleeding through gaps between pills made a broad region search
unreliable (same class of issue hit before), so sampled raw pixel values
along a row instead. From capslock's start to numlock's end, every sampled
pixel stayed in a tight dark range (17-30 per channel) with no jump to
wallpaper brightness anywhere -- confirmed continuous. Then sampled the same
way from numlock into docker as a positive control, specifically to prove
the method would actually catch a real gap: found exactly that, colors
jumping to (183,167,131)-range wallpaper tones in the real gap before
docker. Confirms the capslock/numlock merge is genuinely seamless, not just
an assumption that the CSS technique worked.

## 2026-08-28 (capslock/numlock: click to toggle, hover tooltip, real cursor)

Wanted mouse click-to-toggle, a hover tooltip saying which lock it is, and a
pointer cursor on hover. None of that is possible with waybar's built-in
`keyboard-state` module -- checked `man waybar-keyboard-state` first rather
than fighting CSS against it: no `on-click`, no `tooltip`, nowhere in its
config schema at all. Replaced it with `custom/capslock`/`custom/numlock`,
backed by two new scripts (same `{text,class,tooltip}` JSON pattern already
used for `custom/caffeine`/`custom/docker`), which support all three natively.

`keylock-status.sh` reads `/sys/class/leds/*::capslock|numlock/brightness`
directly -- the real kernel LED state, confirmed correct against actual live
state (numlock genuinely on, capslock genuinely off) at the time.

`keylock-toggle.sh` needed real investigation, not just wiring an `on-click`.
`wtype -k Caps_Lock` -- already used elsewhere in this repo -- does not
actually toggle the real lock state here (confirmed: the LED file stayed `0`
straight through it), because it injects through the `virtual-keyboard-
unstable-v1` Wayland protocol, which doesn't drive the same XKB lock-latch
machinery a real key event does on this compositor. Switched to `ydotool`
instead (official `extra` repo, added to `packages/pacman.txt`) -- injects
through `/dev/uinput`, indistinguishable from real hardware to the same
input pipeline, so it actually works. Checked the Arch package's file
listing before trusting it: ships its own systemd **user** service (no root
needed at runtime) and its own udev rule for `/dev/uinput` permissions --
clean, standard, not a loose workaround.

**Not yet installed** -- needs `sudo pacman -S ydotool`, a udev reload, and
`systemctl --user enable --now ydotool.service` (all three commands in
`docs/ARCHITECTURE.md`). Until then, clicking either indicator fails with a
clear `notify-send` telling you exactly which of those steps is missing,
rather than a silent no-op or a cryptic `ydotool` error -- verified this
fallback path directly.

Cursor needed no extra work at all: waybar shows a pointer automatically for
any module with `on-click`, standard GTK behavior, same as every other
already-clickable pill in this bar. Unrelated to the wofi popups' own cursor
limitation documented elsewhere -- different code path entirely.

## 2026-08-28 (capslock/numlock: fixed two real problems from the last pass)

1. **Couldn't tell which lock was which.** Sharing one padlock shape between
   caps/num (previous entry) meant color alone had to carry "which key is
   this" -- fine once memorized, not self-evident. Added a plain letter badge
   in the config's per-key `format` string alongside `{icon}`: `"A {icon}"`
   for capslock, `"# {icon}"` for numlock. Icon shape/color (padlock,
   Yellow/Teal) unchanged, just no longer the only signal.
2. **Activating a lock grew the whole bar's height.** Real regression from
   the previous pass's `font-size: 19px` bump on the locked state -- waybar's
   configured `"height": 41` didn't hard-clip the over-tall label, so the bar
   visibly grew the moment a lock activated and shrank back when it didn't.
   Removed the font-size change entirely; the `text-shadow` glow stays (it's
   paint-only, doesn't participate in layout/box-height calculation at all,
   confirmed via CSS fundamentals -- this is why it was never the actual
   cause), so the "damn noticeable" glow treatment survives without the size
   change that broke the bar.

Confirmed via `swaymsg` reload the bar reports back its configured height
(`Bar configured (width: 1920, height: 41)`) and `font-size` no longer
appears anywhere in the capslock/numlock CSS rules. Could not force a real
capslock/numlock toggle to visually confirm the height stays fixed while
actually locked (the same `wtype` limitation hit earlier -- synthetic
Caps_Lock presses don't flip the real LED/modifier state in this
environment) -- this rests on the CSS box-model reasoning (text-shadow
cannot affect height, font-size was the only property that could and is now
gone) rather than a live A/B screenshot.

## 2026-08-28 (capslock/numlock, take three -- real padlock, deliberately loud)

Neither prior attempt was noticeable enough. Switched to a real closed-padlock
icon (`fa-lock`, `f023`) for locked, open padlock (`fa-unlock`, `f09c`) for
unlocked -- back to waybar's shared `format-icons` pool (same icon set for
every key, per `man waybar-keyboard-state`) rather than a per-key hardcoded
glyph, since color (Yellow/Teal, unchanged) already tells capslock and numlock
apart and a genuine padlock shape reads faster than an arrow or a hashtag ever
would.

Made the locked state deliberately louder than the rest of the bar's own
restraint calls for: `font-size: 19px` (up from the bar's normal 15px) plus a
two-layer `text-shadow` glow (tight 8px + wide 14px halo, matching each key's
own color). A locked modifier key is more urgent than a passive status icon,
worth breaking the "everything the same size, no glow" convention for. Still
no filled background block, per the earlier explicit ask -- the glow carries
the emphasis instead of a solid fill.

## 2026-08-28 (capslock/numlock icons, take two -- simpler glyphs)

First attempt (`md-caps_lock`/`md-numeric`) didn't land well visually. Swapped
for simpler, more minimal glyphs instead of another detailed Material Design
icon: capslock is now U+21EA (⇪, "UPWARDS WHITE ARROW FROM BAR") -- the actual
ISO keycap symbol printed on real physical Caps Lock keys, standard Unicode
rather than a Nerd Font PUA glyph, so no font-coverage risk at all. Numlock is
`fa-hashtag` (`f292`, a plain `#`) instead of a cluttered "123" icon at bar
size -- clean, single-glyph, immediately reads as "numbers" without the visual
noise a multi-digit icon has this small.

## 2026-08-28 (capslock/numlock: icons instead of "CAPS"/"NUM" text)

Was `"format": "{name} {icon}"` with a shared locked/unlocked icon pair
(`format-icons`) -- per `man waybar-keyboard-state`, that icon pool is the same
set for every key ("the same set of icons is used for number, caps, and scroll
lock"), so simply dropping `{name}` would've left capslock and numlock showing
the *identical* generic lock glyph, impossible to tell apart without the text.

Real fix needed distinct icons per key, not just fewer characters. `format`
turns out to also accept a per-key object (confirmed in the same man page:
`{"numlock": ..., "capslock": ..., "scrolllock": ...}`), so each key now gets
its own hardcoded, purpose-specific icon instead of routing through the shared
locked/unlocked pool at all: `md-caps_lock` (`f0a9b`) for capslock,
`md-numeric` (`f03a0`) for numlock -- both verified present in the installed
font via `fc-query` first. Lock state is still conveyed by color exactly as
before (Yellow/Teal when locked, dim gray when unlocked -- that CSS was
untouched and already independently verified working in an earlier pass), just
no longer duplicated in a text label too.

## 2026-08-28 (active workspace: Sapphire instead of Mauve)

Asked for a different color on the active workspace than Mauve, suggesting
Sapphire or wifi's color. Went with Sapphire: Mauve stays the bar's one
universal "you're pointing at something interactive" hover accent everywhere
else, so giving the workspace's own resting focused state a different hue
keeps those two meanings distinct rather than overloading Mauve for both.
Also ties it into the blue "connectivity" family already established for the
network module (Sapphire = ethernet, Sky = wifi) instead of an arbitrary new
hue. Text color and underline both switched together.

Verified live: pixel-searched the workspace area after switching to
workspace 1, found Sapphire at the number glyph (y13-14/23-24) and the
underline (y32-33), zero Mauve remaining there.

## 2026-08-28 (workspace numbers: one shared container, not N separate buttons)

`#workspaces` (the group wrapper) already had the shared pill treatment every
other module gets -- dark background, Mauve hairline border -- but each number
button *also* had its own smaller background-color and border-radius layered
on top, which read as "several small buttons sitting inside a pill" instead of
one unified group. Removed the per-button background/radius entirely; numbers
now sit directly in the one shared container. Colors, spacing, and the
hover/focused underline accent from the previous change are all untouched --
this was specifically about the idle-state look, not a redesign of the states
themselves.

Verified live: pixel-scanned the workspace area's background after reload,
found one consistent dark tone throughout (no lighter per-button patches
standing out), while the Mauve underline (y32-33) and number glyph (y13-24)
from the previous change both still render correctly.

## 2026-08-28 (workspace switcher: fixed a real toggle bug, added an underline accent)

**Bug**: pressing `$mod+1` while already on workspace 1 jumped back to whatever
workspace you'd been on before -- an alt-tab-style toggle, not "go to/stay on
workspace 1." Root cause: `workspace_auto_back_and_forth yes`, added earlier this
session as a deliberate feature ("like alt-tab for workspaces"). Reverted --
removed the line entirely rather than setting it to `no` explicitly, since `no`
is sway's own documented default (`man 5 sway`: "Default is no"). Verified with
the exact reported reproduction: switched to workspace 1, then repeated the same
switch command -- workspace 1 stayed focused both times (previously the second
call would have jumped to workspace 2).

**Look**: added a 2px underline accent to hover/focused workspace buttons --
translucent Lavender on hover, solid Mauve when focused, same colors already in
use, just a second visual cue (like an active browser/editor tab) on top of the
existing bold-colored-number treatment. Widened button padding one notch (7px ->
8px) so the underline doesn't read as cramped. A transparent `border-bottom`
placeholder on the idle state reserves the same 2px vertical space always, so
the chip doesn't visibly shift height the moment an underline actually appears.
Verified live: pixel-searched after switching to workspace 1, found a solid
~40px-wide horizontal Mauve line at the chip's bottom edge (y32-33), distinct
from the small number-glyph pixels above it (y13-24) -- confirms a real
underline, not just a coincidental color match.

## 2026-08-28 (caffeine mode now actually survives a reboot)

Caffeine mode silently reset to off on every reboot regardless of what it was
left at. Root cause: `swayidle.service` is `enabled` (`WantedBy=default.target`,
confirmed via `systemctl --user is-enabled`), so systemd's user manager
auto-starts it at every login *on its own* -- completely independent of sway.
The old `exec systemctl --user restart swayidle.service` line in `sway/config`
had no way to know caffeine had been left on, so it just reasserted "start"
every time.

Fixed with a persisted marker file, `~/.local/state/caffeine/enabled`.
`caffeine-toggle.sh` now writes/removes it alongside stopping/starting the
service. New `scripts/.local/bin/swayidle-startup.sh` -- what sway's `exec`
line calls now instead of the bare `systemctl restart` -- reads the marker at
startup and is the single source of truth for swayidle's state: stops the
service if caffeine was left on (overriding whatever systemd's default.target
just auto-started), otherwise does the same restart this line always did.

Verified the actual failure mode end to end rather than trusting the fix on
paper: toggled caffeine on, manually replayed what systemd's auto-start would
do at the next login (`systemctl --user start swayidle.service`), confirmed
the service came back active exactly as it incorrectly would pre-fix, then ran
the new startup script the way sway's `exec` line would and confirmed it
correctly stopped it again. Verified the off case and `caffeine-status.sh`'s
reporting through a full toggle sequence too. No literal reboot was performed
to avoid disrupting the live session -- this rests on an exact functional
simulation of the real startup sequence.

## 2026-08-28 (workspace/capslock/numlock: text color instead of a filled block)

Active workspace and locked capslock/numlock indicators used a solid
background-color fill + dark text for contrast. Asked to keep the background
neutral and just recolor the text/number instead. Same hues kept throughout
(Mauve for the active workspace, Yellow for capslock, Teal for numlock) --
just moved from `background-color` fill to `color` text, with `font-weight:
800` added to each so the now-unfilled state still reads as emphasized rather
than losing prominence entirely.

Verified the workspace change live: pixel-searched for Mauve in the
workspace region after reload, found a small ~10-pixel cluster sized like a
single bold glyph (the old filled-block version would have produced hundreds
of hits across a whole chip) -- confirms text-only rendering, not a background
block. Tried to verify capslock the same way but `wtype -k Caps_Lock`'s
synthetic key press doesn't actually toggle the real lock LED state
(`/sys/class/leds/*capslock*/brightness` stayed at 0 through it) -- a testing-tool
limitation, not something to chase further, since capslock/numlock use the
exact same CSS mechanism (state selector + `color` instead of
`background-color`) already confirmed working for the workspace case.

## 2026-08-28 (icons that never actually changed state: volume mute, brightness, wifi signal)

Volume's mute icon and its low-volume tier icon were the literal same codepoint
(`f026`, FontAwesome's `volume_off`/`volume_x`/`volume_xmark` -- confirmed via
nerd-fonts' own glyphnames.json that all three names alias to one codepoint), so
muting while already at low volume showed no visible change at all, and even at
higher volume the "off" icon read ambiguously close to the low-tier one. Backlight
had a single static sun icon the whole time -- no tiering existed at all. The
main waybar network pill's wifi icon was likewise a single static glyph, never
reflecting signal strength (only the wifi *picker* dropdown had tiered icons,
added earlier -- the always-visible bar pill never did).

Switched volume to a full, consistent Material Design Icons set instead of
patching around FontAwesome's ambiguity: `volume_low`/`volume_medium`/`volume_high`
for the tiers, `volume_mute` (a genuinely different codepoint, `f075f`) for muted.
Backlight gained a real 5-tier `format-icons` (`brightness_1`..`brightness_5`,
`f00da`-`f00de`). Network's `format-wifi` now uses `{icon}` against the same
5-tier wifi-strength set (`wifi_strength_outline`/`_1`/`_2`/`_3`/`_4`) already
verified for the wifi picker, so the bar pill and the picker's icons finally
match instead of the bar staying static.

Caught a real hallucination while researching this: an earlier WebFetch summary
of nerd-fonts' glyphnames.json invented `fa-volume_mute` at `f131` -- sounded
completely plausible, wasn't real. Downloaded the actual JSON directly to the
machine and grepped it myself before trusting anything this time (`curl` +
`python3 -c "import json..."` against the real 545KB file) -- that's also just a
more reliable method going forward than relying on a small model's summary of a
huge file, independent of this specific miss. Every codepoint used here was
independently confirmed present in the installed font via `fc-query` afterward,
same discipline as everywhere else in this repo.

Verified all three live, not just "JSON parses": muted vs unmuted at the same 65%
volume now render two clearly different glyph shapes (screenshotted, rendered as
ASCII brightness maps to compare, confirmed genuinely different silhouettes, not
just eyeballed); brightness at 10% vs 90% likewise render distinguishably
different icons (fewer vs more visible sun-rays). Wifi's tiered icon couldn't be
forced to a specific signal strength for a live A/B test the same way (real
hardware, real signal), so that one rests on the codepoint verification plus a
clean waybar reload with no errors, not a live visual diff.

Battery was checked too and turned out already correct -- its `format-icons`
(`battery_empty` through `battery_full`, 5 genuinely distinct FontAwesome
codepoints) never had this bug, confirmed by inspecting the config before
assuming it needed the same fix.

## 2026-08-28 (cursor theme was never actually configured anywhere; wofi hover-cursor investigated)

User reported the cursor doesn't turn into a pointer hovering over entries in the
WiFi/Bluetooth pickers. Checked `man wofi`/`man wofi-style` (well, the actual
`wofi.5`/`wofi.7`/`wofi.1` man pages -- there's no separate wofi-style one) for any
"cursor" mention at all: zero hits anywhere in wofi's own documentation. This
matches an already-documented finding from this repo's own history (the power-menu
build): "no CSS cursor support" in wofi's `--dmenu` mode.

Before accepting that at face value again, checked something adjacent that turned
out to be a real, separate, worthwhile gap: **no cursor theme was configured
anywhere on this system at all** -- not in any env var (`XCURSOR_THEME` was
entirely absent, only `XCURSOR_SIZE=24` existed from some other default),
not in `sway/config` (no `seat ... xcursor_theme` line existed), not in
`gtk-3.0/settings.ini` or `gtk-4.0/settings.ini` (`gtk-cursor-theme-name` was
never set). `/usr/share/icons/default` already resolves to Adwaita
(confirmed: `Inherits=Adwaita` in its `index.theme`), so a sane default cursor
theme was always *available*, just never explicitly told to anything. Fixed
with `seat seat0 xcursor_theme Adwaita 24` in `sway/config` and
`gtk-cursor-theme-name=Adwaita` / `gtk-cursor-theme-size=24` in both GTK
settings files.

**Tested whether this fixes the actual reported issue, rather than assuming**:
launched wofi fresh after `swaymsg reload` and checked its real environment
(`/proc/pid/environ`) -- still no `XCURSOR_THEME` there, meaning sway's
env-var export for the seat's cursor theme apparently only happens at sway's
own actual startup, not on a soft reload (same class of caveat this repo
already has documented for plain `exec` lines not re-running on reload --
will take full effect after next login, not before). The `gtk-cursor-theme-name`
half should already apply immediately though, since wofi is a real GTK3 app
(confirmed via `ldd`) reading `gtk-3.0/settings.ini` fresh on every launch, no
caching involved.

**The actual "no pointer on hover" complaint is a separate thing from theme
configuration, and isn't fixed by any of this**: a cursor theme controls which
glyph set gets used for whatever shape is requested, not whether a shape change
gets requested in the first place. If wofi's dmenu list rows never ask the
compositor for a "pointer" cursor on hover (which is what "no CSS cursor
support" means), a correctly-configured theme changes nothing about that --
there's no shape-change request to render *from* that theme. Real, structural
wofi limitation, same class as the missing hover-tooltip found earlier -- not
fixable through config here. The honest options: live with it (matches the
rest of this bar's wofi-based UI language), or switch the picker backend to
something with fuller cursor support (e.g. rofi) at the cost of visual
consistency with everything else that already matches wofi's theme.

## 2026-08-28 (Bluetooth gets its own picker; WiFi picker no longer shows it)

Four asks in one go: WiFi's menu shouldn't show Bluetooth actions, keyboard focus
should land in the search box automatically, Bluetooth should get "the same modal
approach" with its own unique options (not WiFi's), and the connected entry should
read as more than just a different text color.

**Keyboard focus**: tested this directly before assuming it needed a fix --
launched the picker with zero clicks, typed `wtype "Maha"` into it, screenshotted
before/after. ~7800 pixels differed in the content region, confirming the typed
text reached wofi's search box and filtered the list immediately. This already
works, nothing to change.

**WiFi menu, Bluetooth-free**: `wifi-picker.py` now monkeypatches
`create_other_actions` too (previously only `get_wofi_highlight_markup` and
`get_selection`) to drop the Bluetooth toggle entry by `Action.func` identity
(`is not nmdm.toggle_bluetooth`) before it ever reaches the menu.

**Bluetooth picker**: new `scripts/.local/bin/bluetooth-picker.py`, same modal
approach as the WiFi one (wofi --dmenu, category colors) but fully self-contained
on `bluetoothctl` rather than wrapping a third-party tool -- checked first, and
the only wofi/dmenu-adjacent Bluetooth picker that exists at all is a 3-year-stale
rofi-specific AUR package, not worth the dependency over ~180 lines. Verified
every `bluetoothctl` subcommand against this machine's real bluez (5.87) before
writing anything against it -- caught that `paired-devices` isn't a valid command
in this version (`devices Paired` is), and confirmed `--timeout n scan on`
works non-interactively. Menu: power toggle, bounded 8s scan (relaunches itself
after, same self-relaunch pattern upstream networkmanager_dmenu uses for its own
rescan), Bluetooth Manager shortcut, paired devices (click connects/disconnects),
and -- added after noticing the "nearby" color was defined but nothing used it,
which would've made "Scan for Devices" a dead button -- devices bluez has seen
but not paired with yet, click to pair+trust+connect in one go. Every
`bluetoothctl` call bounded with a timeout that's now caught centrally in `run()`
(returns an ordinary failed result instead of an uncaught traceback) since
connect/pair/disconnect can all hang waiting on a device that needs interactive
PIN confirmation, which has nowhere to go in a dmenu flow -- documented as a real
limitation (falls back to suggesting Bluetooth Manager) rather than silently
dropped. waybar's `bluetooth` on-click now points here; deleted the now-fully-
superseded `nwg-bar/bluetooth.json`.

**Connected-entry border**: Pango `span` markup has no border attribute at all
(checked: foreground/background/underline/strikethrough/weight/style/size exist,
border does not) -- a literal CSS-style border around the connected entry isn't
achievable through this rendering path. Closest honest approximation, applied to
both pickers: a "┃ " heavy-vertical-line prefix inside the same highlighted span,
same idea as an active-indicator sidebar tick in a lot of TUI/statusline designs,
layered on top of the existing filled-background highlight rather than replacing
it.

## 2026-08-28 (Wi-Fi picker: color-coded rows -- networks vs saved vs commands)

Networks, saved connections, and commands (Rescan/Enable/Disable/etc.) all
rendered identically in the wofi menu -- upstream `networkmanager-dmenu` only
colors the single active/connected line, everything else is plain default text.
Couldn't fix this via config.ini (no per-category color hook exists there --
checked the tool's actual config schema first, not just assumed), so wrote
`scripts/.local/bin/wifi-picker.py`, a themed wrapper waybar now calls instead of
`networkmanager_dmenu` directly.

Loads the real installed script via `importlib` and monkeypatches exactly two
functions (`get_wofi_highlight_markup`, `get_selection`) rather than forking the
whole ~1500-line file -- all real NetworkManager interaction still runs upstream's
own maintained code. Colors: Sky for an actual network (matches the wifi icon's
own color elsewhere in the bar), Peach for a command, Teal for a saved connection
-- detected via `Action.func` identity plus the `:SAVED` name suffix upstream
already uses internally, both real signals the tool relies on for its own logic,
not incidental strings I'm guessing at.

Hit a real, worth-remembering bug while verifying this: `importlib.util.
spec_from_file_location` returns `None` (not an error) when it can't infer a
loader for a file with no `.py` extension, which `/usr/bin/networkmanager_dmenu`
is -- failed one line later with a confusing `'NoneType' object has no attribute
'loader'`. Fixed with an explicit `SourceFileLoader`.

Second, more confusing bug while testing: a background-launched wofi process
reliably vanished by the time a *separate* tool call checked on it, even under
`setsid`, producing a false "colors aren't rendering" result from a screenshot of
a stale/empty window. Real cause: this remote session's execution environment
doesn't preserve backgrounded processes across separate tool calls the way an
actual terminal session would. Fix for testing this class of thing here: launch,
wait, and screenshot all within one single call -- retested that way and
confirmed Sky/Mauve/Teal all render correctly in the live window via pixel
search, matching what direct instrumentation of the patched functions had
already shown (correct markup, correct wofi command with `-m` for pango markup).

## 2026-08-28 (waybar's network pill: dropped the visible signal percentage too)

Follow-up: the "%" the user didn't want turned out to be on the always-visible
waybar pill itself (`format-wifi`), not the wofi dropdown from the previous
entry -- two different places both showing signal info, only one had been fixed.
`format-wifi` went from `"  {essid}  {signalStrength}%"` back to `"  {essid}"`.
Left `tooltip-format-wifi` untouched -- it already has the full detail (signal%,
dBm, frequency, IP, gateway) and, unlike wofi's dmenu list, waybar's tooltips are
real GTK tooltips that actually work on hover. So the bar now genuinely has the
"just the name, full detail on hover" behavior that wofi's list couldn't deliver.

## 2026-08-28 (Wi-Fi picker UI: icons instead of signal-strength text)

Follow-up on the Wi-Fi picker from earlier today: wanted the list to just show
network names, not signal%/bars text, with strength conveyed by icon instead
(reads faster, takes less horizontal space) -- plus wanted full detail
available on hover.

Did the icon part: `format` went from `{name}  {sec}  {bars}` to
`{icon}  {name}`, and set `wifi_icons` to the 5-tier Material Design
wifi-strength glyphs (`networkmanager-dmenu` already ships a default set of
these in its own example config, just commented out) -- verified each of the
5 codepoints (`U+F092F` through `U+F0928`) is actually present in the
installed font via `fc-query`, same discipline as every other icon in this
repo, rather than trusting the upstream default blindly.

Couldn't do the hover-detail part -- checked wofi's actual capabilities first
rather than assuming: its dmenu list has no per-item tooltip support at all,
nothing to hook into. Said so plainly rather than silently dropping that half
of the request or pretending a workaround exists. The list is icon+name only
now; full detail (exact %, security type) isn't surfaced anywhere in this UI as
a result, which is the real tradeoff of asking for a compact list.

## 2026-08-28 (real Wi-Fi picker instead of the nwg-bar On/Off/Settings popup)

Wanted: click the network icon, see available networks, pick one, get prompted
for the password if it needs one, connect. `nwg-bar`'s wifi.json couldn't do any
of that -- confirmed (again, same root cause as the volume popup fix earlier)
that it's a static button grid with no dynamic content support at all, reading
its Go source. Architecturally impossible there, not a config problem.

Replaced with `networkmanager-dmenu` (official `extra` repo, not AUR) --
scan/connect/password-prompt/on-off-toggle/nm-connection-editor-shortcut all in
one menu, using `wofi --dmenu` as its backend. Read the tool's actual Python
source before trusting it: confirmed real, dedicated wofi support (not just
generic dmenu-protocol compatibility) -- it detects `wofi` specifically and
appends wofi's own `-P`/`--password` flag for the passphrase prompt (masks
input), plus has wofi-specific highlight markup for the connected network.

Given this repo's history of real, confirmed wofi `--dmenu` bugs (the power-menu
work a while back -- no CSS cursor support, `--columns` capped at 2, etc.),
smoke-tested `wofi --dmenu` here first rather than assuming it'd just work:
piped a sample network list into it, screenshotted, and confirmed a normal
solid popup rendered center-screen with no issue. Those earlier bugs turned out
to be specific to forcing a *button-grid* layout through `--dmenu` -- a plain
vertical scrolling list (what this tool actually does) hits none of them.

Config: `networkmanager-dmenu/.config/networkmanager-dmenu/config.ini` (new stow
package), `dmenu_command = wofi`, Mauve highlight to match the rest of the bar.
Waybar's `network` module `on-click` now runs `networkmanager_dmenu` directly
instead of the old `nwg-bar -t .../wifi.json ...` invocation. Deleted
`nwg-bar/.config/nwg-bar/wifi.json` -- fully superseded, nothing else referenced
it.

**Not yet installed on the live machine** -- `networkmanager-dmenu` needs `sudo
pacman -S networkmanager-dmenu`, this session has no `sudo`. Everything here is
verified as far as it can be without the actual binary present (config syntax,
waybar JSON validity, the wofi backend smoke test, reading the tool's real
source for wofi support) but the actual end-to-end click-to-connect flow is
unverified until it's installed and clicked for real.

## 2026-08-28 (color pass, part 5: date color, take three)

Sky (matching network.wifi exactly) was rejected as a literal duplicate. Tried
Sapphire next -- still a cool cyan-blue like Sky, close enough in the same "family"
that it still read as basically the same color at a glance. Landed on Flamingo: a
genuinely different hue (warm coral, not blue at all), so there's no ambiguity with
wifi, and it pairs as a warm/cool contrast against time's Lavender instead of two
blues sitting side by side.

Verified live: pixel-clustered date/wifi/time after reload -- Flamingo/date at
x927-1078, Sky/wifi at x1151-1354 (no overlap in position or color), Lavender/time
at x830-898 immediately to date's left, unchanged.

Also hit the remote session's connection dropping mid-verification on the previous
attempt (Sapphire) -- the CSS change had already landed and waybar had already
reloaded clean before the drop, confirmed by grep once the connection came back,
but the pixel-screenshot step and this commit hadn't happened yet. Nothing was
lost, just delayed to this entry.

## 2026-08-28 (color pass, part 4: clock reorder/recolor, docker count -> white)

Follow-up feedback on part 3: Rosewater on the date "doesn't look good", and asked
for the time to sit to the left of the date instead of the right.

- Swapped `modules-center` to `["clock#time", "clock"]` -- time first, date
  second. The negative margin that pulls the pair visually together (offsetting
  the bar's own 5px inter-module spacing) moved from `clock#time` to `#clock`
  accordingly, since it's the second element now that needs to pull left toward
  the first, not the other way around.
- Date recolored Rosewater -> Sky, matching the wifi module's color and the
  time's existing Lavender rather than the pale pink that wasn't landing well.
- Docker's container count is now white (Catppuccin's Text color, `#CDD6F4` --
  kept consistent with the theme rather than a stark pure `#FFFFFF`) instead of
  the running/idle Green-or-gray split from the previous pass. That state signal
  didn't disappear, it just moved: the `running`/`idle` class still exists and
  still drives the pill's border-color tint, same as before, just no longer
  duplicated in the count's own text color.

Verified live: reloaded, screenshotted, pixel-clustered Sky and Lavender --
Lavender (time) lands first at x830-898, Sky (date) right after at x927-1078,
distinctly separate from the network module's own Sky wifi text further right
(x1124-1327), confirming the reorder and the reuse aren't colliding into one
cluster.

## 2026-08-28 (color pass, part 3: battery charge states, clock split, docker/volume rework)

- **Battery**: only had colors for the two emergency thresholds (warning/critical)
  plus charging -- the normal "healthy, running on battery" state (`Discharging`,
  confirmed via `cat /sys/class/power_supply/BAT1/status`) fell through to plain
  silver. Added `#battery.discharging` (Green) and `#battery.full` (Teal, topped
  off and plugged in) using the `#battery.status` classes waybar derives from the
  kernel's power_supply status file (`waybar-battery(5)`) -- now every real charge
  state has its own color: Green healthy, Yellow charging, Teal full, Peach warning,
  Red critical. Placed before the existing warning/critical/charging rules in the
  stylesheet since they share selector specificity -- source order is what makes
  the low-battery colors win when both a status and a capacity-state class apply
  at once.
- **Pulseaudio**: Pink -> Maroon. Asked for something "dark/dominating" instead of
  a pastel -- Maroon is deep and grounded, distinct from Yellow on backlight right
  next to it, and its other use (bluetooth.on) sits in the opposite group so there's
  no adjacency clash.
- **Clock**: date and time are now two different colors (Rosewater / Lavender).
  First attempt used two `{:...}` placeholders in one format string with inline
  Pango spans -- waybar rejected it outright ("invalid arg-id in format string"),
  confirming the clock module only accepts one datetime placeholder per instance.
  Real fix: split into two module instances, `clock` (date, full pill) and
  `clock#time` (time, plain floating text next to it, no background of its own) --
  same "boxed pill + adjoining plain-colored text" pattern network/network#speed
  already established, not a new one.
- **Docker**: icon is now a constant Blue (was tied to running/idle state before),
  count switches Green/gray depending on whether anything's actually running --
  colored independently via inline Pango spans in `docker-status.sh` rather than
  one flat color for the whole label. The `running`/`idle` class still exists on
  the module, now driving a border-color tint on the pill instead of duplicating
  the count's own color signal.

Caught one real bug while writing this: a code comment mentioning the literal
path `power_supply/*/status` broke waybar's CSS parser outright (`'/*' in comment
block` at style.css:288) -- the `*/` inside that path silently closed the CSS
comment early. Waybar wouldn't even start until this was reworded. Also had to
rebuild `/tmp/pngdecode.py` a second time -- a mid-session connection drop wiped
`/tmp` entirely, same as every other time this has come up.

Verified every color live: reloaded, screenshotted, pixel-clustered all six new
colors against their expected x-position in the bar (clock date/time correctly
split into adjacent clusters at x834-985/x1016-1084, battery's new Green at
x1795-1846 near the power button, docker's Blue icon narrowed to just x343-355
now that the count isn't also blue, pulseaudio's Maroon confirmed distinct from
backlight's Yellow right beside it).

## 2026-08-27 (color pass, part 2: every remaining module gets its own hue)

Finished the "bar is too monochrome" pass -- clock, backlight, pulseaudio, docker,
and bluetooth's idle-but-on state were all still plain silver (`#CDD6F4`), the only
modules left without an identity color after the network pass. Picked with color
psychology in mind rather than arbitrarily:

- `clock` -> Rosewater. Glanced at constantly, so it gets the calmest, warmest hue
  rather than anything that reads as a status/alert.
- `backlight` -> Flamingo. Warm glow tone for light/comfort, deliberately not the
  Yellow already spoken for by capslock/battery-charging so brightness doesn't
  visually compete with those "heads up" moments.
- `pulseaudio` -> Pink. Audio is the most expressive/personal control in the bar,
  so it gets the most vivid hue left in the palette.
- `custom/docker` -> Blue when containers are actually running (matches Docker's
  own brand blue), dim gray when idle -- previously always showed the same static
  color regardless of whether anything was running. Needed a real script change,
  not just CSS: `docker ps -q | wc -l` piped straight into `format` had no way to
  carry a class, so wrote `scripts/.local/bin/docker-status.sh` (same
  `{"text","class","tooltip"}` JSON pattern as `caffeine-status.sh`) and switched
  the module to `"return-type": "json"`.
- `bluetooth.on` -> Maroon. This is the "powered on, nothing connected" state --
  was falling through to plain silver before, same gap as everything else here.
  Distinct from `.disabled` (gray) and `.connected` (green).

Verified every state live, not just visually glanced at: screenshotted and
pixel-searched for each of the six colors (four resting states plus docker's two),
confirming each cluster lands at the module's actual x-position in the bar (clock
dead center at x834-1084, bluetooth in the left group at x469-478, etc.). Docker's
`.running` state needed an actual running container to verify, so spun up
`docker run --rm -d alpine sleep 20` as a self-cleaning test -- confirmed the Blue
cluster appears at x343-376 while it's up, and `docker ps -a` shows nothing left
over once it exits on its own.

## 2026-08-27 (network module: color, signal strength, richer tooltip)

First piece of the wider "the bar is too monotone" color pass, scoped to `network`/
`network#speed` since that's what got asked about. Read `man waybar-network` before
touching anything -- it documents state-based CSS classes (`#network.wifi`,
`#network.ethernet`, `#network.disabled`, `#network.disconnected`, `#network.linked`)
and a full set of format placeholders that weren't being used at all before
(`{signalStrength}`, `{signaldBm}`, `{frequency}`, `{gwaddr}`, `{cidr}`).

- `#network.wifi` -> Sky `#89DCEB`, `#network.ethernet` -> Sapphire `#74C7EC` (same
  blue family since both mean "connected", distinct enough to tell wifi from wired
  at a glance), `#network.disabled` (rfkill-blocked) -> the same dim gray every other
  "off" state in the bar already uses. `#network.disconnected` (red) was already
  there and untouched.
- `format-wifi` now shows signal strength inline (`{essid}  {signalStrength}%`)
  instead of just the SSID.
- Tooltip went from nothing useful to real diagnostics: SSID/signal/dBm/frequency
  for wifi, interface/IP/gateway for ethernet, explicit disabled/disconnected text.
- `network#speed`'s down/up arrows are now two different colors via inline Pango
  markup (`<span color='...'>`, confirmed supported: `man waybar` -> "MODULE FORMAT"
  section) -- green for download, peach for upload -- rather than one flat color for
  both directions.

Verified for real, not just "JSON parses": reloaded waybar live, screenshotted with
`grim`, and pixel-searched the render (had to rewrite `/tmp/pngdecode.py` from
scratch again -- it's `/tmp`, doesn't survive a session/reboot, no PIL/imagemagick
available to install without sudo). Found Sky-colored pixels exactly where the
`network` module sits (x1121-1307), and two separate color clusters in the speed
module's x-range -- green at x1376-1444 (download), peach at x1495-1562 (upload) --
confirming the Pango spans render as two colors, not one blended block. The
`network.ethernet` rule can't be live-verified the same way (this machine's on wifi,
not ethernet, right now) -- taken on the man page's word that the class exists,
same discipline as everywhere else in this repo, just flagged as unverified live.

## 2026-08-27 (scroll was flooding waybar, and briefly drove volume to 1494%)

User reported scroll-to-adjust "wasn't working" on the volume/brightness pills.
`/tmp/waybar.log` had 249 lines of `Connection failure: Connection terminated` and
`Value "" of hint "value" could not be parsed as type "int"` -- real evidence, not a
guess. Root cause, found in `man waybar-pulseaudio`/`man waybar-backlight`: custom
`on-scroll-up`/`on-scroll-down` "replaces the default behaviour", and neither module
had `smooth-scrolling-threshold` set (default 0). Touchpads emit continuous
fractional scroll deltas, not discrete ticks, so with the threshold at 0 every
micro-delta from one scroll gesture fired the script separately -- dozens of
concurrent `pactl`/`brightnessctl`/`notify-send` processes within milliseconds,
flooding mako's D-Bus connection. Fixed with `"smooth-scrolling-threshold": 1` on
both modules.

Reproducing the flood manually (30 concurrent script calls) also caught a second,
more serious bug: `pactl set-sink-volume ... +5%` doesn't clamp at 100% -- the burst
drove the sink to **1494%**. Confirmed nothing was actually playing at the time
(`pactl list sink-inputs short` was empty), so nothing got physically blasted, but
it would have been genuinely dangerous if something had been. `brightnessctl` does
self-clamp (tested: `set 1000%` lands at exactly 100%), so brightness only had the
flood risk, not an overdrive risk. Fixed both scripts with `flock`-serialized
read-compute-apply, and `volume_osd.sh` now computes and clamps its own 0-100
target instead of trusting pactl's relative math. Re-ran the identical 30-call
burst after the fix: lands exactly at the 100%/0% boundary, zero waybar log errors.
Volume/brightness were reset back to their pre-test values (50%/5%) afterward.

## 2026-08-27 (volume/brightness: real sliders and device selection, not nwg-bar buttons)

The volume popup's Vol-/Vol+ buttons "didn't work" -- tested the underlying `pactl`
commands directly first (`env pactl set-sink-volume @DEFAULT_SINK@ -5%`, confirmed
90%->85%, worked fine), so the bug wasn't the command. Read `nwg-bar`'s `launch()`
in its Go source instead: it fires `glib.TimeoutAdd(150, gtk.MainQuit)` after *every*
click, so the whole popup closed ~150ms after each Vol-/Vol+ press -- no way to make
several incremental adjustments without reopening the menu each time. Root cause was
the widget, not the command: `nwg-bar` only has buttons (no scale/slider in its JSON
schema at all), and volume/brightness are drag-to-a-value interactions.

Replaced both:

- `pulseaudio` waybar module: click = mute/unmute, right-click = `pavucontrol` (real
  drag sliders, plus Output/Input device tabs -- microphone selection included, for
  free), scroll = +-5%. `pavucontrol` was already installed and already renders in
  Catppuccin Mocha (the GTK3 theme is applied system-wide via `gtk-3.0/settings.ini`),
  so no new styling work was needed.
- `backlight` waybar module: click = a new script, `scripts/.local/bin/brightness-slider.sh`,
  wrapping `zenity --scale --print-partial | while read v; do brightnessctl set
  "${v}%"; done` -- `--print-partial` streams every drag frame, so it's a real-time
  slider, not a set-once dialog. Needs `zenity` (added to `packages/pacman.txt`,
  official `extra` repo -- **not yet installed on the live machine**, this session
  has no `sudo`: `sudo pacman -S zenity`).
- Deleted `nwg-bar/.config/nwg-bar/volume.json` -- the button-popup it drove is gone.
- `sway/.config/sway/scripts/volume_osd.sh` gained a `mute-toggle` mode (used by both
  the waybar click and the `XF86AudioMute` key, replacing an inline `pactl && notify-send`
  one-liner that had drifted out of sync with the script) and now auto-unmutes before
  applying a volume delta, so scrolling/raising always changes what you actually hear.
  Added `XF86AudioMicMute` (`pactl set-source-mute @DEFAULT_SOURCE@ toggle`) -- there
  was no microphone-mute keybinding before this.
- `brightness_osd.sh`'s scroll path is unchanged in behavior, just now also wired to
  the waybar `backlight` module's `on-scroll-up`/`on-scroll-down` (previously those
  called raw `brightnessctl` directly, with no OSD notification at all).

Verified end to end with `sh -c` invocations matching exactly what waybar itself runs
(not just running the scripts directly): mute-toggle round-trips correctly
(`Mute: no` -> `yes` -> `no`), scroll volume goes 90%->85%, scroll brightness goes
0%->5%, `pavucontrol` resolves on `$PATH`. `brightness-slider.sh` itself needed a
`stow -R scripts` to actually land the new symlink in `~/.local/bin/` -- caught this
because the first `env` test of the exact waybar-invoked absolute path 404'd until
the restow.

## 2026-08-23 (same nwg-bar treatment for volume/wifi/bluetooth/docker -- found the tilde bug again)

Extended the power-menu pattern to four more waybar modules, reusing `nwg-bar` +
the same `style.css` (same glass-card look) rather than inventing a new mechanism per
module:

- `custom/docker` -> **Stats** (`kitty -e docker stats`), **Stop All** (a new wrapper
  script, `scripts/.local/bin/docker-stop-all.sh` -- `$(docker ps -q)` needs a real
  shell, which nwg-bar's `exec` never provides, so this couldn't be inlined in the
  JSON the way Stats could)
- `network` -> **Wi-Fi On/Off** (`nmcli radio wifi on|off`), **Settings**
  (`nm-connection-editor`)
- `bluetooth` -> **BT On/Off** (`bluetoothctl power on|off`), **Manager**
  (`blueman-manager`)
- `pulseaudio` -> **Mute**, **Vol -/+** (`pactl ...`), **Mixer** (`pavucontrol`)

Icons: none of these had bundled SVGs the way the power actions did, but `nwg-bar`'s
`createPixbuf()` (checked the source again) falls back to the system icon theme by
name when the icon string isn't an absolute path -- used standard freedesktop
`-symbolic` names (`audio-volume-high-symbolic`, `network-wireless-symbolic`,
`bluetooth-symbolic`, etc.), all confirmed present in the installed Adwaita theme
before using them, same discipline as verifying Nerd Font glyphs elsewhere. No new
icon assets bundled in this repo.

**Found the exact same class of bug again, in a new place**: waybar's `on-click`
strings used `~/.config/nwg-bar/wifi.json` for the `-t`/`-s` flags. Tested it the same
way as the Lock bug (no-shell invocation via `env`) before trusting it, and found
`nwg-bar`'s own flag parsing doesn't expand `~` either -- worse, it doesn't even
detect it isn't an absolute path the way it does for the `icon` field, so it
concatenated it onto its default config directory and produced a nonsensical path
that failed outright (`open .../nwg-bar/~/.config/nwg-bar/volume.json: no such file or
directory`). Fixed by using absolute paths in all four `on-click` strings, same as
the earlier Lock fix. Re-tested all four (`env nwg-bar -t /home/yash/... -s
/home/yash/...`) and confirmed each loads its correct item count with no errors.

## 2026-08-23 (nwg-bar robustness audit: found and fixed a real "Lock silently does the wrong thing" bug)

Asked to make sure the power button is robust and has no surprises, now that `nwg-bar`
is actually installed. Tested it for real rather than just checking it launches:

- **The Lock button would have shown a bare, unstyled swaylock screen instead of the
  configured one, with no error to explain why.** Read `nwg-bar`'s own Go source
  (`launch()` in `tools.go`): it calls `exec.Command()` directly on the split command
  string, with no shell involved at all -- so `~` in `swaylock -C
  ~/.config/sway/lockconfig` is never expanded, unlike every other place this exact
  command appears in this setup (sway's own `exec` keybinding, `swayidle`'s config),
  which all go through an actual shell. Verified this precisely, not just from reading
  the source: ran `swaylock -C '~/.config/sway/lockconfig'` (literal tilde, no shell,
  the exact byte string `nwg-bar` would pass) and watched it log `Found config at
  ~/.config/sway/lockconfig` immediately followed by `Failed to read config. Running
  without it.` -- swaylock treats the unexpanded tilde as a literal filename, fails
  silently, and falls back to a plain lock screen with none of the configured
  wallpaper/clock/Catppuccin colors. Fixed by using the absolute path
  (`/home/yash/.config/sway/lockconfig`) instead, and confirmed the fix with the same
  test: full config now parses line by line, wallpaper and all.

  (Incidentally locked this machine's real session for a few seconds running that
  first test, since it's genuine `swaylock` with PAM auth, not a mock -- unlocked it
  immediately afterward, no harm done, but worth knowing this class of test isn't
  fully inert.)

- Confirmed all other `exec` commands (`swaymsg exit`, `systemctl suspend/reboot/poweroff`)
  have no path/tilde dependencies, so they're not affected by the same no-shell
  behavior.
- Tested double-launching `nwg-bar` (simulating an accidental double-click on the
  waybar button): only one instance ends up running, no overlapping bars or errors.
- Swept the whole repo for leftover cruft from the wlogout/wofi iterations: no
  dangling references anywhere, `packages/*.txt` clean, and every script in the
  `scripts/` package is confirmed actually referenced from somewhere (sway config,
  waybar config, or a systemd unit) -- nothing orphaned.

## 2026-08-23 (power menu: switched tools -- wofi's dmenu mode wasn't built for this)

User feedback: alignment still off, no pointer cursor, click-outside still not
working -- fair, after five rounds of patching wofi's `--dmenu` mode, each fix
uncovered another real limitation in the same tool rather than converging:

- No CSS `cursor` property support in this GTK version (confirmed via a real GTK
  parse error, not a guess) -- can't give hover feedback via cursor shape at all in
  wofi's dmenu entries.
- `--columns` capped at 2 per row no matter the width or invocation method.
- `--hide-search` breaks entry rendering entirely when combined with `--dmenu`.
- `close_on_focus_loss` can't distinguish "clicked elsewhere" from "hovered near
  another window" while sway's `focus_follows_mouse` (global-only) is on, which it is
  by default.

Each of these is a real, separately-confirmed limitation of wofi's dmenu mode for
this specific use case (a small button-grid popup), not a config mistake -- so
continuing to patch around them wasn't going to converge. Researched purpose-built
alternatives instead of iterating further on the same tool.

**Switched to `nwg-bar`** (part of the nwg-shell project, official Arch `extra` repo --
no AUR build needed): read its actual Go source before committing to it, not just the
README --

- Real `gtk.ButtonNew()` widgets for every entry -- proper pointer-cursor hover
  behavior comes for free from GTK, unlike wofi's list/flow entries.
- Closes on `leave-notify-event` with a genuine 500ms debounce that's cancelled by
  `enter-notify-event` if the pointer comes back -- solves the "closes mid-hover"
  problem architecturally, since it's the bar's own pointer-leave event, not tied to
  sway's global focus model at all.
- Escape also closes it (`key-release-event` checking `KEY_Escape`).
- Its own default template *is* a sway exit menu (Lock/Logout/Reboot/Shutdown) --
  built for exactly this.
- One real limitation found before writing the config, not after: buttons get no
  individual CSS name/class in nwg-bar's source, so per-action accent colors (a
  different hover color for Lock vs Shutdown, like the earlier wlogout attempt) aren't
  possible here. Used one consistent Mauve accent instead, matching how most other
  waybar modules already work.

New `nwg-bar` stow package: `bar.json` (5 entries, referencing the icon SVGs the
`nwg-bar` package itself ships at `/usr/share/nwg-bar/images/` -- no icon assets
bundled in this repo) and `style.css` (same glass-card material as everywhere else:
kitty's 0.85 opacity, Mauve border/radius). Added to `packages/pacman.txt`. Removed
the wofi-based `power-menu.sh` and `power-style.css` entirely.

**Not yet verified visually** -- `nwg-bar` isn't installed on this machine and
installing it needs `sudo`, which this session doesn't have:

```bash
sudo pacman -S nwg-bar
```

Waybar's power button already points at it (`"on-click": "nwg-bar"`); it just won't
do anything until the package above is installed.

## 2026-08-23 (power menu: single row via orientation=horizontal, click-outside dropped for good)

Two things: confirmed in real use (not a synthetic test this time) that the popup was
closing whenever the pointer moved toward *any* window, not just on an actual click --
exactly the `focus_follows_mouse` interaction flagged two entries back, which my
`swaymsg`-based test hadn't actually reproduced (it forced a focus change directly,
which isn't the same as merely hovering causing one). And a request to switch from the
2-column grid to a single row with centered icons, shorter overall.

- Removed `close_on_focus_loss` for good this time. There's no way to get "click
  elsewhere closes it, hover elsewhere doesn't" out of this option while
  `focus_follows_mouse` is `yes` (sway's default, and global-only per `sway.5` -- no
  per-window override), so the honest fix here is to not use it. Dismissing is Escape
  or picking an option, matching every other wofi popup in this setup.
- Switched from `--columns 2` to `-D orientation=horizontal`: a different wofi layout
  mechanism, not subject to the 2-per-row cap `--columns` hit repeatedly in earlier
  entries. Puts all 5 icons in one row directly. Width 560->650, height 460->150 (one
  row needs far less vertical space than a 3-row grid). Verified: 649x149px against a
  requested 650x150, with all 5 tiles visible in a single centered row.

## 2026-08-23 (power menu: fit all tiles, no scrollbar, re-verified click-outside)

More feedback: not all 5 tiles were visible without scrolling, wanted the scrollbar
gone, wanted a pointer cursor on hover, and "click outside doesn't work at all" (true
-- the previous entry removed `close_on_focus_loss` entirely based on untested
reasoning about `focus_follows_mouse`).

- Width 460->560, height 280->460 -- 460px wasn't tall enough for 3 full rows of
  44px-icon tiles with 26px padding, so the third row (the 5th item) was getting cut
  off, forcing a scroll. Added `--hide-scroll` for the scrollbar itself. Verified: all
  5 tiles visible with room to spare, no scrollbar, 559x449px against a requested
  560x460.
- Tried `cursor: pointer` in CSS for the hand-cursor request -- GTK itself reported
  `Theme parsing error: 'cursor' is not a valid property name`, a real warning, not
  silently ignored. GTK3 controls cursor shape at the widget/GDK level, not via CSS,
  so this isn't fixable from the stylesheet. Removed the invalid property rather than
  leave dead CSS with a warning attached.
- **Actually tested `close_on_focus_loss` this time** instead of reasoning about it
  abstractly: opened a real window, confirmed the popup stays open with no action,
  then shifted focus to that window via `swaymsg` (simulating a genuine click
  elsewhere) and confirmed the popup closed immediately. It works correctly -- the
  previous entry's removal was based on untested theory about
  `focus_follows_mouse` that didn't hold up under an actual test. Re-added it.

## 2026-08-23 (power menu: wider, and click-outside removed for a real reason)

Two more requests: more width, and "moving the cursor away closes it" -- reported as a
bug, but it's a direct consequence of `close_on_focus_loss` (added in the previous
entry) interacting with sway's `focus_follows_mouse`, which defaults to `yes` when
unset (confirmed -- it's not set anywhere in `sway/config`). With hover-focus, moving
the mouse off the popup at all counts as losing focus, not just an actual click
elsewhere -- so the popup was closing on mere hover-away, not just clicks.

Checked whether `focus_follows_mouse` could be scoped to just this popup (`sway.5`
confirms it's a global-only command, no `for_window` equivalent) -- fixing this
properly would mean click-to-focus for the *entire* desktop, a far bigger change than
was asked for. Removed `close_on_focus_loss` instead: dismissing now works the same
way as every other wofi popup in this setup (app launcher, calculator, emoji picker)
already does -- Escape or picking an option, no click-outside.

Width 360->460 (height unchanged at 280). Verified: 459x279px against a requested
460x280.

## 2026-08-23 (power menu: bigger, no search bar, click-outside dismisses it)

Three more requests: more width and bigger buttons, remove the search bar, and close
on click-outside instead of requiring Escape.

- Width 220->360, height 320->280 (shorter now that the search bar's gone), tile
  padding 16px->26px, icon font-size 30px->44px. Verified via the same
  screenshot-and-measure approach: 359x279px against a requested 360x280.
- `close_on_focus_loss=true` (via `-D`, a real documented wofi config option, not
  guessed) makes wofi quit when it loses focus -- which is what happens when you
  click anywhere else. Confirmed the flag is actually present on the running
  process's command line; couldn't fully simulate a mouse click to test it end-to-end
  since `ydotool` isn't installed and `wtype` only does keyboard input, and installing
  a new package just for this one test wasn't worth it.
- Tried wofi's own `--hide-search` flag for the search bar first -- **broke entry
  rendering entirely** when combined with `--dmenu` in this wofi version (confirmed
  by testing side by side: identical command minus that one flag rendered the grid
  fine, with it the popup was empty). Worked around it by visually collapsing `#input`
  via CSS instead (`min-height: 0`, `opacity: 0`) -- keeps the widget functionally
  present, which avoids whatever code path the flag itself breaks, while still being
  invisible.

## 2026-08-23 (power menu: actual grid layout, not a vertical list)

Follow-up feedback: wanted the buttons in a real grid, and the popup ("too small but
kind of quite correct") nudged slightly bigger to fit one. wofi supports this
natively via `columns=`/`--columns` -- not something requiring a different tool this
time.

- Switched entries from "icon + text label" to icon-only. With text labels, columns
  rendered at uneven widths (a "Suspend" entry is wider than "Lock"), which is what
  broke the grid look initially.
- Requested `--columns 3` first. Tested it at three different popup widths (300, 400,
  700px), via both the CLI flag and an explicit `--conf` file, and it rendered as
  **exactly 2 columns every single time** -- confirmed this is a real cap in this
  wofi build (v1.5.3) for `--dmenu` mode specifically, not a sizing mistake, by also
  confirming `--columns 1` correctly renders a single column (so the setting isn't
  ignored outright, just capped above 2 here).
- Settled on `--columns 2`: 5 icons give a clean 2+2+1 grid. Verified the final
  popup's actual dimensions by screenshotting it and searching for the Mauve border
  color: 219×319px against a requested 220×320, and confirmed visually (rendered as
  an ASCII brightness map) that it's a real 2-column, 3-row grid, not another uneven
  wrap.
- Restyled `#entry` in `wofi/.config/wofi/power-style.css` for square-ish icon tiles
  (equal padding, larger icon font) now that there's no text label taking up
  horizontal space.

## 2026-08-23 (replaced wlogout with a compact wofi power menu)

User feedback on the fixed wlogout modal: wanted it transparent like kitty's terminal
(0.85 opacity) and much smaller, on the scale of a wofi popup, not a screen-spanning
modal. Tried to get there with wlogout first, hit a real architectural wall rather
than a styling problem:

- Measured (with a synthetic lime-green marker background, same technique as the
  caffeine padding fix, since the wallpaper's own colors made a plain Mauve-color
  search unreliable) that even with tiny 84px buttons, the 5 buttons still spanned
  1438×598px on screen -- three times wider than intended.
- Confirmed via wlogout's own `main.c` that its `GtkGrid` is a plain, unnamed grid
  with no size constraint in the code -- but GTK still expands it to fill the entire
  layer-shell surface (a widget property set at the C level, not something CSS
  `grid { ... }` can override in GTK3).
- Tried `--column-spacing 0 --row-spacing 0` explicitly -- **identical** 1438×598
  measurement, proving the spread isn't about spacing at all; wlogout's grid divides
  the full screen width into N equal columns regardless of button size or spacing
  flags. This is fundamental to how it lays out, not a config mistake.

Given the user's own size reference was wofi's popup, and wofi is already proven in
this exact setup to render at a precise, compact size (verified the app launcher's
600x400 elsewhere) -- switched the whole power menu to a `wofi --dmenu` list instead
of fighting a tool whose layout model doesn't support what was asked:

- New `scripts/.local/bin/power-menu.sh`: prints 5 lines (icon + label) to
  `wofi --dmenu --width 280 --height 260 --style ~/.config/wofi/power-style.css`,
  then runs the matching action from the selection -- same commands already used
  elsewhere in this setup (lock uses the identical
  `swaylock -C ~/.config/sway/lockconfig`).
- New `wofi/.config/wofi/power-style.css`: same visual language as the existing app
  launcher stylesheet, at kitty's 0.85 opacity instead of the launcher's 0.95, so it
  reads as the same "glass" material as the terminal.
- Verified the actual rendered popup by screenshotting it and searching for the Mauve
  border color within the expected center region: **279×259px**, matching the
  requested 280×260 almost exactly.
- Removed the `wlogout` stow package and its `packages/aur.txt` entry entirely --
  abandoned approach, not worth keeping around unused.

## 2026-08-23 (wlogout: fixed a genuinely broken modal, not just restyled it)

User feedback: "the UI of the popup modal is too crud." Investigated with the same
screenshot-and-measure discipline as the caffeine padding fix, rather than guessing at
CSS tweaks -- found real bugs, not just aesthetic ones:

- **The `wlogout` stow package had never actually been `stow`'d.** `~/.config/wlogout/`
  didn't exist at all -- wlogout had been silently falling back to `/etc/wlogout/`'s
  system-default layout and CSS this entire time. Every earlier CSS/layout edit had
  zero effect, because wlogout was never reading any of those files. Caught by running
  it with an explicit `-C`/`-l` path and seeing `Failed to open .../layout` in stderr;
  confirmed by checking `~/.config/wlogout` was simply missing. Now stowed.
- **wlogout's default `--buttons-per-row` isn't 5.** With exactly 5 buttons and no
  explicit `-b`, one button rendered as a proper large card and the other four were
  cramped into a fraction of the row -- confirmed visually via `grim` screenshots
  rendered as ASCII-art brightness maps (no image viewer available in this session).
  Fixed by passing `-b 5` explicitly in the waybar `on-click` command
  (`wlogout -b 5`), which wlogout's own layout math then distributes evenly.
- Tried centering each icon within its card via the `width`/`height` fields
  documented in `wlogout(5)` -- this triggered real `Gtk-CRITICAL` assertion failures
  (`gtk_label_set_yalign/xalign: assertion 'GTK_IS_LABEL (label)' failed`) and only
  marginally improved icon position. Reverted to the default (no `width`/`height`
  override) once confirmed clean and warning-free -- not worth a real GTK error for a
  small positioning tweak.
- Also hit the raw-glyph-gets-silently-stripped issue from earlier sessions many times
  while iterating on this -- inconsistently, sometimes 8+ consecutive identical
  attempts failed before one landed. Every glyph in the final `layout` file was
  written as a `\uXXXX` Python escape and verified by codepoint after writing, not
  trusted on the first attempt.
- Kept the `min-width`/`min-height: 220px` CSS sizing from the first pass as a safety
  net alongside `-b 5`, so card size stays consistent even if buttons-per-row ever
  changes.

Verified the final result with a clean screenshot: 5 evenly-sized floating cards, no
warnings in wlogout's own output.

## 2026-08-23 (power menu: waybar button + wlogout modal)

Added a power button to the far right of the waybar bar (`custom/power`, after
`battery`) that opens `wlogout` — a proper centered floating modal with five large
icon buttons (Lock, Logout, Suspend, Reboot, Shutdown), not a text dmenu list, since
that's what was actually asked for ("very aesthetic... floating... modal").

- New `wlogout` stow package: `layout` (5 buttons, each action wired to what's already
  used elsewhere in this setup -- `swaylock -C ~/.config/sway/lockconfig` for lock,
  matching the manual lock keybind and idle-lock config exactly) and `style.css`
  (Catppuccin Mocha, matching the rest of the desktop: Deep Midnight translucent
  backdrop, floating cards with the same hairline Mauve border as the waybar pills,
  large Nerd Font glyphs standing in for icons instead of bundled image assets --
  consistent with how every other module in this setup does icons).
- Each button gets a distinct hover accent, deliberately breaking from "one consistent
  accent everywhere" (the rule stated for every other waybar module): Mauve for lock,
  Lavender for logout, Teal for suspend, Peach for reboot, Red for shutdown. A power
  menu is the one place where distinguishing "gentle" from "final" by color is real
  feedback, not decoration -- same reasoning already used for workspace hover states.
- Verified every icon glyph (lock, logout, suspend, reboot, shutdown, and the waybar
  trigger's power-off icon) actually exists in JetBrainsMono Nerd Font's charset
  before using it, same discipline as every other icon added this session. Hit the
  raw-character-gets-silently-stripped issue (documented earlier for the tmux
  separators) twice more while building this -- inconsistently this time, sometimes a
  raw pasted glyph survived and sometimes it didn't with no clear pattern -- so
  switched fully to writing `\uXXXX` escapes in Python source and verifying the
  landed codepoints after every single write, rather than trusting either approach
  blindly.
- Added `wlogout` to `packages/aur.txt`. **Not yet installed on this machine** -- AUR
  package installation needs `sudo`, which this session doesn't have:

```bash
yay -S wlogout
```

  The waybar button and config are ready; the button will just do nothing until the
  package above is installed.

## 2026-08-23 (audio/video/brightness robustness audit — found a battery safety gap)

Asked to make sure audio, display, and brightness are all robust and won't
unexpectedly "shut off." Audited each:

- **Brightness was at 1%** (`brightnessctl`: 655/65535) — looked alarming (screen
  effectively looks off) but isn't a bug: `systemd-backlight@backlight:amdgpu_bl1.service`
  is systemd's own brightness persistence (saves on shutdown, restores on boot) working
  exactly as designed. The *previous* session just happened to end at 1%. Bumped it to
  60% for practical use; nothing to fix in config.
- **Audio (pipewire/pipewire-pulse/wireplumber)**: all active, sound plays, volume/mute
  controls work. Clean.
- **Display/GPU**: `dmesg` clean of amdgpu errors or resets, `eDP-1` output active with
  DPMS on. Clean.
- **`batsignal` (battery warnings + forced-suspend-on-danger) was completely broken,
  possibly since it was first configured.** The exec line's comment said "Forces
  Suspend at 5%" but passed `-f` — which is actually batsignal's "battery **full**
  notification" flag (fires when *charging* completes) and requires a percentage
  argument it was never given. Result: `batsignal: Option -f requires an argument.` and
  immediate exit, every single time sway started it. There was no low-battery warning
  and no forced-suspend safety net at all -- a real battery-depletion event would have
  been an uncontrolled power-loss shutdown, not a graceful suspend.

  Fixed with the actual correct flag: `-D COMMAND` ("run COMMAND at the danger level"),
  wired to `-D "systemctl suspend"`. Verified the fix two ways, not just assumed: ran
  the corrected command line directly first (confirmed it starts and finds the battery
  instead of erroring instantly), then after converting to a systemd service, inspected
  `/proc/pid/cmdline` (NUL-separated, unlike `ps`) to confirm systemd's unit-file
  quoting actually kept `"systemctl suspend"` as one argument to `-D` rather than
  splitting it into two.

  Also converted to a systemd service (`systemd/.config/systemd/user/batsignal.service`,
  `Restart=on-failure`) rather than a raw `exec`, matching swayidle and
  sway-audio-idle-inhibit from earlier today -- this is exactly the kind of daemon
  where a silent, unnoticed crash has real consequences (no restart = no warning before
  the battery just dies), so it gets the same auto-recovery treatment.

Added to `install.sh`'s service-enable line.

## 2026-08-23 (verification found two real regressions from this session's own changes)

Went back to check that recent changes actually held up (after the user rebooted to
test the boot-time fix) rather than assuming. `systemctl --failed` was not clean:

- **`swayidle.service` was crash-looping since login**, hitting `start-limit-hit`.
  Root cause: `exec dbus-update-activation-environment --all` -- which imports
  `WAYLAND_DISPLAY`/`SWAYSOCK` into the *systemd --user manager's own environment*
  (separate from sway's process environment, and required before any systemd --user
  service can reach the compositor) -- was sitting near the *bottom* of `sway/config`,
  after `exec systemctl --user restart swayidle.service` had already fired. Introduced
  by me when swayidle got converted to a systemd service a few sessions back; not
  caught at the time because reloading sway to test it doesn't re-run plain `exec`
  lines (only `exec_always` re-fires on reload), so the bug only showed up on a real
  fresh login. Moved the `dbus-update-activation-environment` line to the top of the
  exec block, ahead of anything that depends on it. Fixed the *live* broken state
  separately (ran the import + `systemctl --user reset-failed` + `start` by hand),
  since exec-order fixes in the config file don't retroactively fix an already-running
  session either.
- **`sway-audio-idle-inhibit` had crashed at login and never came back** (segfault in
  `Pulse::connect`, likely connecting to pipewire-pulse before it was fully up) --
  found via `journalctl -p err -b`, not something `systemctl --failed` would show
  since it was a plain `exec`, not a tracked systemd unit, so systemd had no idea it
  died. Converted it to a systemd service too
  (`systemd/.config/systemd/user/sway-audio-idle-inhibit.service`), with
  `After=pipewire-pulse.socket pipewire-pulse.service` to address the likely race and
  `Restart=on-failure` so a future crash recovers on its own instead of silently
  leaving idle-inhibition dead until next login.

Both added to `install.sh`'s service-enable line. Re-checked `systemctl --failed` /
`systemctl --user --failed` clean after applying both fixes, not just assumed.

## 2026-08-23 (boot follow-up: confirmed 4x win, oomd, waybar height fix)

The `iwd`/`systemd-networkd` fix from the previous entry got applied: boot went from
**2min 26s to 36.5s**, confirmed with a fresh `systemd-analyze` run. Went looking for
more, both boot-time and general snappiness:

- Remaining boot-time items (`NetworkManager-wait-online` 5.8s, `docker.service`
  1.7s, `systemd-tpm2-setup{,-early}` ~3.1s combined) are either doing real work
  (actual network readiness, the container runtime) or would need real research before
  touching safely (there's no disk encryption here, so the TPM setup services aren't
  protecting anything critical, but I don't know precisely what else depends on them
  without more digging, and ~3s isn't worth guessing wrong on). Left alone.
- **Enabled `systemd-oomd`** (was disabled). Confirmed the kernel actually supports
  what it needs first (`/proc/pressure/memory` has real PSI data). This is the
  userspace OOM killer that acts *before* a memory-pressure spiral turns into a full
  swap-thrashing freeze — with a browser that can climb into multiple GB of RSS
  against only 4GB of zram swap, this is a real "why did my desktop just freeze for 20
  seconds" prevention, not just a boot-time thing. Added to `install.sh`'s
  service-enable line too.
- **Fixed waybar's height mismatch**: config said `"height": 32`, but every module's
  actual padding (added over this session's redesigns) needs 41px, so waybar was
  silently overriding it and logging a warning on literally every single restart this
  whole session. Just set it to the real value, 41 — no functional change, just an
  honest config that matches what's actually rendered instead of relying on waybar's
  auto-correction and a noisy log.

## 2026-08-23 (found the actual boot-time problem: 2 minutes wasted on a redundant network stack)

Ran a real optimization sweep instead of another cosmetic pass: `zsh -i -c exit` timing
(~200ms after cache warm, fine — p10k's instant prompt is doing its job), `nvim
--startuptime` (~110ms total, fine), `systemd-analyze` and `systemd-analyze blame`.

`systemd-analyze` reported boot as **2min 26s total**, of which
**`systemd-networkd-wait-online.service` alone was 2 minutes** — essentially the
entire boot. Verified this is genuinely dead weight, not something actually needed:

- `nmcli device status` shows NetworkManager owns `wlan0` and is connected.
- `networkctl list` shows `systemd-networkd` *also* trying to configure the same
  `wlan0` (`configuring`, indefinitely — it can never actually finish, since
  NetworkManager already has the interface).
- `/etc/systemd/network/20-{wlan,wwan,ethernet}.network` exist as manual drop-ins —
  leftover from networkd being configured at some point before NetworkManager was
  installed, never cleaned up afterward.
- Separately, `iwd.service` is enabled and running, but NetworkManager's actual wifi
  backend is `wpa_supplicant` (confirmed running, D-Bus-activated by NetworkManager;
  `NetworkManager.conf` has no `wifi.backend=iwd` override) — `iwd` was just a second
  unused wifi daemon sitting in the background the whole time.
- `systemd-resolved` *is* genuinely in use (`resolv.conf` → its stub resolver, real
  DNS answers via `resolvectl status`) — left alone.

**Fixed in the reproducible setup**: `install.sh` was enabling `iwd` alongside
`NetworkManager`, which would have reproduced this exact redundancy (and the 2-minute
boot stall, if a fresh machine's `systemd-networkd` ever got enabled some other way)
on any new machine. Removed `iwd` from the service-enable line — the package stays in
`packages/pacman.txt` since `iwctl` is genuinely useful for bootstrapping Wi-Fi from a
bare TTY before `install.sh` even runs (see the README's Quick Start), it just
shouldn't run as a background service once NetworkManager takes over.

**Not fixed on the live machine** — needs `sudo`, which this session doesn't have:

```bash
sudo systemctl disable --now iwd.service
sudo systemctl disable --now systemd-networkd-wait-online.service systemd-networkd.service
```

Expected result: next boot should land somewhere around 25-30 seconds instead of 2min 26s.

## 2026-08-23 (removed a duplicate wallpaper system, window margins)

### Found and removed a second, untracked, more wasteful wallpaper fetcher

While reloading sway to test an unrelated config change, noticed a real network
fetch happen that had nothing to do with the change. Traced it to
`exec_always --no-startup-id /home/yash/scripts/fetch-bing.sh` in `sway/config` --
a second wallpaper-fetching script, never tracked in this repo, running on
**every sway reload** (not once a day like `wallpaper.timer`). Its own log
(`/tmp/sway_wallpaper.log`) confirmed two runs in the same session just from normal
`swaymsg reload` calls. 50 of the 61 files in `Archive/` turned out to have come
from this script, not the tracked one.

It was actually well-written in places (talked to Bing's real `HPImageArchive` API
directly instead of a third-party proxy, market/index shuffling for variety, archive
pruning) -- but firing on every reload instead of daily directly worked against
"don't add CPU/network load," and it wasn't reproducible since it lived outside the
dotfiles entirely. Its own `fallback.jpg` last-resort file didn't even exist, so its
own fallback path was broken too.

Removed `~/scripts/fetch-bing.sh` and the `exec_always` line entirely. Standardized
on the one already-hardened, tracked, timer-based script
(`fetch_wallpaper.sh`/`wallpaper.timer`, once a day). Ported over the one genuinely
good idea from the removed script -- archive pruning (keep newest 60, prune oldest by
mtime) -- since the tracked script's `Archive/` had no cap and would have grown
unbounded. Verified the prune logic fires correctly with a synthetic over-threshold
test (created 10 dummy files, confirmed the oldest 6 got removed by actual
modification time) before trusting it.

### Window margins + workspace switching feel

- `gaps outer 6` → `9`, and `smart_gaps on` → `smart_gaps inverse_outer`: outer
  (screen-edge) gaps now show specifically when a workspace has exactly one window
  (the common case) so there's always a visible-but-small margin to the screen edge
  then; with multiple tiled windows, outer gaps hide (inner gaps between windows still
  apply) so tiling doesn't waste edge space to a margin you won't see anyway. Plain
  `smart_gaps on` (tried first) hid outer gaps for single-window workspaces too, which
  fought directly against wanting a visible edge margin -- `inverse_outer` reconciles
  both wants instead of picking one.
- `workspace_auto_back_and_forth yes`: pressing the key for the workspace you're
  already on jumps back to whichever workspace you were on before.
- Both are pure sway behavior config -- zero added CPU/RAM, same per-frame gap
  calculation sway already does, just different threshold logic.

True directional slide animation when switching workspaces (the original ask) isn't
achievable on swayfx at any version -- checked the upstream config docs directly
(`animation_duration_ms` only covers individual windows opening/closing, no code path
for animating the workspace switch itself). That would require a compositor built
around it, like Hyprland -- a full compositor swap, not something to start without it
being its own deliberate decision.

## 2026-08-23 (bluetooth fix, caffeine mode)

### Waybar bluetooth module: fixed, same class of bug as before

Root cause of "I don't see bluetooth on the status bar": `format-off` and `format-on`
in the bluetooth module were both **literally empty strings** — same failure mode as
the tmux separators/docker icon a few sessions back (lost glyphs, not a font problem).
Separately, `format-connected` used ``, which is the *speaker* icon
(`nf-fa-volume-down`), not bluetooth — a copy-paste mistake, unrelated to the font
migration. Verified `U+F293` (`nf-fa-bluetooth`) is actually in `JetBrainsMono Nerd
Font`'s charset before using it for all four states; the existing CSS already handles
dimming it when off/disabled and coloring it green when connected, so only the icon
itself needed fixing.

### New: caffeine mode (`custom/caffeine` waybar module)

Added a toggle to keep the screen from dimming/locking/suspending — click the coffee
cup icon in the bar (or run `caffeine-toggle.sh`) to stop it, click again to restore
normal behavior.

Refactored `swayidle` from a raw `exec` line in `sway/config` into a proper systemd
user service (`systemd/.config/systemd/user/swayidle.service`) specifically to support
this cleanly: caffeine-on is just `systemctl --user stop swayidle.service`, caffeine-off
is `systemctl --user start swayidle.service` — no PID tracking, no state file, systemd
already knows whether it's running. `caffeine-status.sh` (polled by waybar every 5s)
reports that same state as the module's icon color (dim gray off, peach glow on).

Deliberately stops swayidle **entirely** rather than using `systemd-inhibit` to just
block suspend: an inhibitor lock wouldn't touch `timeout 600 swaymsg output * dpms
off` at all, since that's swayidle talking to sway directly, never going through
logind. Stopping the whole service is the only thing that keeps the screen itself on
too, which is what "keep it alive" actually means here.

Tried a raw `pkill`/`setsid ... & disown` version first and hit a real, reproducible
hang — the backgrounded `swayidle` process ended up stuck as a direct child of the
toggle script's own bash process (confirmed via `pstree` and `/proc/pid/wchan`
showing `do_wait`), which doesn't happen with well-behaved job control but did happen
here reliably enough to not trust it. The systemd version has no such fragility: no
job-control edge cases, and `Restart=on-failure` for free.

## 2026-08-23 (install.sh end-to-end verification — found a real install-breaking bug)

Went back to close out the one item left unverified: `install.sh` had only ever been
checked piece-by-piece in sandboxes, never proven against the actual current package
manifests. Ran every check that's possible without a spare VM and without `sudo`:

- **Every `packages/pacman.txt` and `packages/aur.txt` entry, checked against the real
  repos** (`pacman -Si` / `yay -Si`, read-only, no root needed). Found a real bug:
  15 packages in `pacman.txt` were actually AUR-only (`brave-bin`, `google-chrome`,
  `swayfx`, `zen-browser-bin`, etc.) — duplicated from `aur.txt`, left over from how
  the manifests were originally generated (`pacman -Qqe` returns *every* explicitly
  installed package regardless of which repo it came from, official or AUR, and that
  got dumped into `pacman.txt` wholesale without subtracting the AUR ones). Separately,
  6 entries in `aur.txt` were `-debug` packages (`bruno-bin-debug`, `swayfx-debug`,
  etc.) — these are auto-generated side effects of building their parent package, not
  real independently-fetchable AUR targets, so `yay -S` would fail trying to fetch them.
  **This mattered because `pacman -S` aborts its entire transaction if even one target
  package name is invalid** — as written, `install.sh` would have failed to install
  *any* of the 104 packages on a truly fresh machine, not just skip the bad ones.
  Removed all 21 bogus entries; every remaining entry in both files now verified to
  resolve.
- **Every external URL the script touches** (9 total: the repo clone, TPM,
  Powerlevel10k, the two zsh plugins, the AUR helper bootstrap, oh-my-zsh's installer,
  Homebrew's installer) — checked with `git ls-remote` for git URLs and a real HTTP
  request for the two raw-file URLs. All resolve.
- **Every systemd service name it enables** (`NetworkManager`, `iwd`, `bluetooth`,
  `docker`, `power-profiles-daemon`, `ufw`, `sddm`, plus the user-level
  `wallpaper.timer`) — confirmed each is a real unit on this system.
- **A full stow simulation with all 13 current packages at once** (the earlier sandbox
  test only used 2 toy packages) against a fake `$HOME` seeded with the actual
  `/etc/skel` files a fresh Arch account would have (`.bashrc`, `.bash_profile`,
  `.bash_logout`) — succeeded cleanly, no false-positive conflicts, every symlink
  (including executable scripts under `.local/bin`) landed correctly.

Still not run as a real, single, uninterrupted execution against an actual blank
machine — that's the one thing that genuinely requires a spare VM or drive. But every
individual piece of it is now verified against reality rather than assumed, and the
one bug that actually would have broken it outright is fixed.

## 2026-08-23 (Docker + UFW writeup, kitty cleanup)

- **`docs/DOCKER_SECURITY.md`** (new): the full explanation of why Docker bypasses UFW
  (it inserts its own `iptables` rules in `DOCKER`/`DOCKER-ISOLATION-STAGE-*`, ahead of
  where UFW's rules apply), exactly what was checked on this machine (`docker ps` —
  nothing running, nothing published, no live exposure), and a concrete fix in two
  layers: bind future publishes to `127.0.0.1` (zero config), or run the new
  `docs/harden-docker.sh` for an actual `DOCKER-USER`-chain-based restriction (allow
  loopback + RFC1918 ranges, drop everything else), with `docs/docker-user-rules.service`
  to make it survive `docker.service` restarts (which reset `DOCKER-USER` to empty).
  Neither script runs automatically anywhere — this couldn't be tested against a real
  container without `sudo`, so it's opt-in with explicit testing steps in the doc
  rather than something applied silently.
- `kitty.conf`: dropped `hide_tab_bar_if_only_one_tab` and `startup_mode` — confirmed
  via `man kitty.conf` that neither exists in kitty 0.48.2 at all (not deprecated
  aliases, just gone). The tab-bar behavior they wanted is kitty's default now
  (`tab_bar_min_tabs 2`); `startup_mode` never mapped to a real directive.

## 2026-08-23 (kitty remote control)

Enabled `allow_remote_control yes` + `listen_on unix:/tmp/kitty-{kitty_pid}` in
`kitty.conf` — `kitty @ ...` / kittens couldn't control the running instance at all
before this (`{"ok": false, "error": "Remote control is disabled"}`), which blocks
live config/font reloads without a full restart. Not force-restarting the running
kitty instance to apply it — this session's remote shell very likely runs *through*
that same kitty window, and killing it would cut the connection. Needs a manual full
quit/reopen of kitty (not just `ctrl+shift+f5`, since `listen_on` sets up a socket at
startup) to actually take effect. Also re-audited the whole live system (not just this
repo) for stray `ZedMono` references post-migration — none found; the font is
consistent across every app that renders it.

## 2026-08-23 (optimization pass)

Went looking for what could be optimized/improved system-wide and fixed what could
safely be fixed without root access (this session's tools have no sudo on this
machine — see the two items at the end that need the user to run them).

### Font: dropped ZedMono Nerd Font entirely

Scoped this as "switch tmux/kitty off the 700MB manual font download" and then found,
partway through, that **ZedMono Nerd Font was actually the primary font across sway,
mako, wofi, zed, and waybar too** — not just kitty/tmux. Deleted the font directory
before catching that (a `grep --include="*.conf" --include="*.sh"` missed the plain
`sway/config`/`mako/config` files with no extension, and the `.css`/`.json` configs
entirely) — a real mistake, caught immediately by re-grepping with no filter, and
since `rm -rf` on ext4 has no undo, the only responsible path forward was finishing
the migration properly everywhere rather than leaving it half-broken.

Switched every reference to `JetBrainsMono Nerd Font` — already a pacman package
(`ttf-jetbrains-mono-nerd`, already in `packages/pacman.txt`), verified via
`fc-query -f '%{charset}'` to cover every codepoint the tmux status bar actually uses
before relying on it. Updated: `kitty.conf`, `sway/config`, `mako/config`,
`wofi/style.css`, `zed/settings.json`, `waybar/style.css`'s font fallback chain, and
removed the now-dead ZedMono download step from `install.sh` entirely — one less
external dependency and one less thing that could fail on a fresh install.

### Committed four "pending WIP" files that turned out to be finished work

These had been sitting uncommitted for a while and were deliberately left alone in
every earlier session on the assumption they might be someone's mid-edit. Actually
reading the diffs this time: all four were complete, coherent work, not unfinished --

- `sway/config`: wires up `swayidle` and `sway-audio-idle-inhibit` automatically at
  startup (previously had to be started manually), plus idle-timeout inhibition for
  fullscreen windows (videos won't get the screen locked mid-playback).
- `waybar/config` + `style.css`: a full redesign -- Nerd Font glyph icons replacing
  emoji throughout, a `network#speed` module added, floating-pill styling reworked
  with real design rationale in the comments (logical module grouping, one consistent
  hover accent instead of per-module colors, tooltips matching the theme).
- `nvim/lazy-lock.json`: routine plugin version bump from normal `nvim` use.

### Display managers: pruned to just the one actually in use

`packages/pacman.txt` had `sddm` (the one actually enabled and running), plus
`greetd` + `greetd-tuigreet` + `ly` installed and unused -- leftovers from earlier
experimentation. Removed the three unused ones from the manifest so a fresh install
doesn't carry them forward. **Not yet removed from this live machine** -- that needs
`sudo`, which this session doesn't have; see the note in `docs/ARCHITECTURE.md`.

### Docker + UFW: documented, not silently "fixed"

Docker manipulates `iptables` directly and can bypass UFW's rules for published
container ports -- a real gap, but checked `docker ps` first and confirmed **no
containers are currently running and no ports are currently published**, so there's
no live exposure today. Given that, and given this session has no `sudo` to test a
firewall change against, writing a specific `iptables`/`ufw` rule I can't verify would
be worse than not touching it -- a wrong firewall rule is a worse outcome than a
correctly-scoped gap. Documented the mechanism and the safe default (bind future
`-p` publishes to `127.0.0.1` explicitly) in `docs/ARCHITECTURE.md` instead.

## 2026-08-13

### Made the wallpaper fetcher bulletproof

Root cause of "sometimes the wallpaper script just crashes sway and I have to keep
reloading": found live in `journalctl --user -u wallpaper.service` — the Bing wallpaper
API occasionally returns a JSON status blob (`[{"success": true}]`) instead of image
bytes. The old script only checked the response was non-empty (`[ -s "$FILEPATH" ]`),
so that JSON got saved as `wallpaper-*.jpg`, symlinked to `current.jpg`, and handed
straight to `swaymsg output * bg ... fill` — which crashes `swaybg` (the process sway
actually delegates background rendering to) since it isn't a real image. The output
goes blank until something reapplies a valid background, which is what "reloading sway
until it works" was actually doing.

Rewrote `scripts/.local/bin/fetch_wallpaper.sh` around three fixes:

- **Actually validate the response is an image** (`file --mime-type`, not just
  non-empty) before it ever touches `current.jpg` or gets near `swaymsg`.
- **Check network connectivity first** (`nmcli networking connectivity check`) and
  give the download itself real timeouts (`--connect-timeout 10 --max-time 20`) and
  3 retries — previously an unreachable network meant an unbounded hang or a fast
  false failure, depending on how DNS/connect behaved that day.
- **Three-tier fallback**, in order: today's freshly-validated download → the last
  known-good wallpaper (`.last_good.jpg`, a stable copy outside the daily
  Active/Archive rotation so it can't itself get archived away or overwritten by a bad
  run) → a plain solid color via `swaybg`'s native `-c`/`solid_color` mode, which needs
  no image file at all and therefore cannot itself fail to parse. A brand-new machine
  with no wallpaper history yet and no network still gets a valid background, never a
  crash.
- Also fixed a latent bug in the *old* script's archiving order: it moved whatever was
  in `Active/` to `Archive/` **before** attempting the new download, so a bad response
  got archived right alongside the real history. Now archiving only happens after the
  new file is confirmed valid.
- Added `flock`-based locking (manual trigger and the daily timer could otherwise race
  each other) and structured logging to `~/.local/state/fetch-wallpaper/fetch-wallpaper.log`
  (simple size-based rotation) — every attempt, failure reason, and fallback decision is
  now visible there instead of the script being a black box between "works" and "crashed
  and I don't know why."

Verified against four scenarios before trusting it live: the real API (happy path), a
fake endpoint returning JSON (the actual historical failure, confirmed it falls back
instead of applying the bad response), an unreachable host (confirmed retry + fallback
to last-known-good), and a from-scratch machine with neither network nor prior
wallpaper history (confirmed the solid-color tier). Then ran it for real on this
machine and confirmed `swaybg` picked up the result correctly.

## 2026-08-13

### Tmux status bar: redesigned and fixed

- **Rebuilt the status bar around a single Catppuccin Mocha palette.** It had drifted
  into a mix of One Dark colors (session/window segments), unrelated Catppuccin accents
  (date/time), and a near-white docker pill (`#E5E9F0`) that clashed with everything
  around it. Now: Mauve (session) / Surface1+Green (windows) / Yellow (docker) / Peach
  (date) / Blue (time) — one dark ink color (`#1e1e2e`) for all pill text.
- **Fixed `bind r`** — it reloaded `~/.tmux.conf`, which hasn't existed since the config
  moved to `~/.config/tmux/tmux.conf`.
- **Fixed the actual glyphs, three times**, because each fix surfaced a new layer of
  the same problem:
  1. Two `.context/*.md` reference docs a redesign was based on turned out to have
     already lost their powerline-separator and docker-icon glyphs — saved as empty
     strings (`@sep_left ""`, `icon=$''`). Copying them verbatim just reproduced the
     loss, not a working config.
  2. Re-typing the glyphs directly into a file-write call *also* silently dropped
     them — something in that write path strips Private-Use-Area Unicode characters.
     Worked around it by writing the codepoints as `\uXXXX` escapes inside a Python
     heredoc run over the shell instead (plain ASCII in transit, decoded to real
     UTF-8 bytes at write time, which does survive).
  3. Once real bytes were landing, the docker icon still rendered as a tofu box —
     wrong codepoint, not a missing font. `U+F395` ("fa-docker") doesn't exist in
     `ZedMonoNerdFont-Regular.ttf`; verified the font's actual glyph coverage with
     `fc-query -f '%{charset}'` before picking a replacement, and switched to
     `U+F308` (`nf-linux-docker`), which the font does contain.
- Added a terminal icon (`U+F489`) in front of the session name — there wasn't one —
  and widened the gap after it once it looked cramped.
- `@continuum-boot` → `off`.

### Made the whole system reproducible from one command

Starting point: a stow-managed dotfiles repo (`~/dotfiles`) covering only
kitty/mako/nvim/sway/tmux/waybar/wofi/zed/zsh, no install script, and several real
(non-symlinked) files quietly living outside the repo entirely.

- **Found and fixed a live secret before it reached GitHub**: `zsh/.zshrc` had
  `GEMINI_API_KEY` hardcoded — uncommitted, but about to go out with the next push.
  Moved it to `~/.zshrc.local` (gitignored, matching the convention the README already
  documented) and had `.zshrc` source that file instead.
- **Vendored everything real-but-untracked**, converting each into a proper stow
  symlink once it was added to the repo:
  - `~/.tmux/scripts/docker_status.sh` → `tmux/.tmux/scripts/`
  - `~/.p10k.zsh` → `zsh/.p10k.zsh`
  - `~/.local/bin/{wf-recorder-toggle,wofi-calc,fetch_wallpaper}.sh` → new `scripts/` package
  - `~/.config/systemd/user/{wallpaper.timer,wallpaper.service,tmux.service}` → new `systemd/` package
  - `~/.config/gtk-{3,4}.0/settings.ini` → new `gtk/` package
  - `~/.config/mimeapps.list` → new `xdg/` package
- **Captured the full package set**: `packages/pacman.txt` (104 official packages) and
  `packages/aur.txt` (22 AUR packages), from `pacman -Qqe` / `pacman -Qqm`.
- **Wrote `install.sh`**, a single idempotent bootstrap script (see
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for what it actually does). Bugs
  caught before they shipped — each verified against real command behavior, not
  assumed:
  - `stow -n`'s actual conflict message format didn't match the first draft's parser;
    combined with `set -e -o pipefail` this would have aborted the whole script on the
    very first package, conflicting or not. Verified the real format in an isolated
    `/tmp` sandbox before trusting the parser.
  - `stow */` (both in the script and in the README's own manual instructions) would
    have tried to stow `.git` and `packages/` into `$HOME` — neither is a real
    package. Now built from an explicit, filtered directory listing.
  - `yay`'s stdin syntax for a package list isn't documented/verified the way
    `pacman -S -` is (confirmed straight from `pacman`'s own man page); switched both
    installs to `xargs -a` instead of trusting an unverified assumption about `yay`.
  - `sddm` was going to be `enable --now`'d mid-script, which would hijack the
    console before the rest of the script finished running. Now just `enable`d — it
    takes over on the reboot the script already tells you to do at the end.
  - The `*.local` gitignore rule (for override files like `.zshrc.local`) also matched
    a directory literally named `.local` — which silently swallowed the entire new
    `scripts/.local/bin/` package from `git status` without any error. Tightened the
    glob to `?*.local` (requires a real prefix before `.local`).
- **Theming**: GTK's `settings.ini` sets the theme *name*, but GNOME-aware apps read
  the active theme from dconf. Added `dconf write` calls for `gtk-theme` and
  `color-scheme` to the end of `install.sh` so a fresh install doesn't end up with the
  theme installed but not actually applied.
