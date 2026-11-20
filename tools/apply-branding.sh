#!/usr/bin/env bash
# Apply the OziOS desktop to the current user. No root, no system files.
#
#   tools/apply-branding.sh          apply
#   tools/apply-branding.sh --undo   remove again
#
# Works both from a source checkout and from the installed package; from a
# checkout it first copies the desktop pieces into the user's data directory.
set -u

root="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
src="$root/branding"
data="${XDG_DATA_HOME:-$HOME/.local/share}"
conf="${XDG_CONFIG_HOME:-$HOME/.config}"
fish_rc="$conf/fish/config.fish"
begin="# >>> ozios >>>"
end="# <<< ozios <<<"
theme=org.ozios.desktop
wallpaper=org.ozios.tesseract
style=ozios                                  # the Plasma style: bar, dock and popup frames
motion=ozios_motion                          # the window open and close animation
applets="org.ozios.control org.ozios.dock org.ozios.launcher"
qdbus="$(command -v qdbus6 || command -v qdbus-qt6 || command -v qdbus || true)"

say() { printf '%-28s' "$1"; }

drop_block() {
  [ -f "$1" ] && sed -i "/^$begin\$/,/^$end\$/d" "$1"
}

kwin_effect() {  # kwin_effect <name> <true|false>
  kwriteconfig6 --file kwinrc --group Plugins --key "${1}Enabled" "$2"
  [ -n "$qdbus" ] || return 0
  local method=unloadEffect
  [ "$2" = true ] && method=loadEffect
  "$qdbus" org.kde.KWin /Effects "org.kde.kwin.Effects.$method" "$1" >/dev/null 2>&1
}

installed() {  # installed <kind> <id>: is this Plasma package available?
  [ -d "$data/plasma/$1/$2" ] || [ -d "/usr/share/plasma/$1/$2" ]
}

if [ "${1:-}" = "--undo" ]; then
  [ -x "$HOME/.local/bin/ozi-fetch" ] && "$HOME/.local/bin/ozi-fetch" --unpin >/dev/null 2>&1
  [ -f /usr/share/ozios/edu/apply-edu.sh ] && bash /usr/share/ozios/edu/apply-edu.sh --undo >/dev/null 2>&1
  drop_block "$HOME/.bashrc"
  drop_block "$fish_rc"
  command -v plasma-apply-lookandfeel >/dev/null &&
    plasma-apply-lookandfeel -a org.kde.breezedark.desktop --resetLayout >/dev/null 2>&1
  rm -f "$conf/autostart/cachyos-hello.desktop"
  command -v plasma-apply-desktoptheme >/dev/null && plasma-apply-desktoptheme default >/dev/null 2>&1
  rm -f "$HOME/.local/bin/ozi-fetch" "$data"/color-schemes/OziOS*.colors \
        "$data"/konsole/OziOS*.colorscheme "$data/konsole/OziOS.profile"
  rm -rf "$data/ozios" "$data/plasma/look-and-feel/$theme" "$data/plasma/wallpapers/$wallpaper" \
         "$data/plasma/desktoptheme/$style" "$data/kwin/effects/$motion"
  for applet in $applets; do rm -rf "$data/plasma/plasmoids/$applet"; done
  kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile --delete
  for name in wobblywindows magiclamp squash blur scale glide fade "$motion"; do
    kwriteconfig6 --file kwinrc --group Plugins --key "${name}Enabled" --delete
  done
  kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor --delete
  [ -n "$qdbus" ] && "$qdbus" org.kde.KWin /KWin reconfigure >/dev/null 2>&1
  echo "OziOS desktop removed."
  exit 0
fi

say "Copying files"
mkdir -p "$HOME/.local/bin" "$data/color-schemes" "$data/konsole" "$data/ozios"
install -m755 "$src/ozi-fetch" "$HOME/.local/bin/ozi-fetch"
install -m644 "$src/OziOS.colors" "$data/color-schemes/"
# The terminal colours of every theme; `ozi theme` points the profile at one of them.
install -m644 "$src"/konsole/*.colorscheme "$src/konsole/OziOS.profile" "$data/konsole/"
install -m644 "$src/logo.svg" "$src/wallpaper.svg" "$data/ozios/"
if [ -d "$root/desktop/look-and-feel/$theme" ]; then   # source checkout
  mkdir -p "$data/plasma/look-and-feel" "$data/plasma/wallpapers"
  rm -rf "$data/plasma/look-and-feel/$theme" "$data/plasma/wallpapers/$wallpaper"
  cp -r "$root/desktop/look-and-feel/$theme" "$data/plasma/look-and-feel/"
  cp -r "$root/desktop/wallpaper/$wallpaper" "$data/plasma/wallpapers/"
  mkdir -p "$data/plasma/plasmoids" "$data/plasma/desktoptheme" "$data/kwin/effects"
  for applet in $applets; do
    rm -rf "$data/plasma/plasmoids/$applet"
    cp -r "$root/desktop/plasmoids/$applet" "$data/plasma/plasmoids/"
  done
  rm -rf "$data/plasma/desktoptheme/$style" "$data/kwin/effects/$motion"
  cp -r "$root/desktop/plasma-style/$style" "$data/plasma/desktoptheme/"
  cp -r "$root/desktop/kwin/effects/$motion" "$data/kwin/effects/"
  install -m644 "$src"/themes/*.colors "$data/color-schemes/"
  # The splash screen reuses the wallpaper's figure.
  cp "$root/desktop/wallpaper/$wallpaper/contents/ui/Tesseract.qml" \
     "$data/plasma/look-and-feel/$theme/contents/splash/"
fi
echo ok

# Software rendering can not afford blur, wobble or a moving wallpaper.
# OZI_EFFECTS=lite|full overrides the guess.
lite=false
if [ -n "$qdbus" ]; then
  renderer="$("$qdbus" org.kde.KWin /KWin org.kde.KWin.supportInformation 2>/dev/null | grep -i 'OpenGL renderer' || true)"
  # SVGA3D is the graphics card of a VirtualBox or VMware guest: it draws, but slowly.
  case "$renderer" in *llvmpipe* | *softpipe* | *"Software Rasterizer"* | *SVGA3D*) lite=true ;; esac
fi
case "${OZI_EFFECTS:-}" in lite) lite=true ;; full) lite=false ;; esac

# The global theme carries colours, splash screen, panel layout and wallpaper.
say "Desktop theme"
if installed look-and-feel "$theme" && command -v plasma-apply-lookandfeel >/dev/null; then
  plasma-apply-lookandfeel -a "$theme" --resetLayout >/dev/null 2>&1 && echo ok || echo failed
else
  echo "colours only"
fi
# The theme's own defaults do not always carry the colour scheme over.
command -v plasma-apply-colorscheme >/dev/null && plasma-apply-colorscheme OziOS >/dev/null 2>&1

# The frames of the bar, the dock and every popup; they take the colour scheme's colours.
say "Plasma style"
if command -v plasma-apply-desktoptheme >/dev/null && { [ -d "$data/plasma/desktoptheme/$style" ] || [ -d "/usr/share/plasma/desktoptheme/$style" ]; }; then
  plasma-apply-desktoptheme "$style" >/dev/null 2>&1 && echo ok || echo failed
else
  echo skipped
fi

say "Wallpaper"
if $lite || ! installed wallpapers "$wallpaper"; then
  plasma-apply-wallpaperimage "$data/ozios/wallpaper.svg" >/dev/null 2>&1 && echo "still" || echo failed
elif [ -n "$qdbus" ]; then
  "$qdbus" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
    "for (const d of desktops()) { d.wallpaperPlugin = '$wallpaper'; }" >/dev/null 2>&1 && echo animated || echo failed
else
  echo skipped
fi

say "Konsole profile"
kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile OziOS.profile && echo ok

# Pinned header where the terminal allows it, plain greeting otherwise.
say "Shell greeting"
drop_block "$HOME/.bashrc"
drop_block "$fish_rc"
cat >> "$HOME/.bashrc" <<EOF
$begin
case ":\$PATH:" in *":\$HOME/.local/bin:"*) ;; *) PATH="\$HOME/.local/bin:\$PATH" ;; esac
case \$- in *i*) command -v ozi-fetch >/dev/null && { ozi-fetch --pin || ozi-fetch; } ;; esac
$end
EOF
if command -v fish >/dev/null; then
  mkdir -p "$conf/fish"
  cat >> "$fish_rc" <<EOF
$begin
fish_add_path -g \$HOME/.local/bin
function fish_greeting
    command -q ozi-fetch; or return
    ozi-fetch --pin; or ozi-fetch
end
$end
EOF
fi
echo ok

# OziOS has its own welcome app; keep the CachyOS one from opening beside it.
say "Welcome app"
mkdir -p "$conf/autostart"
printf '[Desktop Entry]\nType=Application\nName=CachyOS Hello\nHidden=true\n' > "$conf/autostart/cachyos-hello.desktop"
echo ok

say "Window effects"
kwin_effect squash false   # replaced by magic lamp; the two conflict
kwin_effect magiclamp true
# Windows open and close with the OziOS motion; KWin's own animations of that kind step aside.
for name in scale glide fade; do kwin_effect "$name" false; done
kwin_effect "$motion" true
if $lite; then
  kwin_effect wobblywindows false
  kwin_effect blur false
  kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0.5
else
  kwin_effect wobblywindows true
  kwin_effect blur true
  kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0.7
fi
[ -n "$qdbus" ] && "$qdbus" org.kde.KWin /KWin reconfigure >/dev/null 2>&1
$lite && echo "ok (light)" || echo ok

# The Education edition adds its own desktop on top: board layout, school defaults.
if [ "$(cat /usr/share/ozios/edition 2>/dev/null)" = edu ] && [ -f /usr/share/ozios/edu/apply-edu.sh ]; then
  say "Education desktop"
  bash /usr/share/ozios/edu/apply-edu.sh >/dev/null 2>&1 && echo ok || echo failed
fi

echo
echo "Done. Open a new Konsole window."
