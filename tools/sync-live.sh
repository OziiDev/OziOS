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
for f in identity patch-installer install-to-target first-login start-installer ozi-pkg-helper tidy-menu retry-download; do
  install -m755 "$src/packages/ozios-settings/$f" "/usr/lib/ozios/$f"
done
install -Dm644 "$src/packages/ozios-settings/zz-ozios-menu.hook" /usr/share/libalpm/hooks/zz-ozios-menu.hook
install -Dm644 "$src/packages/ozios-settings/60-ozios-animations.conf" /usr/lib/environment.d/60-ozios-animations.conf
install -m644 "$src/winbridge/ozi-winrun.desktop" /usr/share/applications/ozi-winrun.desktop
/usr/lib/ozios/tidy-menu
for f in ozi ozi-pkg ozi-box ozi-tools; do
  install -m755 "$src/packages/ozi-cli/$f" "/usr/bin/$f"
done
install -m755 "$src/tools/apply-branding.sh" /usr/share/ozios/tools/apply-branding.sh
# The OziOS apps' commands and menu entries; Meta+K comes from ozi-keys.desktop.
for app in ozi-store ozi-welcome ozi-look; do
  ln -sf "/usr/lib/ozios/apps/$app/$app" "/usr/bin/$app"
  install -m644 "$src/apps/$app.desktop" /usr/share/applications/
done
install -m644 "$src/apps/ozi-keys.desktop" /usr/share/applications/
cp -r "$src/apps/." /usr/lib/ozios/apps/
mkdir -p /usr/share/ozios/branding /usr/share/ozios/layouts
install -m644 "$src"/branding/boot/limine-splash.png "$src"/branding/boot/desktop.png /usr/share/ozios/branding/
install -m644 "$src"/desktop/layouts/*.js /usr/share/ozios/layouts/
[ ! -d "$src/edu/layouts" ] || install -m644 "$src"/edu/layouts/*.js /usr/share/ozios/layouts/

# The OziOS shell: dock, launcher, control widget, desktops, clock, wallpaper, Plasma style,
# window motion, colour themes.
for applet in org.ozios.clock org.ozios.control org.ozios.dock org.ozios.launcher org.ozios.workspaces; do
  rm -rf "/usr/share/plasma/plasmoids/$applet"
  cp -r "$src/desktop/plasmoids/$applet" /usr/share/plasma/plasmoids/
done
rm -rf /usr/share/plasma/wallpapers/org.ozios.tesseract /usr/share/plasma/desktoptheme/ozios /usr/share/kwin-wayland/effects/ozios_*
cp -r "$src/desktop/wallpaper/org.ozios.tesseract" /usr/share/plasma/wallpapers/
mkdir -p /usr/share/plasma/desktoptheme /usr/share/kwin-wayland/effects
cp -r "$src/desktop/plasma-style/ozios" /usr/share/plasma/desktoptheme/
cp -r "$src"/desktop/kwin/effects/ozios_* /usr/share/kwin-wayland/effects/
rm -rf /usr/share/kwin-wayland/tabbox/org.ozios.switcher && mkdir -p /usr/share/kwin-wayland/tabbox
cp -r "$src/desktop/kwin/tabbox/org.ozios.switcher" /usr/share/kwin-wayland/tabbox/
rm -rf /usr/share/kwin-wayland/scripts/ozios-tiling && mkdir -p /usr/share/kwin-wayland/scripts
cp -r "$src/desktop/kwin/scripts/ozios-tiling" /usr/share/kwin-wayland/scripts/
install -m644 "$src"/branding/konsole/*.colorscheme /usr/share/konsole/
install -m644 "$src/branding/OziOS.colors" "$src"/branding/themes/*.colors /usr/share/color-schemes/
lnf=/usr/share/plasma/look-and-feel/org.ozios.desktop
if [ -d "$lnf" ]; then
  install -m644 "$src/desktop/look-and-feel/org.ozios.desktop/contents/defaults" "$lnf/contents/defaults"
  install -m644 "$src"/desktop/look-and-feel/org.ozios.desktop/contents/layouts/*.js "$lnf/contents/layouts/"
  install -Dm644 -t "$lnf/contents/logout" "$src"/desktop/look-and-feel/org.ozios.desktop/contents/logout/*.qml \
    "$src/desktop/look-and-feel/org.ozios.desktop/contents/logout/keys.js"
fi
# The same screen for the logout greeter of Plasma 6.8 and later, in a shell package.
shell=/usr/share/plasma/shells/org.ozios.desktop
install -Dm644 "$src/desktop/shell/org.ozios.desktop/metadata.json" "$shell/metadata.json"
install -Dm644 -t "$shell/contents/logout" "$src"/desktop/look-and-feel/org.ozios.desktop/contents/logout/*.qml \
  "$src/desktop/look-and-feel/org.ozios.desktop/contents/logout/keys.js"
chmod -R go+rX,go-w "$shell"
mkdir -p /usr/share/calamares/branding/ozios /usr/share/grub/themes/ozios
install -m644 "$src"/branding/calamares/ozios/{logo.png,icon.png,welcome.png,show.qml,OziSlide.qml} /usr/share/calamares/branding/ozios/
install -m644 "$src"/branding/boot/theme.txt "$src"/branding/boot/background.png /usr/share/grub/themes/ozios/
install -m644 "$src/data/i18n/tr.json" /usr/share/ozios/data/i18n/tr.json
mkdir -p /etc/plasmalogin.conf.d && install -m644 "$src/branding/login/10-ozios.conf" /etc/plasmalogin.conf.d/10-ozios.conf
install -m644 "$src/desktop/defaults/ksplashrc" "$src/desktop/defaults/kscreenlockerrc" /etc/xdg/
version="$(tr -d '[:space:]' < "$src/VERSION")"
sed "s/@VERSION@/$version/g" "$src/branding/calamares/ozios/branding.desc" > /usr/share/calamares/branding/ozios/branding.desc
# A VirtualBox shared folder hands out its files as rwxrwx--- and cp keeps that, so
# new files would be readable by root only: the desktop could not load them.
chmod -R go+rX,go-w /usr/lib/ozios/python/ozipkg /usr/lib/ozios/apps \
  /usr/share/plasma/plasmoids/org.ozios.* /usr/share/plasma/wallpapers/org.ozios.tesseract \
  /usr/share/plasma/desktoptheme/ozios /usr/share/kwin-wayland/effects/ozios_* \
  /usr/share/kwin-wayland/tabbox/org.ozios.switcher /usr/share/kwin-wayland/scripts/ozios-tiling
/usr/lib/ozios/patch-installer
echo "live session now runs the checkout ($version)"
