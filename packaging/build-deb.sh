#!/usr/bin/env bash
# Builds the tapir .deb inside a throwaway Debian container (docker or podman).
# Usage: packaging/build-deb.sh [version]   -> writes ../build-deb/tapir_*.deb
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$SRC_DIR/build-deb}"
DEBIAN_IMAGE="${DEBIAN_IMAGE:-debian:trixie}"
VERSION="${1:-}"
ENGINE="$(command -v docker || command -v podman)"

mkdir -p "$OUT_DIR"
"$ENGINE" run --rm \
    -v "$SRC_DIR:/src:ro" -v "$OUT_DIR:/out" \
    -e VERSION="$VERSION" -e COMMIT="$(git -C "$SRC_DIR" rev-parse --short HEAD 2>/dev/null || true)" -e ENGINE="$(basename "$ENGINE")" -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
    "$DEBIAN_IMAGE" bash -euo pipefail -c '
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends build-essential debhelper devscripts >/dev/null
        # Only what the package contains: scripts, templates and the Keycloak login theme
        mkdir -p /build/docker/keycloak && cd /build
        cp -a /src/debian /src/packaging .
        cp -a /src/docker/keycloak/themes docker/keycloak/
        if [ -n "$VERSION" ]; then
            DEBEMAIL="ci@localhost" DEBFULLNAME="Tapir CI" \
                dch --newversion "$VERSION" --distribution trixie --force-distribution "Automated build $COMMIT"
        fi
        dpkg-buildpackage -b -uc -us
        cp ../tapir_*.deb ../tapir_*.changes ../tapir_*.buildinfo /out/
        # rootless podman already maps container root to the calling user
        if [ "$ENGINE" = docker ]; then chown "$HOST_UID:$HOST_GID" /out/*; fi
    '
ls -lh "$OUT_DIR"
