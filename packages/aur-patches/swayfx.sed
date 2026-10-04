# swayfx 0.6's PKGBUILD depends on scenefx0.5, which no longer exists: scenefx
# 0.5 moved to [extra] as plain `scenefx`, without a scenefx0.5 provides.
# Fix from the AUR comments. A no-op once the PKGBUILD itself is fixed.
s/"scenefx0\.5"/"scenefx"/
s/\bscenefx0\.5\b/scenefx/g
