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
  drop_block "$HOME/.bashrc"
  drop_block "$fish_rc"
  command -v plasma-apply-lookandfeel >/dev/null &&
    plasma-apply-lookandfeel -a org.kde.breezedark.desktop --resetLayout >/dev/null 2>&1
  rm -f "$conf/autostart/cachyos-hello.desktop"
  rm -f "$HOME/.local/bin/ozi-fetch" "$data/color-schemes/OziOS.colors" \
        "$data/konsole/OziOS.colorscheme" "$data/konsole/OziOS.profile"
  rm -rf "$data/ozios" "$data/plasma/look-and-feel/$theme" "$data/plasma/wallpapers/$wallpaper"
  kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile --delete
  for name in wobblywindows magiclamp squash blur; do
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
install -m644 "$src/konsole/OziOS.colorscheme" "$src/konsole/OziOS.profile" "$data/konsole/"
install -m644 "$src/logo.svg" "$src/wallpaper.svg" "$data/ozios/"
if [ -d "$root/desktop/look-and-feel/$theme" ]; then   # source checkout
  mkdir -p "$data/plasma/look-and-feel" "$data/plasma/wallpapers"
  rm -rf "$data/plasma/look-and-feel/$theme" "$data/plasma/wallpapers/$wallpaper"
  cp -r "$root/desktop/look-and-feel/$theme" "$data/plasma/look-and-feel/"
  cp -r "$root/desktop/wallpaper/$wallpaper" "$data/plasma/wallpapers/"
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
  case "$renderer" in *llvmpipe* | *softpipe* | *"Software Rasterizer"*) lite=true ;; esac
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

echo
echo "Done. Open a new Konsole window."
