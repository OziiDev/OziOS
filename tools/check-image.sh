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
check "installer puts the kernel in before the driver step" 'awk "/- pacstrap\$/{p=NR} /shellprocess@ozios_kernel\$/{k=NR} /- chwd\$/{c=NR} END{exit !(p && k==p+1 && c>k)}" /usr/share/calamares/settings_online.conf'
check "installer's driver step does not stop the installation" 'grep -q "ozios_chwd_failed" /usr/lib/calamares/modules/chwd/main.py'
check "installer package list has no CachyOS kernels" '! grep -q "linux-cachyos" /etc/calamares/modules/netinstall.yaml'
check "installer uses only the local package list" '! grep -q "https://" /etc/calamares/modules/netinstall.conf'
check "installer's base system adds no CachyOS kernel or theme" '! grep -qE "\"(linux-cachyos|cachyos-grub-theme)" /usr/lib/calamares/modules/pacstrap/main.py'
check "installer does not offer ZFS as a root file system" '! grep -q "^ *availableFileSystemTypes:.*zfs" /etc/calamares/modules/partition.conf'
check "installer branding files are installed" 'test -f /usr/share/calamares/branding/ozios/branding.desc && test -f /usr/share/calamares/branding/ozios/logo.png'
check "GRUB theme and boot splash are installed" 'test -f /usr/share/grub/themes/ozios/theme.txt && test -f /usr/share/ozios/branding/limine-splash.png'
check "boot loader entry is named ozios" 'grep -q "efiBootloaderId: \"ozios\"" /etc/calamares/modules/bootloader.conf'
check "host name template is ozios" 'grep -q "ozios-" /etc/calamares/modules/users.conf'
check "the alpm hook sorts after CachyOS's" 'test -f /usr/share/libalpm/hooks/zz-ozios.hook'
check "OziOS Welcome offers the installer" 'python3 -c "import sys; sys.path.insert(0,\"/usr/lib/ozios/python\"); from ozipkg import welcome; sys.exit(0 if welcome.info()[\"live\"] else 1)"'
check "CachyOS Hello is not running" '! pgrep -f cachyos-hello'

# The OziOS shell.
check "the dock and the launcher are installed" 'test -f /usr/share/plasma/plasmoids/org.ozios.dock/contents/ui/DockItem.qml && test -f /usr/share/plasma/plasmoids/org.ozios.launcher/contents/ui/AppTile.qml'
check "the OziOS Plasma style is installed" 'test -f /usr/share/plasma/desktoptheme/ozios/widgets/panel-background.svg && test -f /usr/share/plasma/desktoptheme/ozios/translucent/dialogs/background.svg'
check "the window motion is installed" 'test -f /usr/share/kwin/effects/ozios_motion/contents/code/main.js'
check "every colour theme is installed" 'for s in OziOS OziOSAurora OziOSEmber OziOSMint OziOSRose OziOSFrost; do test -f /usr/share/color-schemes/$s.colors && test -f /usr/share/konsole/$s.colorscheme || exit 1; done'
check "the boot splash and the day and night timer are installed" 'test -f /usr/share/plymouth/themes/ozios/ozios.plymouth && test -f /usr/lib/systemd/user/ozios-theme-auto.timer'
check "file search does not read every document" 'grep -q "only basic indexing=true" /etc/xdg/baloofilerc'
# In the live session itself, once the first login has applied the desktop:
if [ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]; then
  check "this session uses the OziOS Plasma style" 'test "$(kreadconfig6 --file plasmarc --group Theme --key name)" = ozios'
  check "this session uses the OziOS window motion" 'test "$(kreadconfig6 --file kwinrc --group Plugins --key ozios_motionEnabled)" = true'
  check "the panels hold the OziOS dock and launcher" 'grep -q "plugin=org.ozios.dock" ~/.config/plasma-org.kde.plasma.desktop-appletsrc && grep -q "plugin=org.ozios.launcher" ~/.config/plasma-org.kde.plasma.desktop-appletsrc'
  check "plasmashell reported no QML errors for OziOS" '! journalctl --user -b --no-pager 2>/dev/null | grep -i "org.ozios" | grep -qiE "error|unavailable|is not a type|cannot assign"'
fi

if [ "$edition" = edu ]; then
  check "edition marker says edu" 'test "$(cat /usr/share/ozios/edition)" = edu'
  check "os-release names the variant" 'grep -q "^VARIANT_ID=edu" /etc/os-release'
  check "the screen pen is installed" 'test -x /usr/bin/ozi-pen'
  check "the classroom app is installed" 'test -x /usr/bin/ozi-classroom'
  check "the board layout is installed" 'test -f /usr/share/ozios/layouts/board.js'
  check "school programs are installed" 'pacman -Qq xournalpp okular kcalc plasma-keyboard libreoffice-still libreoffice-still-tr'
  check "the live session is Turkish" 'grep -q "tr_TR" /etc/locale.conf'
  check "school links are in the menu" 'test -f /usr/share/applications/ozi-eba.desktop'
else
  check "no Education edition marker" '! test -f /usr/share/ozios/edition'
fi
exit "$fail"
