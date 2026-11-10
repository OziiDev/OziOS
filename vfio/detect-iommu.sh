#!/usr/bin/env bash
# Report what this machine can do for the Windows guest. Read-only.
set -u

echo "== CPU =="
grep -m1 'model name' /proc/cpuinfo
if grep -qE 'vmx|svm' /proc/cpuinfo; then
  echo "Hardware virtualization: yes"
  has_virt=1
else
  echo "Hardware virtualization: no (enable VT-x / SVM in the firmware setup)"
  has_virt=0
fi

echo
echo "== IOMMU =="
if [ -n "$(ls -A /sys/kernel/iommu_groups 2>/dev/null)" ]; then
  echo "IOMMU: on"
  has_iommu=1
else
  echo "IOMMU: off (enable VT-d / AMD-Vi in the firmware setup; kernel: intel_iommu=on or amd_iommu=on, iommu=pt)"
  has_iommu=0
fi

echo
echo "== GPUs =="
gpus=0
while read -r line; do
  [ -z "$line" ] && continue
  gpus=$((gpus + 1))
  dev="/sys/bus/pci/devices/0000:${line%% *}"
  group="-"
  [ -e "$dev/iommu_group" ] && group="$(basename "$(readlink -f "$dev/iommu_group")")"
  echo "$line  [IOMMU group: $group]"
done < <(lspci -nn 2>/dev/null | grep -Ei 'vga|3d controller|display controller')

echo
echo "== Suggested mode =="
if [ "$has_virt" = 0 ]; then
  echo "Tier D: the Windows guest cannot run without hardware virtualization."
elif [ "$has_iommu" = 1 ] && [ "$gpus" -ge 2 ]; then
  echo "Tier A: GPU passthrough with Looking Glass."
elif [ "$has_iommu" = 1 ]; then
  echo "Tier B: one GPU; app mode on virtio-gpu. Passthrough needs a second GPU."
else
  echo "Tier C: app mode only (RemoteApp); limited for games."
fi
