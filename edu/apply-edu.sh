#!/usr/bin/env bash
# Set up the OziOS Education desktop for the current user: board layout,
# Turkish keyboard and language, an on-screen keyboard, large cursor, and no
# screen lock or sleep during a lesson. No root, no system files.
#
#   apply-edu.sh          apply
#   apply-edu.sh --undo   take the settings out again
set -u

kw() {  # kw <file> <group> <key> <value>
  kwriteconfig6 --file "$1" --group "$2" --key "$3" "$4"
}
kw2() {  # kw2 <file> <group> <subgroup> <key> <value>
  kwriteconfig6 --file "$1" --group "$2" --group "$3" --key "$4" "$5"
}
qdbus="$(command -v qdbus6 || command -v qdbus-qt6 || command -v qdbus || true)"

if [ "${1:-}" = "--undo" ]; then
  kwriteconfig6 --file kcminputrc --group Mouse --key cursorSize --delete
  kwriteconfig6 --file kscreenlockerrc --group Daemon --key Autolock --delete
  kwriteconfig6 --file kscreenlockerrc --group Daemon --key LockOnResume --delete
  kwriteconfig6 --file kwinrc --group Wayland --key InputMethod --delete
  kwriteconfig6 --file plasma-localerc --group Formats --key LANG --delete
  kwriteconfig6 --file plasma-localerc --group Translations --key LANGUAGE --delete
  for profile in AC Battery LowBattery; do
    kwriteconfig6 --file powerdevilrc --group "$profile" --group SuspendAndShutdown --key AutoSuspendAction --delete
    kwriteconfig6 --file powerdevilrc --group "$profile" --group Display --key DimDisplayWhenIdle --delete
    kwriteconfig6 --file powerdevilrc --group "$profile" --group Display --key TurnOffDisplayWhenIdle --delete
  done
  command -v ozi >/dev/null && ozi layout default
  echo "Education settings removed."
  exit 0
fi

# Turkish keyboard and language, the way the schools use them.
kw kxkbrc Layout Use true
kw kxkbrc Layout LayoutList tr
kw plasma-localerc Formats LANG tr_TR.UTF-8
kw plasma-localerc Translations LANGUAGE tr

# Big targets for fingers and a pen.
kw kcminputrc Mouse cursorSize 36

# A board must not lock or sleep in the middle of a lesson.
kw kscreenlockerrc Daemon Autolock false
kw kscreenlockerrc Daemon LockOnResume false
for profile in AC Battery LowBattery; do
  kw2 powerdevilrc "$profile" SuspendAndShutdown AutoSuspendAction 0
  kw2 powerdevilrc "$profile" Display DimDisplayWhenIdle false
  kw2 powerdevilrc "$profile" Display TurnOffDisplayWhenIdle false
done

# The on-screen keyboard that comes up when a text field is touched.
desktop=/usr/share/applications/org.kde.plasma.keyboard.desktop
if [ -f "$desktop" ]; then
  kw kwinrc Wayland InputMethod "$desktop"
fi

# The board layout last: it replaces the panels.
if command -v ozi >/dev/null; then
  ozi layout board || echo "apply-edu: the board layout needs a running desktop session"
fi
[ -n "$qdbus" ] && "$qdbus" org.kde.KWin /KWin reconfigure >/dev/null 2>&1
echo "Education settings applied. Log out and in again for the keyboard and cursor."
