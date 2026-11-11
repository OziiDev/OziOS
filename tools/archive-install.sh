#!/usr/bin/env bash
# Install packages into the running live system from the Arch Linux Archive
# snapshot the live image was built from, so versions match the image and no
# newer library gets mixed into an older system.
#
#   archive-install.sh <YYYY/MM/DD> <package>...
#
# The date is the day of the ISO build (see /usr/lib/os-release BUILD_ID or
# the ISO's volume id). Sync databases go to a scratch directory; the live
# system's own databases are not touched. Run as root.
set -eu

date="${1:?usage: archive-install.sh YYYY/MM/DD package...}"
shift
[ "$#" -gt 0 ] || { echo "no packages given" >&2; exit 2; }

work=/tmp/arch-archive
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

# A link left over from an earlier run points at the live database, which
# pacman would then try to treat as part of the scratch one.
rm -rf "$work/db/local"
pacman --config "$work/pacman.conf" --dbpath "$work/db" --logfile /dev/null -Sy
# --dbpath would hide what is installed, so pacman only learns about it from
# the real local database, linked in next to the scratch sync databases.
rm -rf "$work/db/local"
ln -s /var/lib/pacman/local "$work/db/local"
pacman --config "$work/pacman.conf" --dbpath "$work/db" --cachedir "$work/cache" \
  --noconfirm --needed -S "$@"
