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

# xorriso: not in every live image, and the first attempt after boot can fail
# while the network comes up.
if ! command -v xorriso >/dev/null; then
  for _ in 1 2 3; do
    bash "$repo/tools/archive-install.sh" 2026/08/09 libisoburn >/dev/null 2>&1 && break
    sleep 10
  done
fi
command -v xorriso >/dev/null || { echo "build: no xorriso"; exit 1; }

# A run that stopped early can leave the source ISO mounted inside the work folder.
findmnt -rno TARGET | grep '^/mnt/build/remaster/' | sort -r | while read -r target; do umount -l "$target"; done
rm -rf /mnt/build/remaster
mkdir -p "$(dirname "$log")"
rm -f "$log"
systemd-run --unit "ozi-remaster-$$" --working-directory="$repo" bash -c \
  "bash $repo/iso/remaster.sh $source_arg --kernel $kernel --archive 2026/08/09 --add 'python-pyqt6 podman bubblewrap pacman-contrib ttf-overpass kdialog' $edition > $log 2>&1; echo \"exit \$?\" >> $log"
echo "build started; follow $log"
