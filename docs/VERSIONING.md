# Versioning & release process

Started at **v1.0.0**, tagged 2026-08-30, once the desktop reached a state where
every major subsystem had been directly, live-verified as working -- not
just "looks right in the config" (see the stability check in `CHANGELOG.md`'s
`v1.0.0` entry for exactly what was checked and how). Everything before that
tag was pre-1.0, iterative work with no version boundaries; from here on,
this repo follows a real release pattern.

## Branch model

- **`main`** -- always the last known-good, tagged release. Nothing lands here
  directly. The only things that ever touch `main` are merges from
  `development` (each one tagged) and, rarely, a hotfix branched straight off
  `main` for something urgent that can't wait for `development` to be ready.
  This is also the **Stable** update channel (see below) -- `install.sh`
  checks this out by default.
- **`development`** -- the active branch (renamed from `develop` -- both the
  local and GitHub remote branch were renamed together via GitHub's own
  branch-rename API, not a manual delete+recreate, so history/references
  stayed intact). All day-to-day work happens here: every feature, fix, and
  tweak, committed the same way this repo always has (detailed messages,
  real bugs found and how they were verified, no shortcuts). This is the
  branch to be on for anything that isn't "cut a release", and it's also the
  **Nightly** update channel -- day-to-day work, may break.
- Feature branches off `development` are optional, not mandatory -- fine to
  work directly on `development` for most changes, matching how this repo
  has always worked; branch off it only for something big/risky enough to
  want isolated review before it touches `development` itself.

## Update channels (Stable vs Nightly)

`install.sh` asks once, at first install, which of these two branches to
track -- **Stable** (`main`, default) or **Nightly** (`development`).
Whichever is chosen is just what ends up checked out in `~/dotfiles`; nothing
else is channel-aware beyond that. `scripts/.local/bin/update-check.sh` (runs
once per login, see its own comments and `docs/ARCHITECTURE.md`'s package
card for the full mechanism) reads whatever branch is actually checked out
and its real upstream, deriving the "Stable"/"Nightly" label it shows in its
notification/prompt straight from the branch name (`main` -> Stable,
`development` -> Nightly) -- there's no separate channel-preference file to
drift out of sync with what's genuinely on disk.

## Cutting a release

1. Make sure `development` is in a state that's actually been tested live on
   the real system, not just written and assumed correct -- same standard
   this repo has always held changes to, just applied at the branch level
   too.
2. Merge `development` into `main` (fast-forward if possible, no rebasing
   history that's already been pushed).
3. Tag the merge commit: `git tag -a vX.Y.Z -m "..."` -- annotated, not
   lightweight, so the tag itself carries a real message about what the
   release contains.
4. Push both: `git push origin main && git push origin vX.Y.Z`.
5. Add a version marker to the top of `CHANGELOG.md` at that point (see
   below) -- the dated entries underneath it stay exactly as they are, this
   just marks where the release boundary actually falls.

## Version numbers

Loosely semver (`MAJOR.MINOR.PATCH`), kept simple since this is a personal
setup, not a published library with a real compatibility contract to honor:

- **PATCH** -- a fix to something that was broken (a bug, a regression, a
  wrong assumption corrected).
- **MINOR** -- a new feature or capability that didn't exist before
  (a new picker, a new mode, a new keybinding class of thing).
- **MAJOR** -- something big enough to change how the desktop fundamentally
  behaves or how this repo itself is organized/worked with -- rare. v1.0.0
  itself is the only one so far, marking "this is now a real, versioned
  project" rather than marking any specific technical milestone.

## CHANGELOG.md convention going forward

The existing dated-entry format (`## YYYY-MM-DD (short description)`,
newest first, one entry per logical change, full reasoning/bugs/verification
inline) doesn't change -- it's already exactly the right level of detail and
stays the primary record of *what happened and why*. Version tags are a
second, coarser layer on top: at each release, a line like

```
## v1.0.0 -- 2026-08-30
```

gets inserted directly above the dated entry it corresponds to, marking
"everything from here down, up to the previous version marker, is what
shipped in this version" -- without editing or collapsing any of the
existing dated entries underneath it.
