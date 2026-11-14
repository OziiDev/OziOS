#!/usr/bin/env bash
# Send key presses to a VirtualBox guest, for driving programs that can be
# used from the keyboard (Calamares, GRUB, a login prompt).
#
#   tools/vbkeys.sh <vm> <key>...
#
# Keys: enter tab space esc backspace up down left right home end
#       alt+<letter> ctrl+<letter> shift+tab  f1..f10  text:<string>
set -u
vm="${1:?usage: vbkeys.sh <vm> <key>...}"
shift
vb="${VBOXMANAGE:-VBoxManage}"
command -v "$vb" >/dev/null 2>&1 || vb="/c/Program Files/Oracle/VirtualBox/VBoxManage.exe"
export MSYS_NO_PATHCONV=1

declare -A code=(
  [esc]="01 81" [backspace]="0e 8e" [tab]="0f 8f" [enter]="1c 9c" [space]="39 b9"
  [up]="e0 48 e0 c8" [down]="e0 50 e0 d0" [left]="e0 4b e0 cb" [right]="e0 4d e0 cd"
  [home]="e0 47 e0 c7" [end]="e0 4f e0 cf" [pgup]="e0 49 e0 c9" [pgdn]="e0 51 e0 d1"
  [f1]="3b bb" [f2]="3c bc" [f3]="3d bd" [f4]="3e be" [f5]="3f bf"
  [f6]="40 c0" [f7]="41 c1" [f8]="42 c2" [f9]="43 c3" [f10]="44 c4"
)
declare -A letter=(
  [q]=10 [w]=11 [e]=12 [r]=13 [t]=14 [y]=15 [u]=16 [i]=17 [o]=18 [p]=19
  [a]=1e [s]=1f [d]=20 [f]=21 [g]=22 [h]=23 [j]=24 [k]=25 [l]=26
  [z]=2c [x]=2d [c]=2e [v]=2f [b]=30 [n]=31 [m]=32
)

press() { "$vb" controlvm "$vm" keyboardputscancode "$@" >/dev/null; }

for key in "$@"; do
  case "$key" in
    text:*) "$vb" controlvm "$vm" keyboardputstring "${key#text:}" ;;
    alt+[a-z])  l="${letter[${key#alt+}]}";  press 38 "$l" "$(printf '%02x' $((0x$l + 0x80)))" b8 ;;
    ctrl+[a-z]) l="${letter[${key#ctrl+}]}"; press 1d "$l" "$(printf '%02x' $((0x$l + 0x80)))" 9d ;;
    shift+tab)  press 2a 0f 8f aa ;;
    *) if [ -n "${code[$key]:-}" ]; then press ${code[$key]}; else echo "vbkeys: unknown key $key" >&2; exit 2; fi ;;
  esac
  sleep 0.4
done
