# Power menu icons

Not nwg-bar's own stock icons, and not solid-fill icons either --
reported back twice: first that Suspend's shape wasn't meaningful ("a
circle with a vertical rod in the middle"), then that a solid-icon
replacement pass (Adwaita's set) lost the *lean* look of the originals
entirely -- "older once were better than this. i want lean icons just
like the older once but just different." Landed on: keep the thin,
outline, single-stroke look the originals had, but with genuinely
distinct, recognizable shapes instead of near-identical rings.

Sourced from [Lucide](https://lucide.dev) -- a modern line-icon set
(24x24 grid, 2px stroke, round caps/joins, no fill) already vendored
locally as an npm dependency in another project on this machine
(`~/Codes/claude-remote-main/client/node_modules/lucide-react`), not
fetched from the network. Every icon here is that exact path data,
copied out of Lucide's own per-icon source files and wrapped in a plain
standalone SVG -- same style, same stroke weight, across all five, so
they read as one consistent family rather than a patchwork:

| Action   | Lucide icon | Shape |
| -------- | ----------- | ----- |
| Lock     | `lock`      | a hollow padlock outline |
| Logout   | `log-out`   | a door outline with an arrow pointing out |
| Suspend  | `moon`      | a thin crescent moon -- the universal "sleep" symbol |
| Reboot   | `rotate-cw` | a circular refresh/restart arrow |
| Shutdown | `power`     | the real ISO power/standby symbol (ring + vertical line), same concept as before, now in the same lean stroke style as the rest |

`download.svg`/`clock.svg` added later for the update-prompt bar
(`update-bar.json`/`update-bar-style.css`, see `scripts/.local/bin/
update-check.sh`) -- same source, same exact wrapper template
(`stroke-width="1.5"`, `#CDD6F4`, 24x24), pulled from the same
already-vendored `lucide-react` copy rather than fetched fresh, so
every icon across every nwg-bar prompt in this desktop stays one
consistent family:

| Action     | Lucide icon | Shape |
| ---------- | ----------- | ----- |
| Update Now | `download`  | a downward arrow into a tray -- the standard "fetch/install" symbol |
| Later      | `clock`     | a plain clock face -- "remind me", not a dismissive X |

Lucide's own default is `stroke="currentColor"` -- swapped for a
hardcoded `#CDD6F4` (Clean Silver, this bar's own text color) instead,
same reasoning as every other icon fix in this repo: these load as raw
SVG files via an absolute path, not through GTK's own icon-theme
resolution, so `currentColor` has no guaranteed context to resolve
against.

Color stays off the icon entirely -- still the button's job
(`style.css`'s own per-`nth-child` border tints), unchanged by this
pass. Verified live: launched `nwg-bar` directly and read every icon's
actual rendered pixels back as ASCII art.
