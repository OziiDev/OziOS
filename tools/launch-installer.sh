#!/usr/bin/env bash
# Start the installer in a live session from outside the desktop, on an empty
# disk, and wait until its window is up. For tests that click through it
# (tools/drive-calamares.sh). Run as root in the live session:
#
#   bash /mnt/ozios/tools/launch-installer.sh [disk]
#
# An installer that is still running is stopped first and what it mounted is
# let go, so a failed run can simply be repeated. The disk is wiped.
set -u
disk="${1:-/dev/sda}"
log=/home/liveuser/cachy-install.log

pkill -x calamares 2>/dev/null
pkill -f pacstrap_calamares 2>/dev/null
pkill -x pacman 2>/dev/null
sleep 2
for root in /tmp/calamares-root-*; do
  [ -d "$root" ] && { umount -R "$root" 2>/dev/null || umount -Rl "$root" 2>/dev/null; }
done
wipefs -a "$disk"?* "$disk" >/dev/null 2>&1
sgdisk --zap-all "$disk" >/dev/null 2>&1
partprobe "$disk" 2>/dev/null
rm -f "$log"

# The installer needs the desktop session's environment; take it from the shell of the session.
pid="$(pgrep -u liveuser -x plasmashell | head -n 1)"
[ -n "$pid" ] || { echo "the desktop is not up yet" >&2; exit 1; }
tr '\0' '\n' < "/proc/$pid/environ" |
  grep -E '^(DISPLAY|WAYLAND_DISPLAY|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS|XDG_CURRENT_DESKTOP|XDG_SESSION_TYPE|KDE_SESSION_VERSION|XAUTHORITY|HOME)=' \
  > /tmp/session.env
# The welcome window keeps a software-rendered animation going and slows the keyboard down enough to lose keys.
pkill -u liveuser -f 'ozi-welcome' 2>/dev/null

setsid -f sudo -u liveuser env $(tr '\n' ' ' < /tmp/session.env) /usr/lib/ozios/start-installer \
  > /tmp/calaunch.log 2>&1 < /dev/null

# The last page is loaded some seconds before the window leaves its waiting screen.
for _ in $(seq 1 180); do
  if grep -q 'ViewModule "finished@finished" loading complete' "$log" 2>/dev/null; then
    sleep 20
    echo "installer ready"
    exit 0
  fi
  sleep 5
done
echo "the installer did not come up; see /tmp/calaunch.log" >&2
exit 1
