#!/usr/bin/env bash
# Click through the Calamares installer in a VirtualBox guest with the keyboard,
# with the answers a test needs: erase the whole disk, default bootloader and
# desktop, user "tester". Start the installer in the guest first
# (/usr/local/bin/calamares-online.sh) and wait for its window.
#
#   tools/drive-calamares.sh <vm> [password]
#
# The guest keyboard is Turkish Q in the Education edition, where an "i" typed
# from here becomes a dotless one, so the name, host name and password avoid it.
# The window is Turkish when the live session is: Alt+S is "Sonraki" (Next),
# Alt+K is "Kur" (Install). In English they are Alt+N and Alt+I.
set -u
vm="${1:?usage: drive-calamares.sh <vm> [password]}"
password="${2:-Test1234!}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
keys() { bash "$here/vbkeys.sh" "$vm" "$@"; }
shot() { "${VBOXMANAGE:-/c/Program Files/Oracle/VirtualBox/VBoxManage.exe}" controlvm "$vm" screenshotpng "$1" >/dev/null 2>&1; }
out="${DRIVE_SHOTS:-$here/../.bridge}"

next="alt+s"; install="alt+k"
[ "${CALAMARES_LANG:-tr}" = en ] && { next="alt+n"; install="alt+i"; }

keys "$next"; sleep 6            # welcome -> location
keys "$next"; sleep 6            # location -> keyboard
keys "$next"; sleep 6            # keyboard -> bootloader
keys "$next"; sleep 10           # bootloader -> partitioning (scans the disks)
keys tab tab tab space; sleep 4  # "erase disk"
keys "$next"; sleep 6            # -> desktop
keys "$next"; sleep 6            # -> packages
keys "$next"; sleep 6            # -> user account
keys text:Tester tab ctrl+a text:tester tab ctrl+a text:osboxtest tab "text:$password" tab "text:$password"
sleep 2; shot "$out/drive-users.png"
keys "$next"; sleep 6            # -> summary
shot "$out/drive-summary.png"
keys "$install"; sleep 3         # confirmation dialog
keys enter; sleep 5
shot "$out/drive-started.png"
echo "installation started; screenshots in $out"
