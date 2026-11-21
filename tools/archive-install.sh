#!/usr/bin/env bash
# Install packages into the running live system from the Arch Linux Archive
# snapshot the live image was built from, so versions match the image and no
# newer library gets mixed into an older system.
#
#   archive-install.sh <YYYY/MM/DD> <package>...
#
# The date is the day of the ISO build (see /usr/lib/os-release BUILD_ID or
# the ISO's volume id). Sync databases go to a scratch directory; the live
# system's own sync databases are not touched, and what gets installed is
# recorded in its package database. Run as root.
set -eu

date="${1:?usage: archive-install.sh YYYY/MM/DD package...}"
shift
[ "$#" -gt 0 ] || { echo "no packages given" >&2; exit 2; }

work=/tmp/arch-archive
local_db="$work/db/local"
mkdir -p "$work/db" "$work/cache"
cat > "$work/pacman.conf" <<EOF
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Optional
ParallelDownloads = 3

[core]
Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch

[extra]
Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch

[multilib]
Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch
EOF

# The live package database is mounted into the scratch one below. Never remove
# anything there while it is mounted: that would remove the live database itself.
release() { while mountpoint -q "$local_db"; do umount "$local_db"; done; }
release
# Earlier versions put a symbolic link there instead; pacman 7 writes around a
# link, so packages went unrecorded and empty entries were left in the live
# database, which break every query.
rm -rf "$local_db"
find /var/lib/pacman/local -mindepth 1 -maxdepth 1 -type d -empty -delete

pacman --config "$work/pacman.conf" --dbpath "$work/db" --logfile /dev/null -Sy
# --dbpath would hide what is installed, so the live package database is mounted
# next to the scratch sync databases: pacman resolves against it and records
# what it installs there.
release
rm -rf "$local_db"
mkdir "$local_db"
mount --bind /var/lib/pacman/local "$local_db"
trap release EXIT
pacman --config "$work/pacman.conf" --dbpath "$work/db" --cachedir "$work/cache" \
  --noconfirm --needed -S "$@"
