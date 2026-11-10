#!/usr/bin/env bash
# Build the OziOS live ISO: the CachyOS live profile plus our overlay.
#
#   iso/build.sh --prepare-disk /dev/sdX   turn an EMPTY disk into build space
#   iso/build.sh [workdir]                 build (default: /mnt/build, else ~/ozios-build)
#
# The build needs about 20 GB of real disk. A live session keeps / in RAM, so
# there you have to give it a disk with --prepare-disk first.
set -euo pipefail

repo="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
upstream="https://github.com/CachyOS/CachyOS-Live-ISO.git"

die() { echo "build: $*" >&2; exit 1; }
step() { printf '\n==> %s\n' "$*"; }

prepare_disk() {
  local dev="$1"
  [ -b "$dev" ] || die "$dev is not a block device"
  sudo mkdir -p /mnt/build
  if [ "$(lsblk -dno LABEL "$dev")" != ozibuild ]; then
    # Only ever format a disk that has nothing on it.
    if [ "$(lsblk -no NAME "$dev" | wc -l)" -gt 1 ] || [ -n "$(lsblk -dno FSTYPE "$dev")" ]; then
      die "$dev already has data or partitions; refusing to format it"
    fi
    sudo mkfs.ext4 -q -L ozibuild "$dev"
  fi
  mountpoint -q /mnt/build || sudo mount "$dev" /mnt/build
  sudo chown "$(id -u):$(id -g)" /mnt/build
  df -h /mnt/build
}

if [ "${1:-}" = "--prepare-disk" ]; then
  [ -n "${2:-}" ] || die "usage: build.sh --prepare-disk /dev/sdX"
  prepare_disk "$2"
  exit 0
fi

work="${1:-}"
if [ -z "$work" ]; then
  if mountpoint -q /mnt/build; then work=/mnt/build; else work="$HOME/ozios-build"; fi
fi
mkdir -p "$work"
work="$(readlink -f "$work")"

[ "$(findmnt -no FSTYPE -T "$work")" != overlay ] || die "$work is in RAM; run --prepare-disk first"
free_gb="$(df --output=avail -BG "$work" | tail -1 | tr -dc '0-9')"
[ "$free_gb" -ge 18 ] || die "only ${free_gb} GB free in $work, need 18"

step "Installing build tools"
sudo pacman -Sy --needed --noconfirm archiso mkinitcpio-archiso git squashfs-tools grub

# Downloaded packages are several GB; keep them off the live session's RAM disk.
if [ "$(findmnt -no FSTYPE /)" = overlay ] && ! mountpoint -q /var/cache/pacman/pkg; then
  mkdir -p "$work/pkgcache"
  sudo mount --bind "$work/pkgcache" /var/cache/pacman/pkg
fi

step "Fetching the CachyOS live profile"
sudo rm -rf "$work/upstream"
git clone --depth 1 "$upstream" "$work/upstream"
profile="$work/upstream/archiso"
root="$profile/airootfs"
[ -f "$profile/packages_desktop.x86_64" ] || die "upstream layout changed: no packages_desktop.x86_64"

step "Applying the OziOS overlay"
added=0
while IFS= read -r pkg; do
  case "$pkg" in '' | \#*) continue ;; esac
  if ! grep -qxF "$pkg" "$profile/packages_desktop.x86_64"; then
    echo "$pkg" >> "$profile/packages_desktop.x86_64"
    added=$((added + 1))
  fi
done < "$repo/iso/packages.ozi.x86_64"
echo "packages added: $added"

# OziOS itself is one package, served to the build from a local repository.
# makepkg gets a copy of the recipe on real disk; the shared folder it comes
# from does not keep Unix permissions.
rm -rf "$work/pkgbuild" "$work/makepkg" "$work/repo"
mkdir -p "$work/pkgbuild" "$work/repo"
cp "$repo/packages/ozios-settings/PKGBUILD" "$repo/packages/ozios-settings/ozios-settings.install" "$work/pkgbuild/"
(cd "$work/pkgbuild" && OZI_SRC="$repo" BUILDDIR="$work/makepkg" PKGDEST="$work/repo" makepkg -f --nodeps)
package="$(find "$work/repo" -name 'ozios-settings-*.pkg.tar.*' ! -name '*.sig' | head -n1)"
[ -n "$package" ] || die "makepkg did not produce ozios-settings"
repo-add -q "$work/repo/ozios.db.tar.zst" "$package"

cat >> "$profile/pacman.conf" <<EOF

[ozios]
SigLevel = Optional TrustAll
Server = file://$work/repo
EOF
echo ozios-settings >> "$profile/packages_desktop.x86_64"

# The installer copies this into the system it installs.
install -Dm644 "$package" "$root/opt/ozios/$(basename "$package")"

[ -f "$root/etc/hostname" ] && echo ozios > "$root/etc/hostname"

# Boot menu titles only. Labels and kernel arguments must stay as they are,
# the live system finds its own medium through them.
find "$profile/grub" "$profile/syslinux" "$profile/efiboot" -type f \( -name '*.cfg' -o -name '*.conf' \) -print0 2>/dev/null |
  xargs -0 -r sed -i -E '/^[[:space:]]*(menuentry|submenu|title|MENU LABEL|MENU TITLE)/ s/CachyOS/OziOS/g'

step "Building (this takes a long time)"
cd "$work/upstream"
sudo ./buildiso.sh -p desktop -v || echo "build: buildiso.sh reported an error, checking for an ISO anyway" >&2

iso="$(find "$work/upstream/out" -name '*.iso' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
[ -n "$iso" ] || die "no ISO was produced; see the log under $work/upstream"

name="ozios-$(date +%y%m%d).iso"
sudo mv "$iso" "$work/$name"
sudo chown "$(id -u):$(id -g)" "$work/$name"
(cd "$work" && sha256sum "$name" > "$name.sha256")

step "Done"
ls -lh "$work/$name"
if [ -w "$repo" ] && [ "$repo" != "$work" ]; then
  mkdir -p "$repo/out"
  cp "$work/$name" "$work/$name.sha256" "$repo/out/" && echo "copied to $repo/out/"
fi
