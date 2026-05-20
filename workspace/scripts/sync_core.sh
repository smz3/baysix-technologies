#!/usr/bin/env bash
# Sync B2B detection logic from sigma-crypto (source of truth) into sigma-lean's
# embedded mirror. Run this after any changes to sigma-crypto/core/b2b/.
# Must be run from the sigma-brain root.

set -e

SRC="workspace/sigma-crypto/core"
# sigma_core lives inside B2BZoneStrategy/ so LEAN bundles it with the project
DST="workspace/sigma-lean/B2BZoneStrategy/sigma_core/b2b"
DST_MIRROR="workspace/sigma-lean/sigma_core/b2b"

for dir in detectors filters models strategy; do
    rsync -av --delete "$SRC/$dir/" "$DST/$dir/"
    rsync -av --delete "$SRC/$dir/" "$DST_MIRROR/$dir/"
done

echo "sync_core: done — B2BZoneStrategy/sigma_core and sigma-lean/sigma_core are up to date"
