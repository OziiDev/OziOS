#!/usr/bin/env bash
# Install packages into the running live system from the Arch Linux Archive
# snapshot the live image was built from, so versions match the image and no
# newer library gets mixed into an older system.
#
#   archive-install.sh <YYYY/MM/DD> <package>...
#   archive-install.sh current <package>...
#
# The date is the day of the ISO build (see /usr/lib/os-release BUILD_ID or
# the ISO's volume id). Sync databases go to a scratch directory; the live
# system's own sync databases are not touched, and what gets installed is
# recorded in its package database. Run as root.
#
# With `current` the packages come from the mirrors the live system lists, in
# today's versions: for tools that only run during a build (xorriso, cmake)
# while the archive does not answer. Nothing the live system has may change
# then: if a package would need a newer version of something installed,
# nothing is installed at all.
set -eu

date="${1:?usage: archive-install.sh YYYY/MM/DD|current package...}"
shift
[ "$#" -gt 0 ] || { echo "no packages given" >&2; exit 2; }

if [ "$date" = current ]; then
  server="Include = /etc/pacman.d/mirrorlist"
else
  server="Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch"
fi
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
$server

[extra]
$server

[multilib]
$server
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
if [ "$date" = current ]; then
  # What would be installed; anything among it that the live system already has
  # would be replaced by today's version. (An `if`, not `&&`: a test that fails for
  # the last name must not end the script under set -e.)
  wanted="$(pacman --config "$work/pacman.conf" --dbpath "$work/db" -S --needed --print --print-format '%n' "$@")"
  replaced=""
  for name in $wanted; do
    if pacman -Q "$name" >/dev/null 2>&1; then replaced="$replaced $name"; fi
  done
  if [ -n "$replaced" ]; then
    echo "archive-install: today's packages would replace what the live system has:$replaced" >&2
    exit 1
  fi
fi
pacman --config "$work/pacman.conf" --dbpath "$work/db" --cachedir "$work/cache" \
  --noconfirm --needed -S "$@"
