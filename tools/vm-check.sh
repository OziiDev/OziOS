#!/usr/bin/env bash
# Collect facts about the running system into docs/vm-report.txt.
# Changes nothing; run `sudo pacman -Sy` first if you want the package check.

root="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/.." 2>/dev/null && pwd)"
[ -d "$root/docs" ] || root="/mnt/ozios"
report="$root/docs/vm-report.txt"
qdbus="$(command -v qdbus6 || command -v qdbus-qt6 || command -v qdbus)"

{
echo "### OziOS VM report: $(date -Is)"

echo
echo "## System"
grep -E '^(NAME|VERSION_ID|BUILD_ID)=' /etc/os-release
uname -r
echo "Session: ${XDG_SESSION_TYPE:-?} / ${XDG_CURRENT_DESKTOP:-?}"
plasmashell --version 2>&1
kwin_wayland --version 2>&1 || kwin_x11 --version 2>&1
grep -m1 'model name' /proc/cpuinfo
echo "vCPUs: $(nproc)  RAM: $(free -h | awk '/^Mem/ { print $2 }')"
echo "x86-64 levels: $(/lib/ld-linux-x86-64.so.2 --help 2>/dev/null | grep -E 'x86-64-v[234].*supported' | tr '\n' ' ')"
echo "Nested virt flags: $(grep -cE 'vmx|svm' /proc/cpuinfo)  /dev/kvm: $([ -e /dev/kvm ] && echo yes || echo no)"
echo "OpenGL: $(glxinfo -B 2>/dev/null | grep -E 'OpenGL renderer' || echo 'glxinfo missing')"

echo
echo "## Repositories"
grep -E '^\[' /etc/pacman.conf

echo
echo "## Packages from iso/packages.ozi.x86_64"
while IFS= read -r pkg; do
  pkg="${pkg%$'\r'}"
  case "$pkg" in '' | \#*) continue ;; esac
  if pacman -Si "$pkg" >/dev/null 2>&1; then
    echo "ok         $pkg ($(pacman -Si "$pkg" | awk -F': ' '/^Repository/ { r = $2 } /^Version/ { v = $2 } END { print r " " v }'))"
  elif pacman -Qi "$pkg" >/dev/null 2>&1; then
    echo "installed  $pkg (not in the synced repos)"
  else
    echo "missing    $pkg"
  fi
done < "$root/iso/packages.ozi.x86_64"

echo
echo "## KWin effects"
if [ -n "$qdbus" ]; then
  echo "Loaded: $("$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.loadedEffects 2>&1 | tr '\n' ' ')"
  echo "Available: $("$qdbus" org.kde.KWin /Effects org.kde.kwin.Effects.listOfEffects 2>&1 | tr '\n' ' ')"
else
  echo "qdbus not found"
fi

echo
echo "## KDE settings"
for key in blurEnabled wobblywindowsEnabled magiclampEnabled overviewEnabled slideEnabled squashEnabled; do
  echo "kwinrc [Plugins] $key = '$(kreadconfig6 --file kwinrc --group Plugins --key "$key" 2>&1)'"
done
echo "kwinrc [Compositing] LatencyPolicy = '$(kreadconfig6 --file kwinrc --group Compositing --key LatencyPolicy 2>&1)'"
echo "kdeglobals [KDE] AnimationDurationFactor = '$(kreadconfig6 --file kdeglobals --group KDE --key AnimationDurationFactor 2>&1)'"

echo
echo "## Script syntax"
for script in winbridge/ozi-winrun packages/ozi-cli/ozi vfio/detect-iommu.sh tools/apply-branding.sh; do
  endings=LF
  grep -q $'\r' "$root/$script" && endings=CRLF
  if err="$(tr -d '\r' < "$root/$script" | bash -n 2>&1)"; then
    echo "ok    $script ($endings)"
  else
    echo "FAIL  $script ($endings): $err"
  fi
done
python3 -m py_compile "$root/branding/ozi-fetch" 2>&1 && echo "ok    branding/ozi-fetch"

echo
echo "## detect-iommu.sh"
tr -d '\r' < "$root/vfio/detect-iommu.sh" | bash 2>&1

echo
echo "## Tools"
for tool in xfreerdp3 virsh qemu-system-x86_64 virt-viewer secret-tool snapper paru efibootmgr calamares mkarchiso cmake; do
  printf '%-22s %s\n' "$tool" "$(command -v "$tool" || echo missing)"
done
} > "$report" 2>&1

echo "Report written to $report"
