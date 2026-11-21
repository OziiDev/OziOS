#!/usr/bin/env bash
# Run inside the Dev VM (a live session, build disk mounted at /mnt/build,
# project folder at /mnt/ozios): convert the ISO, in the background, and write
# the output to .bridge/remaster.log.
#
#   bash /mnt/ozios/tools/build-iso-in-vm.sh [edu]
#
# By default it converts the medium the session was booted from (the CachyOS
# ISO) with the kernel packages in the project's .kernel-pkgs. From another live
# session, an OziOS one for example, name the source and the kernel instead:
#
#   OZI_SOURCE_ISO=/mnt/ozihost/CachyOS.iso OZI_KERNEL_DIR=/mnt/ozihost/.kernel-pkgs \
#     bash /mnt/ozios/tools/build-iso-in-vm.sh
#
# The OziOS image is made from that same CachyOS ISO, so its tools fit.
set -u

edition=""
[ "${1:-}" = edu ] && edition="--edition edu"
repo=/mnt/ozios
log="$repo/.bridge/remaster.log"
kernel="${OZI_KERNEL_DIR:-$repo/.kernel-pkgs}"
source_arg=""
[ -n "${OZI_SOURCE_ISO:-}" ] && source_arg="--iso $OZI_SOURCE_ISO"
[ -d "$kernel" ] || { echo "build: no kernel packages in $kernel"; exit 1; }

# The build's own tools, where the live image lacks them: xorriso writes the ISO,
# and the window frames are compiled (packages/ozios-decoration). They come from
# the snapshot the image was made from; the first try after boot can fail while
# the network comes up. When the Arch Linux Archive does not answer at all, they
# come from today's mirrors, as long as that changes nothing the live system has:
# the frames are still compiled by its own compiler, against its own KWin.
tools=""
command -v xorriso >/dev/null || tools="$tools libisoburn"
command -v cmake >/dev/null || tools="$tools cmake"
[ -d /usr/share/ECM ] || tools="$tools extra-cmake-modules"
command -v g++ >/dev/null || tools="$tools gcc"
command -v make >/dev/null || tools="$tools make"
command -v pkgconf >/dev/null || tools="$tools pkgconf"
if [ -n "$tools" ]; then
  for source in 2026/08/09 2026/08/09 2026/08/09 current; do
    # shellcheck disable=SC2086
    bash "$repo/tools/archive-install.sh" "$source" $tools >/dev/null 2>&1 && break
    sleep 10
  done
fi
command -v xorriso >/dev/null || { echo "build: no xorriso"; exit 1; }
command -v cmake >/dev/null && command -v g++ >/dev/null && [ -d /usr/share/ECM ] ||
  { echo "build: no compiler for the window frames"; exit 1; }

# A run that stopped early can leave the source ISO mounted inside the work folder.
findmnt -rno TARGET | grep '^/mnt/build/remaster/' | sort -r | while read -r target; do umount -l "$target"; done
# Everything from the last run except its downloaded packages.
mkdir -p /mnt/build/remaster
find /mnt/build/remaster -mindepth 1 -maxdepth 1 ! -name pkgcache -exec rm -rf {} +
mkdir -p "$(dirname "$log")"
rm -f "$log"
systemd-run --unit "ozi-remaster-$$" --working-directory="$repo" bash -c \
  "bash $repo/iso/remaster.sh $source_arg --kernel $kernel --archive 2026/08/09 --add 'python-pyqt6 podman bubblewrap pacman-contrib ttf-overpass kdialog' $edition > $log 2>&1; echo \"exit \$?\" >> $log"
echo "build started; follow $log"
