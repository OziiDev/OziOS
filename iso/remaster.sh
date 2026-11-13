#!/usr/bin/env bash
# Turn a CachyOS live ISO into an OziOS live ISO without rebuilding it.
#
#   sudo iso/remaster.sh [--iso <file-or-device>] [--work <dir>] [--add "<pkg> ..."]
#                        [--archive <YYYY/MM/DD>] [--kernel <dir>] [--edition edu] [--keep-root]
#
#   --add "<pkg> ..."   extra packages for the image. The OziOS package needs
#                       python-pyqt6; podman runs boxed .deb apps.
#   --archive <date>    take the --add packages from the Arch Linux Archive
#                       snapshot of that day (the ISO's build date) instead of
#                       today's mirrors, so they match the image's libraries.
#
#   --edition edu  the Education edition for smart boards: adds the ozios-edu
#                   package and what it needs, Turkish defaults for the live
#                   session, and names the ISO ozios-edu-*.
#   --kernel <dir>  directory with the packages built by kernel/build.sh
#                   (linux-ozios, linux-ozios-nvidia-open, linux-ozios-zfs).
#                   They replace the linux-cachyos* ones, and the live boot
#                   files and menus are switched to the new kernel. Build the
#                   kernel with OZI_KERNEL_DATE set to the ISO's build date.
#
# The root image is unpacked, OziOS is installed into it, and the repacked
# image replaces the original inside a copy of the ISO. Kernel, boot loaders
# and partition layout are carried over untouched, so anything that booted
# the source ISO boots the result.
#
# Run it from the live session of the ISO being converted: with no --iso it
# uses the medium it was booted from. Needs about 16 GB in the work directory.
set -euo pipefail

repo="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
src="" work="" add="" keep=false kernel="" archive="" edition=""
while [ $# -gt 0 ]; do
  case "$1" in
    --keep-root) keep=true; shift ;;   # reuse the root unpacked by an earlier run
    --iso)  src="${2:?}"; shift 2 ;;
    --work) work="${2:?}"; shift 2 ;;
    --add)  add="${2:?}"; shift 2 ;;
    --archive) archive="${2:?}"; shift 2 ;;
    --kernel) kernel="${2:?}"; shift 2 ;;
    --edition) edition="${2:?}"; shift 2 ;;
    *) echo "remaster: unknown argument $1" >&2; exit 2 ;;
  esac
done

die() { echo "remaster: $*" >&2; exit 1; }
case "$edition" in "" | edu) ;; *) die "unknown edition: $edition (only edu exists)" ;; esac
# What the Education edition needs besides what ozios-edu itself ships.
if [ "$edition" = edu ]; then
  add="$add xournalpp okular kcalc kolourpaint plasma-keyboard libreoffice-still libreoffice-still-tr"
fi
step() { printf '\n==> %s (%s)\n' "$*" "$(date +%H:%M:%S)"; }

[ "$(id -u)" = 0 ] || die "run as root"
command -v xorriso >/dev/null || pacman -Sy --needed --noconfirm libisoburn
builder="${SUDO_USER:-liveuser}"
id "$builder" >/dev/null 2>&1 || die "no unprivileged user to build the package with (tried $builder)"

if [ -z "$work" ]; then
  mountpoint -q /mnt/build || die "no --work given and /mnt/build is not mounted"
  work=/mnt/build/remaster
fi
mkdir -p "$work"
work="$(readlink -f "$work")"
[ "$(findmnt -no FSTYPE -T "$work")" != overlay ] || die "$work is in RAM"

# Source medium: mounted already when we were booted from it.
mnt=/run/archiso/bootmnt
if [ -z "$src" ]; then
  mountpoint -q "$mnt" || die "not booted from a live ISO; pass --iso"
  src="$(findmnt -no SOURCE "$mnt")"
else
  mnt="$work/src"
  mkdir -p "$mnt"
  mountpoint -q "$mnt" || mount -o ro,loop "$src" "$mnt"
fi

image="$(find "$mnt" -maxdepth 4 \( -name 'airootfs.sfs' -o -name 'airootfs.erofs' \) | head -n1)"
[ -n "$image" ] || die "no airootfs image on $src"
inside="${image#"$mnt"}"
echo "source: $src"
echo "image:  $inside ($(du -h "$image" | cut -f1))"

root="$work/root"
cleanup() {
  for dir in var/cache/pacman/pkg run sys dev/pts dev proc; do
    mountpoint -q "$root/$dir" && umount -l "$root/$dir"
  done
  return 0
}
trap cleanup EXIT

step "Building the OziOS package"
rm -rf "$work/pkgbuild" "$work/makepkg" "$work/pkg"
mkdir -p "$work/pkgbuild" "$work/makepkg" "$work/pkg" "$work/pkgcache"
cp "$repo/packages/ozios-settings/PKGBUILD" "$repo/packages/ozios-settings/ozios-settings.install" "$work/pkgbuild/"
chown -R "$builder" "$work/pkgbuild" "$work/makepkg" "$work/pkg"
(cd "$work/pkgbuild" && sudo -u "$builder" env OZI_SRC="$repo" BUILDDIR="$work/makepkg" PKGDEST="$work/pkg" makepkg -f --nodeps)
package="$(find "$work/pkg" -name 'ozios-settings-*.pkg.tar.*' ! -name '*.sig' | head -n1)"
[ -n "$package" ] || die "makepkg produced nothing"
edu_package=""
if [ "$edition" = edu ]; then
  step "Building the Education package"
  rm -rf "$work/pkgbuild-edu"
  mkdir -p "$work/pkgbuild-edu"
  cp "$repo/packages/ozios-edu/PKGBUILD" "$repo/packages/ozios-edu/ozios-edu.install" "$work/pkgbuild-edu/"
  chown -R "$builder" "$work/pkgbuild-edu"
  (cd "$work/pkgbuild-edu" && sudo -u "$builder" env OZI_SRC="$repo" BUILDDIR="$work/makepkg" PKGDEST="$work/pkg" makepkg -f --nodeps)
  edu_package="$(find "$work/pkg" -name 'ozios-edu-*.pkg.tar.*' ! -name '*.sig' | head -n1)"
  [ -n "$edu_package" ] || die "makepkg produced no Education package"
fi

step "Unpacking the root image"
if $keep && [ -f "$root/etc/os-release" ]; then
  echo "reusing $root"
else
  rm -rf "$root"
  case "$image" in
    *.sfs)   unsquashfs -no-progress -d "$root" "$image" ;;
    *.erofs) mkdir -p "$root" && fsck.erofs --extract="$root" "$image" ;;
  esac
fi

step "Installing OziOS into it"
mount -t proc proc "$root/proc"
mount --rbind /dev "$root/dev" && mount --make-rslave "$root/dev"
mount -t sysfs sys "$root/sys"
mount -t tmpfs tmpfs "$root/run"
mount --bind "$work/pkgcache" "$root/var/cache/pacman/pkg"

# The image has no pacman keyring of its own (the live system creates one at
# boot), so verify with the keyring of the system we are running on.
pm=(pacman --root "$root" --gpgdir /etc/pacman.d/gnupg --cachedir "$work/pkgcache" --noconfirm)
if [ -n "$archive" ]; then
  cat > "$work/pacman-archive.conf" <<CONF
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Optional
ParallelDownloads = 3

[core]
Server = https://archive.archlinux.org/repos/$archive/\$repo/os/\$arch

[extra]
Server = https://archive.archlinux.org/repos/$archive/\$repo/os/\$arch

[multilib]
Server = https://archive.archlinux.org/repos/$archive/\$repo/os/\$arch
CONF
  pm+=(--config "$work/pacman-archive.conf")
fi
if [ -n "$add" ]; then
  # shellcheck disable=SC2086
  "${pm[@]}" -Sy --needed $add
  rm -rf "$root"/var/lib/pacman/sync/*
fi
"${pm[@]}" -U "$package" ${edu_package:+"$edu_package"}
rm -f "$root"/opt/ozios/ozios-settings-*.pkg.tar.* "$root"/opt/ozios/ozios-edu-*.pkg.tar.*
install -Dm644 "$package" "$root/opt/ozios/$(basename "$package")"
[ -z "$edu_package" ] || install -Dm644 "$edu_package" "$root/opt/ozios/$(basename "$edu_package")"
echo ozios > "$root/etc/hostname"

if [ "$edition" = edu ]; then
  step "Turkish defaults for the live session"
  sed -i 's/^#\(tr_TR.UTF-8\)/\1/' "$root/etc/locale.gen"
  chroot "$root" locale-gen
  echo 'LANG=tr_TR.UTF-8' > "$root/etc/locale.conf"
  echo 'KEYMAP=trq' > "$root/etc/vconsole.conf"
  ln -sf /usr/share/zoneinfo/Europe/Istanbul "$root/etc/localtime"
fi

step "Removing CachyOS programs and branding"
drop=()
for name in cachyos-hello cachyos-cli-installer-new cachy-chroot; do
  pacman --root "$root" -Qq "$name" >/dev/null 2>&1 && drop+=("$name")
done
[ "${#drop[@]}" -eq 0 ] || "${pm[@]}" -Rdd "${drop[@]}"
rm -f "$root/etc/skel/.config/autostart/cachyos-hello.desktop" \
      "$root/home/liveuser/.config/autostart/cachyos-hello.desktop" "$root/etc/cachyos-release"
cat > "$root/etc/motd" <<'MOTD'
Welcome to OziOS.

You are running from the install medium. Open the Welcome window to install it
on this computer, or look around first. Everything here is gone after a reboot.

  ozi status      what this system is running
  ozi --help      the everyday commands
MOTD
[ ! -f "$root/etc/skel/.config/alacritty/alacritty.toml" ] ||
  sed -i 's|^title = .*|title = "Alacritty@OziOS"|' "$root/etc/skel/.config/alacritty/alacritty.toml"

boot_maps=()
kernel_sed=()
if [ -n "$kernel" ]; then
  step "Swapping in the OziOS kernel"
  kernel="$(readlink -f "$kernel")"
  new_pkgs=()
  for name in linux-ozios linux-ozios-nvidia-open linux-ozios-zfs; do
    file="$(find "$kernel" -maxdepth 1 -name "$name-[0-9]*.pkg.tar.*" ! -name '*.sig' | head -n1)"
    if [ -n "$file" ]; then
      new_pkgs+=("$file")
    elif [ "$name" = linux-ozios ]; then
      die "no linux-ozios package in $kernel"
    else
      echo "note: no $name package; that module set will be missing"
    fi
  done
  # Every CachyOS kernel goes, the long-term one included: the image carries
  # one kernel, ours, and the fallback entries in the boot menu use it too.
  old_pkgs=()
  for name in linux-cachyos linux-cachyos-headers linux-cachyos-nvidia-open linux-cachyos-zfs \
              linux-cachyos-lts linux-cachyos-lts-headers linux-cachyos-lts-nvidia-open linux-cachyos-lts-zfs; do
    pacman --root "$root" -Qq "$name" >/dev/null 2>&1 && old_pkgs+=("$name")
  done
  [ "${#old_pkgs[@]}" -eq 0 ] || "${pm[@]}" -Rdd "${old_pkgs[@]}"
  "${pm[@]}" -U "${new_pkgs[@]}"
  # Keep the packages on the medium: the installer puts them into the new system.
  rm -f "$root"/opt/ozios/linux-ozios*.pkg.tar.*
  install -Dm644 -t "$root/opt/ozios" "${new_pkgs[@]}"

  kver="$(ls "$root/usr/lib/modules" | grep -- '-ozios$' | head -n1)"
  [ -n "$kver" ] || die "the kernel package installed no modules"
  echo "kernel release: $kver"

  # The live system's initramfs uses the archiso hooks, which the image
  # carries as a mkinitcpio drop-in; building it here follows the same rules.
  chroot "$root" mkinitcpio -k "$kver" -g /tmp/initramfs-linux-ozios.img
  mkdir -p "$work/boot"
  cp "$root/usr/lib/modules/$kver/vmlinuz" "$work/boot/vmlinuz-linux-ozios"
  mv "$root/tmp/initramfs-linux-ozios.img" "$work/boot/initramfs-linux-ozios.img"
  rm -f "$root"/boot/vmlinuz-linux-ozios "$root"/boot/initramfs-linux-ozios*.img

  bootdir="$(dirname "$(find "$mnt" -name 'vmlinuz-linux-cachyos' | head -n1)")"
  [ -d "$bootdir" ] || die "no vmlinuz-linux-cachyos on the source medium"
  bootdir="${bootdir#"$mnt"}"
  boot_maps+=(-rm "$bootdir/vmlinuz-linux-cachyos" "$bootdir/initramfs-linux-cachyos.img" \
                  "$bootdir/vmlinuz-linux-cachyos-lts" "$bootdir/initramfs-linux-cachyos-lts.img" --
              -map "$work/boot/vmlinuz-linux-ozios" "$bootdir/vmlinuz-linux-ozios"
              -map "$work/boot/initramfs-linux-ozios.img" "$bootdir/initramfs-linux-ozios.img")
  # Both CachyOS kernels give way to ours; the long-term kernel's own menu entry
  # becomes a duplicate and is dropped below.
  kernel_sed=(-e 's#(vmlinuz-linux)-cachyos(-lts)?([^-[:alnum:]]|$)#\1-ozios\3#g'
              -e 's#(initramfs-linux)-cachyos(-lts)?(\.img)#\1-ozios\3#g')
fi
cleanup

new="$work/$(basename "$image")"
if $keep && [ -s "$new" ] && [ "$new" -nt "$root/opt/ozios" ]; then
  step "Repacking skipped, reusing $new"
else
  step "Repacking"
  rm -f "$new"
  case "$image" in
    *.sfs)   mksquashfs "$root" "$new" -noappend -no-progress -comp zstd -Xcompression-level 10 -b 1M ;;
    *.erofs) mkfs.erofs -zzstd,15 -C 1048576 -E ztailpacking "$new" "$root" ;;
  esac
fi
echo "image: $(du -h "$new" | cut -f1)"

maps=(-map "$new" "$inside")
sum="${image%.*}.sha512"
if [ -f "$sum" ]; then
  (cd "$work" && sha512sum "$(basename "$new")" > "$work/airootfs.sha512")
  maps+=(-map "$work/airootfs.sha512" "${sum#"$mnt"}")
fi
[ ! -f "${image}.sig" ] || echo "remaster: note: the source image was signed; the new one is not" >&2

# Boot menu titles. Labels and kernel arguments stay as they are: the live
# system finds its medium through them.
mkdir -p "$work/cfg"
n=0
product=OziOS
[ "$edition" != edu ] || product="OziOS Education"
while IFS= read -r cfg; do
  if grep -qE '^[[:space:]]*(menuentry|submenu|title|MENU LABEL|MENU TITLE).*CachyOS' "$cfg" ||
     { [ -n "$kernel" ] && grep -qE 'linux-cachyos' "$cfg"; }; then
    n=$((n + 1))
    # The long-term kernel's own entry ("... LTS Kernel") would now start the same
    # kernel as the first one, so it is dropped.
    sed -E "${kernel_sed[@]}" -e '/^[[:space:]]*(menuentry|submenu|title|MENU LABEL|MENU TITLE)/ s/CachyOS/'"$product"'/g' "$cfg" |
      awk '/^menuentry .*LTS Kernel/ { skip = 1 } skip { if ($0 ~ /^}/) skip = 0; next } { print }' > "$work/cfg/$n"
    maps+=(-map "$work/cfg/$n" "${cfg#"$mnt"}")
  fi
done < <(find "$mnt" -maxdepth 5 -type f \( -name '*.cfg' -o -name '*.conf' \) -size -200k)
echo "boot menu files retitled: $n"

step "Writing the ISO"
version="$(tr -d '[:space:]' < "$repo/VERSION")"
name=ozios
[ "$edition" != edu ] || name=ozios-edu
out="$work/$name-$version-$(date +%y%m%d)-x86_64.iso"
rm -f "$out"
# The boot loaders look the medium up by its volume id, which is its creation
# time. A fresh timestamp would leave the new ISO unable to find itself.
uuid="$(blkid -o value -s UUID "$src" | tr -d '-')"
[ -n "$uuid" ] || die "could not read the volume id of $src"
# xorriso cannot open a drive that is mounted, so read a file copy of it.
source_iso="$src"
if [ -b "$src" ]; then
  source_iso="$work/source.iso"
  [ -s "$source_iso" ] || { echo "copying the source medium"; cat "$src" > "$source_iso"; }
fi
xorriso -indev "$source_iso" -outdev "$out" -boot_image any replay -volume_date uuid "$uuid" "${boot_maps[@]}" "${maps[@]}" -commit
(cd "$work" && sha256sum "$(basename "$out")" > "$out.sha256")

step "Done"
ls -lh "$out"
if [ -w "$repo" ]; then
  mkdir -p "$repo/out"
  cp "$out" "$out.sha256" "$repo/out/" && echo "copied to $repo/out/"
fi
