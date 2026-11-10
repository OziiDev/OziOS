#!/usr/bin/env bash
# Runs inside the archlinux container started by the GitHub workflow: install
# the build tools, make an unprivileged builder and run kernel/build.sh.
#
#   /src is the checked-out repository (read-only is fine); results go to
#   /src/out/kernel.
set -euo pipefail

pacman -Syu --noconfirm --needed base-devel git sudo bc cpio libelf pahole perl python tar xz zstd clang llvm lld \
  inetutils kmod
useradd -m builder
echo 'builder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/builder

cp -r /src /home/builder/src
chown -R builder:builder /home/builder/src

su builder -c "cd /home/builder/src && \
  OZI_CPU='${OZI_CPU:-generic_v2}' OZI_LTO='${OZI_LTO:-none}' OZI_NVIDIA='${OZI_NVIDIA:-yes}' OZI_ZFS='${OZI_ZFS:-yes}' \
  OZI_KERNEL_DATE='${OZI_KERNEL_DATE:-}' OZI_KERNEL_WORK=/home/builder/work bash kernel/build.sh /home/builder/out"

mkdir -p /src/out/kernel
cp -v /home/builder/out/* /src/out/kernel/
