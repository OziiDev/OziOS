#!/usr/bin/env bash
# Look inside the system the installer put on a disk, from a live session,
# without booting it: kernels, boot loader, packages, accounts. Run as root:
#
#   bash /mnt/ozios/tools/inspect-target.sh [disk]
#
# The disk is mounted read-only and let go again.
set -u
disk="${1:-/dev/sda}"
mnt=/mnt/target
mkdir -p "$mnt"

root="$(lsblk -lnpo NAME,FSTYPE "$disk" | awk '$2 == "btrfs" || $2 == "ext4" || $2 == "xfs" || $2 == "f2fs" {print $1; exit}')"
[ -n "$root" ] || { echo "no root file system on $disk" >&2; exit 1; }
mount -o ro,subvol=@ "$root" "$mnt" 2>/dev/null || mount -o ro "$root" "$mnt" || exit 1
boot="$(lsblk -lnpo NAME,FSTYPE "$disk" | awk '$2 == "vfat" {print $1; exit}')"
[ -n "$boot" ] && mount -o ro "$boot" "$mnt/boot" 2>/dev/null
trap 'umount -R "$mnt" 2>/dev/null' EXIT

say() { printf '\n== %s\n' "$*"; }
installed() { pacman -r "$mnt" --dbpath "$mnt/var/lib/pacman" -Qq 2>/dev/null; }

say "os-release"
grep -E '^(NAME|PRETTY_NAME|ID|VARIANT_ID|BUILD_ID|OZIOS_VERSION)=' "$mnt/etc/os-release"

say "kernels in /usr/lib/modules"
ls "$mnt/usr/lib/modules"

say "kernel, boot loader and OziOS packages"
installed | grep -E '^(linux|cachyos|ozios|chwd|limine|grub|systemd-boot|refind|plymouth|sddm|plasma-login|greetd)' | sort | tr '\n' ' '
echo

say "/boot"
ls "$mnt/boot"

say "boot loader entries"
if [ -f "$mnt/boot/limine.conf" ]; then
  grep -vE '^\s*(#|$)' "$mnt/boot/limine.conf" | head -50
fi
if [ -f "$mnt/boot/grub/grub.cfg" ]; then
  grep -E "^\s*(menuentry|set theme|set default)" "$mnt/boot/grub/grub.cfg" | head -30
fi
ls "$mnt/boot/EFI" "$mnt/boot/EFI/"* 2>/dev/null | head -20

say "accounts and host"
cat "$mnt/etc/hostname"
grep -E '^(tester|root):' "$mnt/etc/passwd"
cat "$mnt/etc/locale.conf" "$mnt/etc/vconsole.conf" 2>/dev/null

say "display manager"
readlink "$mnt/etc/systemd/system/display-manager.service"
ls "$mnt/etc/sddm.conf.d" "$mnt/etc/plasmalogin.conf.d" 2>/dev/null

say "OziOS files"
ls "$mnt/usr/share/ozios" 2>/dev/null | tr '\n' ' '
echo
cat "$mnt/usr/share/ozios/edition" 2>/dev/null
ls "$mnt/usr/bin/ozi" "$mnt/usr/bin/ozi-pen" "$mnt/usr/bin/ozi-classroom" 2>&1 | sed 's|.*/||'

say "fstab"
grep -vE '^\s*(#|$)' "$mnt/etc/fstab"

say "left behind from the installer"
ls "$mnt/opt/ozios" 2>/dev/null | head
ls "$mnt/var/log" 2>/dev/null | head -5
