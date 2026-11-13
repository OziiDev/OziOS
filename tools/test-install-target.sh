#!/usr/bin/env bash
# Check the OziOS installer step without clicking through Calamares: build a
# small target system on an empty disk, run /usr/lib/ozios/install-to-target
# against it exactly as Calamares would, and look at the result.
#
#   tools/test-install-target.sh <disk> <YYYY/MM/DD>
#
# Run as root in the live session. The disk is wiped. INSTALL_SCRIPT points at
# a checkout copy of install-to-target when that is what should be tested. The date selects the Arch
# Archive snapshot the target is built from; use the ISO's build date so the
# base system matches the packages already on the medium.
set -euo pipefail

disk="${1:?usage: test-install-target.sh <disk> <YYYY/MM/DD>}"
date="${2:?usage: test-install-target.sh <disk> <YYYY/MM/DD>}"
root=/tmp/calamares-root-test
[ -b "$disk" ] || { echo "$disk is not a block device" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 2; }
[ "$(lsblk -no NAME "$disk" | wc -l)" -le 1 ] || { echo "$disk has partitions; refusing" >&2; exit 2; }

step() { printf '\n==> %s\n' "$*"; }
part() { case "$disk" in *[0-9]) echo "${disk}p$1" ;; *) echo "${disk}$1" ;; esac; }

step "Partitioning $disk"
parted -s "$disk" mklabel gpt mkpart ESP fat32 1MiB 513MiB set 1 esp on mkpart root ext4 513MiB 100%
partprobe "$disk"; sleep 2
mkfs.fat -F32 "$(part 1)" >/dev/null
mkfs.ext4 -q "$(part 2)"
mkdir -p "$root"
mount "$(part 2)" "$root"
mkdir -p "$root/boot"
mount "$(part 1)" "$root/boot"

step "Installing a base system from the $date snapshot"
conf=/tmp/archive-pacman.conf
cat > "$conf" <<EOF
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Optional
ParallelDownloads = 3

[core]
Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch

[extra]
Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch
EOF
pacstrap -C "$conf" -K "$root" base linux-firmware grub efibootmgr sudo
# Inside the target pacman should keep using the same snapshot.
sed -i '/^Server/d;/^#Server/d' "$root/etc/pacman.d/mirrorlist"
echo "Server = https://archive.archlinux.org/repos/$date/\$repo/os/\$arch" >> "$root/etc/pacman.d/mirrorlist"
arch-chroot "$root" pacman -Sy --noconfirm >/dev/null

step "Installing the boot loader, as Calamares does before our step"
arch-chroot "$root" grub-install --target=x86_64-efi --efi-directory=/boot --removable
arch-chroot "$root" grub-mkconfig -o /boot/grub/grub.cfg 2>&1 | tail -n 3
echo "root:ozi" | arch-chroot "$root" chpasswd

step "Running the OziOS installer step"
mkdir -p /opt/ozios
ls -la /opt/ozios
bash -x "${INSTALL_SCRIPT:-/usr/lib/ozios/install-to-target}" || true

step "What ended up in the target"
arch-chroot "$root" pacman -Q ozios-settings linux-ozios python-pyqt6 2>&1 || true
ls "$root/boot" "$root/usr/lib/modules" 2>&1 || true
grep -c ozios "$root/boot/grub/grub.cfg" 2>/dev/null && grep -m3 -E 'menuentry' "$root/boot/grub/grub.cfg" || echo "no grub.cfg"
grep -E 'NAME=|OZIOS' "$root/etc/os-release" 2>&1 || true
