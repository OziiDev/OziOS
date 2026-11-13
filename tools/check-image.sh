#!/usr/bin/env bash
# Check a running OziOS live image for what should and should not be in it.
# Prints one line per check and exits non-zero if any failed.
#
#   bash tools/check-image.sh [edu]
set -u
fail=0
edition="${1:-}"

ok()   { printf 'ok    %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fail=1; }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }

check "runs the OziOS kernel" 'uname -r | grep -q ozios'
check "no CachyOS kernel package" '! pacman -Qq 2>/dev/null | grep -q "^linux-cachyos"'
check "no CachyOS Hello, CLI installer or cachy-chroot" '! pacman -Qq 2>/dev/null | grep -qE "^(cachyos-hello|cachyos-cli-installer-new|cachy-chroot)$"'
check "os-release names OziOS" 'grep -q "^NAME=\"OziOS\"" /etc/os-release'
check "os-release points to this project" 'grep -q "^HOME_URL=\"https://github.com/OziiDev/OziOS\"" /etc/os-release'
check "no CachyOS URLs in os-release" '! grep -qi "cachyos.org" /etc/os-release'
check "the motd is ours" 'grep -q "^Welcome to OziOS" /etc/motd && ! grep -qi cachyos /etc/motd'
check "no CachyOS kernel files on the medium" '! ls /run/archiso/bootmnt/arch/boot/x86_64 | grep -q cachyos'
check "the boot menus start no CachyOS kernel" '! grep -rIl "linux-cachyos" /run/archiso/bootmnt --include=*.cfg --include=*.conf | grep -q .'
check "the boot menus have no LTS entry" '! grep -rIq "LTS Kernel" /run/archiso/bootmnt/boot/grub'
# The live launcher copies settings_online.conf over the installer's settings.
check "installer branding is OziOS" 'grep -q "^branding: ozios" /usr/share/calamares/settings_online.conf'
check "installer has the early and late OziOS steps" 'grep -q "shellprocess@ozios_early" /usr/share/calamares/settings_online.conf && grep -q "shellprocess@ozios$" /usr/share/calamares/settings_online.conf'
check "installer package list has no CachyOS kernels" '! grep -q "linux-cachyos" /etc/calamares/modules/netinstall.yaml'
check "installer uses only the local package list" '! grep -q "https://" /etc/calamares/modules/netinstall.conf'
check "installer branding files are installed" 'test -f /usr/share/calamares/branding/ozios/branding.desc && test -f /usr/share/calamares/branding/ozios/logo.png'
check "GRUB theme and boot splash are installed" 'test -f /usr/share/grub/themes/ozios/theme.txt && test -f /usr/share/ozios/branding/limine-splash.png'
check "boot loader entry is named ozios" 'grep -q "efiBootloaderId: \"ozios\"" /etc/calamares/modules/bootloader.conf'
check "host name template is ozios" 'grep -q "ozios-" /etc/calamares/modules/users.conf'
check "the alpm hook sorts after CachyOS's" 'test -f /usr/share/libalpm/hooks/zz-ozios.hook'
check "OziOS Welcome offers the installer" 'python3 -c "import sys; sys.path.insert(0,\"/usr/lib/ozios/python\"); from ozipkg import welcome; sys.exit(0 if welcome.info()[\"live\"] else 1)"'
check "CachyOS Hello is not running" '! pgrep -f cachyos-hello'

if [ "$edition" = edu ]; then
  check "edition marker says edu" 'test "$(cat /usr/share/ozios/edition)" = edu'
  check "os-release names the variant" 'grep -q "^VARIANT_ID=edu" /etc/os-release'
  check "the screen pen is installed" 'test -x /usr/bin/ozi-pen'
  check "the board layout is installed" 'test -f /usr/share/ozios/layouts/board.js'
  check "school programs are installed" 'pacman -Qq xournalpp okular kcalc maliit-keyboard libreoffice-still libreoffice-still-tr'
  check "the live session is Turkish" 'grep -q "tr_TR" /etc/locale.conf'
  check "school links are in the menu" 'test -f /usr/share/applications/ozi-eba.desktop'
else
  check "no Education edition marker" '! test -f /usr/share/ozios/edition'
fi
exit "$fail"
