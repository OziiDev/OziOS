#!/usr/bin/env bash
# Inside a live session of an OziOS ISO, put the code of the checkout (the
# shared folder at /mnt/ozios) on top of what the ISO carries, so a change can
# be tried without building a new ISO. Run as root.
#
#   bash /mnt/ozios/tools/sync-live.sh
#
# Covers the Python tree, the apps, the helper scripts and the artwork, then
# applies the installer rewrite again. The changes last until the session ends.
set -eu
src="${1:-/mnt/ozios}"
[ -d "$src/python/ozipkg" ] || { echo "no checkout at $src" >&2; exit 2; }

cp -r "$src/python/ozipkg/." /usr/lib/ozios/python/ozipkg/
find /usr/lib/ozios/python -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
for f in identity patch-installer install-to-target first-login start-installer ozi-pkg-helper; do
  install -m755 "$src/packages/ozios-settings/$f" "/usr/lib/ozios/$f"
done
for f in ozi ozi-pkg ozi-box ozi-tools; do
  install -m755 "$src/packages/ozi-cli/$f" "/usr/bin/$f"
done
install -m755 "$src/tools/apply-branding.sh" /usr/share/ozios/tools/apply-branding.sh
cp -r "$src/apps/." /usr/lib/ozios/apps/
mkdir -p /usr/share/ozios/branding /usr/share/ozios/layouts
install -m644 "$src"/branding/boot/limine-splash.png "$src"/branding/boot/desktop.png /usr/share/ozios/branding/
install -m644 "$src"/desktop/layouts/*.js /usr/share/ozios/layouts/
[ ! -d "$src/edu/layouts" ] || install -m644 "$src"/edu/layouts/*.js /usr/share/ozios/layouts/
mkdir -p /usr/share/calamares/branding/ozios /usr/share/grub/themes/ozios
install -m644 "$src"/branding/calamares/ozios/{logo.png,icon.png,welcome.png,show.qml} /usr/share/calamares/branding/ozios/
install -m644 "$src"/branding/boot/theme.txt "$src"/branding/boot/background.png /usr/share/grub/themes/ozios/
install -m644 "$src/data/i18n/tr.json" /usr/share/ozios/data/i18n/tr.json
version="$(tr -d '[:space:]' < "$src/VERSION")"
sed "s/@VERSION@/$version/g" "$src/branding/calamares/ozios/branding.desc" > /usr/share/calamares/branding/ozios/branding.desc
/usr/lib/ozios/patch-installer
echo "live session now runs the checkout ($version)"
