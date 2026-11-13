#!/usr/bin/env bash
# Run inside the Dev VM (live session of the source ISO, build disk mounted at
# /mnt/build, project folder at /mnt/ozios): convert the ISO, in the background,
# and write the output to .bridge/remaster.log.
#
#   bash /mnt/ozios/tools/build-iso-in-vm.sh [edu]
set -u

edition=""
[ "${1:-}" = edu ] && edition="--edition edu"
repo=/mnt/ozios
log="$repo/.bridge/remaster.log"

# xorriso: not in every live image, and the first attempt after boot can fail
# while the network comes up.
if ! command -v xorriso >/dev/null; then
  for _ in 1 2 3; do
    bash "$repo/tools/archive-install.sh" 2026/08/09 libisoburn >/dev/null 2>&1 && break
    sleep 10
  done
fi
command -v xorriso >/dev/null || { echo "build: no xorriso"; exit 1; }

rm -rf /mnt/build/remaster
rm -f "$log"
systemd-run --unit "ozi-remaster-$$" --working-directory="$repo" bash -c \
  "bash $repo/iso/remaster.sh --kernel $repo/.kernel-pkgs --archive 2026/08/09 --add 'python-pyqt6 podman bubblewrap' $edition > $log 2>&1; echo \"exit \$?\" >> $log"
