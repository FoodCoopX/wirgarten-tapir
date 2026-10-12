#!/usr/bin/env bash
# Builds a signed flat-layout APT repository from a directory of .deb files.
# Usage: packaging/build-apt-repo.sh <deb-dir> <repo-dir> [gpg-key-id]
#
# Result: <repo-dir>/dists/trixie/main/binary-amd64/Packages, pool/main/*.deb,
# signed InRelease/Release.gpg and the public key as tapir-archive-keyring.gpg
set -euo pipefail

DEB_DIR="$1"
REPO_DIR="$2"
KEY_ID="${3:-}"
SUITE="${SUITE:-trixie}"
COMPONENT=main
ARCH=amd64

mkdir -p "$REPO_DIR/pool/$COMPONENT" "$REPO_DIR/dists/$SUITE/$COMPONENT/binary-$ARCH"
cp "$DEB_DIR"/*.deb "$REPO_DIR/pool/$COMPONENT/"

cd "$REPO_DIR"
apt-ftparchive packages "pool/$COMPONENT" > "dists/$SUITE/$COMPONENT/binary-$ARCH/Packages"
gzip -9kf "dists/$SUITE/$COMPONENT/binary-$ARCH/Packages"

apt-ftparchive \
    -o "APT::FTPArchive::Release::Origin=Tapir" \
    -o "APT::FTPArchive::Release::Label=Tapir" \
    -o "APT::FTPArchive::Release::Suite=$SUITE" \
    -o "APT::FTPArchive::Release::Codename=$SUITE" \
    -o "APT::FTPArchive::Release::Architectures=$ARCH" \
    -o "APT::FTPArchive::Release::Components=$COMPONENT" \
    release "dists/$SUITE" > Release.tmp
mv Release.tmp "dists/$SUITE/Release"

if [ -n "$KEY_ID" ]; then
    gpg --batch --yes --local-user "$KEY_ID" --clearsign -o "dists/$SUITE/InRelease" "dists/$SUITE/Release"
    gpg --batch --yes --local-user "$KEY_ID" --armor --detach-sign -o "dists/$SUITE/Release.gpg" "dists/$SUITE/Release"
    gpg --batch --yes --export "$KEY_ID" > tapir-archive-keyring.gpg
fi
