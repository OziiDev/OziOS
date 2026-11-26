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
effects_ours="ozios_motion ozios_morph ozios_minimize"   # opening and closing, flowing to a new place, minimising
decoration=org.ozios.decoration              # the window frames (a compiled KWin plugin)
switcher=org.ozios.switcher                  # the Alt+Tab window switcher
applets="org.ozios.clock org.ozios.control org.ozios.dock org.ozios.launcher org.ozios.workspaces"
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

# shortcut <component> <action> [key...]: give a global shortcut its keys now and for
# good; no key clears it. Keys are Qt's numbers: Meta 0x10000000, Ctrl 0x04000000,
# a digit its ASCII code, F1 0x01000030. A key another action holds is not taken.
shortcut() {
  local component="$1" action="$2" spec="" key
  shift 2
  for key in "$@"; do spec="$spec 4 $key 0 0 0"; done
  command -v busctl >/dev/null || return 0
  # shellcheck disable=SC2086
  busctl --user call org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel setForeignShortcutKeys     "asa(ai)" 4 "$component" "$action" "$component" "$action" $# $spec >/dev/null 2>&1
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
  # The logout greeter back to Plasma's own screen.
  rm -f "$data/dbus-1/services/org.kde.LogoutPrompt.service"
  command -v busctl >/dev/null &&
    busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null 2>&1
  command -v plasma-apply-desktoptheme >/dev/null && plasma-apply-desktoptheme default >/dev/null 2>&1
  rm -f "$HOME/.local/bin/ozi-fetch" "$data"/color-schemes/OziOS*.colors \
        "$data"/konsole/OziOS*.colorscheme "$data/konsole/OziOS.profile"
  rm -rf "$data/ozios" "$data/plasma/look-and-feel/$theme" "$data/plasma/wallpapers/$wallpaper" \
         "$data/plasma/desktoptheme/$style" "$data/kwin-wayland/effects/$motion" "$data/kwin-wayland/tabbox/$switcher" \
         "$data/kwin-wayland/scripts/ozios-tiling"
  for applet in $applets; do rm -rf "$data/plasma/plasmoids/$applet"; done
  kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile --delete
  for name in wobblywindows magiclamp squash maximize blur scale glide fade $effects_ours; do
    kwriteconfig6 --file kwinrc --group Plugins --key "${name}Enabled" --delete
  done
  for key in library theme BorderSize BorderSizeAuto ButtonsOnLeft ButtonsOnRight; do
    kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key "$key" --delete
  done
  kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor --delete
  kwriteconfig6 --file kwinrc --group TabBox --key LayoutName --delete
  # Tiling off, and Meta+T back to KWin's tile editor.
  kwriteconfig6 --file kwinrc --group Plugins --key ozios-tilingEnabled --delete
  for key in TextOn TextOff TileByDefault Gap OuterGap; do
    kwriteconfig6 --file kwinrc --group Script-ozios-tiling --key "$key" --delete
  done
  shortcut kwin "OziOS Tiling Toggle"
  shortcut kwin "OziOS Tiling Float"
  shortcut kwin "Edit Tiles" $((0x10000054))
  # Meta+Q back to the activity switcher, Meta+Enter off the terminal.
  shortcut kwin "Window Close" $((0x09000033))
  shortcut plasmashell "manage activities" $((0x10000051))
  shortcut org.kde.konsole.desktop _launch $((0x0C000054))
  # Meta and a number back to the task manager; the desktops keep Ctrl+F1 and Meta+F1.
  for n in 1 2 3 4; do
    shortcut kwin "Window to Desktop $n"
    shortcut kwin "Switch to Desktop $n" $((0x0500002F + n)) $((0x1100002F + n))
    shortcut plasmashell "activate task manager entry $n" $((0x10000030 + n))
  done
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
  mkdir -p "$data/plasma/plasmoids" "$data/plasma/desktoptheme" "$data/kwin-wayland/effects"
  for applet in $applets; do
    rm -rf "$data/plasma/plasmoids/$applet"
    cp -r "$root/desktop/plasmoids/$applet" "$data/plasma/plasmoids/"
  done
  rm -rf "$data/plasma/desktoptheme/$style"
  cp -r "$root/desktop/plasma-style/$style" "$data/plasma/desktoptheme/"
  for name in $effects_ours; do
    rm -rf "$data/kwin-wayland/effects/$name"
    cp -r "$root/desktop/kwin/effects/$name" "$data/kwin-wayland/effects/"
  done
  mkdir -p "$data/kwin-wayland/tabbox" && rm -rf "$data/kwin-wayland/tabbox/$switcher"
  cp -r "$root/desktop/kwin/tabbox/$switcher" "$data/kwin-wayland/tabbox/"
  mkdir -p "$data/kwin-wayland/scripts" && rm -rf "$data/kwin-wayland/scripts/ozios-tiling"
  cp -r "$root/desktop/kwin/scripts/ozios-tiling" "$data/kwin-wayland/scripts/"
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

# The rest talks to Plasma, which may still be starting on the first login.
if [ -n "$qdbus" ]; then
  for _ in $(seq 1 30); do
    "$qdbus" org.kde.plasmashell /PlasmaShell >/dev/null 2>&1 && break
    sleep 1
  done
fi

# The global theme carries colours, splash screen, panel layout and wallpaper.
say "Desktop theme"
if installed look-and-feel "$theme" && command -v plasma-apply-lookandfeel >/dev/null; then
  plasma-apply-lookandfeel -a "$theme" --resetLayout >/dev/null 2>&1 && echo ok || echo failed
else
  echo "colours only"
fi
# The theme's own defaults do not always carry the colour scheme over.
command -v plasma-apply-colorscheme >/dev/null && plasma-apply-colorscheme OziOS >/dev/null 2>&1

# The screen to log out, restart or shut down. Up to Plasma 6.7 the logout greeter takes
# it from the global theme above; from 6.8 on from a shell package, the one that
# PLASMA_DEFAULT_SHELL names. D-Bus starts the greeter, and a service file of one's own
# comes before the system's: this one names the OziOS shell package, which holds only that
# screen, to the greeter alone, so the desktop itself stays Plasma's. Should Plasma reject
# the screen, the greeter shows its own; without the package it starts as it always did.
say "Logout screen"
greeter_service="$data/dbus-1/services/org.kde.LogoutPrompt.service"
if [ -x /usr/lib/ksmserver-logout-greeter ]; then
  mkdir -p "$(dirname "$greeter_service")"
  cat > "$greeter_service" <<'EOF'
[D-BUS Service]
Name=org.kde.LogoutPrompt
Exec=/bin/sh -c "[ -f /usr/share/plasma/shells/org.ozios.desktop/contents/logout/Logout.qml ] && export PLASMA_DEFAULT_SHELL=org.ozios.desktop; exec /usr/lib/ksmserver-logout-greeter"
EOF
  # The session bus reads service files when it starts; this has it read them now.
  command -v busctl >/dev/null &&
    busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus ReloadConfig >/dev/null 2>&1
  echo ok
else
  echo skipped
fi

# The frames of the bar, the dock and every popup; they take the colour scheme's colours.
say "Plasma style"
if command -v plasma-apply-desktoptheme >/dev/null && { [ -d "$data/plasma/desktoptheme/$style" ] || [ -d "/usr/share/plasma/desktoptheme/$style" ]; }; then
  plasma-apply-desktoptheme "$style" >/dev/null 2>&1 && echo ok || echo failed
else
  echo skipped
fi

# The same wallpaper everywhere; in the light profile it holds still, because a
# computer drawing in software spends a processor core on every moving frame.
say "Wallpaper"
animated=true
$lite && animated=false
if ! installed wallpapers "$wallpaper"; then
  plasma-apply-wallpaperimage "$data/ozios/wallpaper.svg" >/dev/null 2>&1 && echo "picture" || echo failed
elif [ -n "$qdbus" ]; then
  sleep 2   # a reset layout needs a moment to put its desktops on the screens
  "$qdbus" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
    "for (const d of desktops()) { d.wallpaperPlugin = '$wallpaper'; d.currentConfigGroup = ['Wallpaper', '$wallpaper', 'General']; d.writeConfig('Animated', $animated); }" \
    >/dev/null 2>&1 && { $animated && echo animated || echo still; } || echo failed
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

# Rounded windows with an outline in the accent colour; KWin falls back to Breeze
# by itself if the plugin can not be loaded.
say "Window frames"
if [ -f "/usr/lib/qt6/plugins/org.kde.kdecoration3/$decoration.so" ]; then
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library "$decoration"
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme ""
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key BorderSize None
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key BorderSizeAuto false
  # No program menu on the left; minimise, maximise and close on the right.
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnLeft ""
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnRight IAX
  echo ok
else
  echo "Breeze (OziOS frames not installed)"
fi

say "Window effects"
# OziOS's own motion: windows open and close, minimise into the dock and flow to a
# new place or size; KWin's animations of the same kinds step aside.
for name in scale glide fade; do kwin_effect "$name" false; done
kwin_effect squash false      # one minimise animation at a time
kwin_effect magiclamp false
kwin_effect maximize false    # ozios_morph also covers maximising
kwin_effect "$motion" true
kwin_effect ozios_morph true
kwin_effect ozios_minimize true
# Wobbling would bend a window while it flows into place.
kwin_effect wobblywindows false
# Desktops slide past each other with a gap between them.
kwriteconfig6 --file kwinrc --group Effect-slide --key HorizontalGap 48
kwriteconfig6 --file kwinrc --group Effect-slide --key VerticalGap 48
kwriteconfig6 --file kwinrc --group Effect-slide --key SlideBackground false
# KWin's reconfigure only loads and unloads effects; a running one rereads its
# settings when asked by name.
[ -n "$qdbus" ] && "$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.reconfigureEffect slide >/dev/null 2>&1
# Alt+Tab shows the OziOS switcher.
kwriteconfig6 --file kwinrc --group TabBox --key LayoutName "$switcher"
if $lite; then
  kwin_effect blur false
  kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0.5
  # Without blur a see-through terminal shows the text of the window behind it.
  sed -i 's/^Opacity=.*/Opacity=1/' "$data"/konsole/OziOS*.colorscheme 2>/dev/null
else
  kwin_effect blur true
  kwriteconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 0.7
fi
[ -n "$qdbus" ] && "$qdbus" org.kde.KWin /KWin reconfigure >/dev/null 2>&1
$lite && echo "ok (light)" || echo ok

# Four desktops in a row, as the lights in the bar show them. Meta and a number go
# to a desktop, Meta+Ctrl and a number take the active window along; the dock does
# not use Meta and a number, so the shell lets go of them first.
say "Desktops"
kwriteconfig6 --file kwinrc --group Desktops --key Rows 1
count="$(kreadconfig6 --file kwinrc --group Desktops --key Number --default 1 2>/dev/null)"
if [ -n "$qdbus" ] && "$qdbus" org.kde.KWin /VirtualDesktopManager >/dev/null 2>&1; then
  count="$("$qdbus" org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager.count 2>/dev/null || echo 4)"
  while [ "${count:-4}" -lt 4 ] &&
        "$qdbus" org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager.createDesktop "$count" "" >/dev/null 2>&1; do
    count=$((count + 1))
  done
  command -v busctl >/dev/null &&
    busctl --user set-property org.kde.KWin /VirtualDesktopManager org.kde.KWin.VirtualDesktopManager rows u 1 >/dev/null 2>&1
elif [ "${count:-1}" -lt 4 ]; then
  kwriteconfig6 --file kwinrc --group Desktops --key Number 4
fi
for n in 1 2 3 4; do
  shortcut plasmashell "activate task manager entry $n"
  shortcut kwin "Switch to Desktop $n" $((0x10000030 + n)) $((0x0500002F + n)) $((0x1100002F + n))
  shortcut kwin "Window to Desktop $n" $((0x14000030 + n))
done
echo ok

# Tiling as on a tiling desktop, a desktop at a time: Meta+T tiles, Meta+F lets a
# window float (ozios-tiling). KWin's tile editor makes way, to Meta+Shift+T, before
# the script asks for Meta+T. The script says on and off in the session's language.
say "Tiling"
shortcut kwin "Edit Tiles" $((0x12000054))
case "${LANG:-}" in
  tr*) tiling_on="Döşeme açık"; tiling_off="Döşeme kapalı" ;;
  *) tiling_on="Tiling on"; tiling_off="Tiling off" ;;
esac
kwriteconfig6 --file kwinrc --group Script-ozios-tiling --key TextOn "$tiling_on"
kwriteconfig6 --file kwinrc --group Script-ozios-tiling --key TextOff "$tiling_off"
kwriteconfig6 --file kwinrc --group Plugins --key ozios-tilingEnabled true
if [ -n "$qdbus" ]; then
  "$qdbus" org.kde.KWin /KWin reconfigure >/dev/null 2>&1      # starts the scripts turned on
  for _ in $(seq 1 10); do
    [ "$("$qdbus" org.kde.KWin /Scripting org.kde.kwin.Scripting.isScriptLoaded ozios-tiling 2>/dev/null)" = true ] && break
    sleep 0.5
  done
  # Also when the script met its keys taken once and kglobalaccel remembers it without them.
  shortcut kwin "OziOS Tiling Toggle" $((0x10000054))
  shortcut kwin "OziOS Tiling Float" $((0x10000046))
fi
echo ok

# Keys from tiling desktops on top of Plasma's own: Meta+Q closes the window (Alt+F4
# still does), Meta+Enter opens a terminal (and Ctrl+Alt+T). The activity switcher
# moves to Meta+Shift+Q first. Meta+K shows them all (ozi-keys.desktop).
say "Keys"
shortcut plasmashell "manage activities" $((0x12000051))
shortcut kwin "Window Close" $((0x09000033)) $((0x10000051))
shortcut org.kde.konsole.desktop _launch $((0x0C000054)) $((0x11000004))
echo ok

echo
echo "Done. Open a new Konsole window."
