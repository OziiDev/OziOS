#!/usr/bin/env bash
# List what in a running image still belongs to CachyOS: packages, files that
# carry its name, configuration that mentions it and the boot menu entries.
# Read-only. Run it in a live session:  bash tools/inventory-cachyos.sh
set -u

echo "== packages with cachy in the name =="
pacman -Qq 2>/dev/null | grep -i cachy | while read -r p; do
  printf '%-40s %s\n' "$p" "$(pacman -Qi "$p" 2>/dev/null | awk -F': *' '/^Installed Size/ {print $2}')"
done

echo; echo "== kernels =="
pacman -Qq 2>/dev/null | grep -E '^linux(-|$)' | grep -v firmware | head -30
ls /run/archiso/bootmnt/arch/boot/x86_64 2>/dev/null

echo; echo "== repositories =="
grep -n '^\[' /etc/pacman.conf

echo; echo "== files and directories named after it =="
find /usr/share /etc /usr/lib -maxdepth 4 -iname '*cachy*' 2>/dev/null | sort | head -120

echo; echo "== config that mentions it (outside package data) =="
grep -rIl -i cachyos /etc 2>/dev/null | head -60

echo; echo "== boot menu entries =="
grep -rIl -i 'cachyos' /run/archiso/bootmnt --include='*.cfg' --include='*.conf' 2>/dev/null
