#!/usr/bin/env bash
# Build the OziOS kernel: the CachyOS kernel recipe with the name changed from
# "cachyos" to "ozios". Run on Arch or CachyOS as a normal user (makepkg refuses
# to run as root), with base-devel and git installed.
#
#   kernel/build.sh [output-dir]
#
# Settings, all optional, through the environment:
#   OZI_CPU     generic_v1 | generic_v2 | generic_v3 | generic_v4 | zen4 | native
#               (default generic_v2: runs on any PC from about 2009 on. Never
#               "native" for a kernel others will install: it is tuned to
#               whatever machine happens to build it.)
#   OZI_LTO     none | thin | full   (default none: thin LTO needs far more RAM
#               and time; use it on a strong machine)
#   OZI_NVIDIA  yes | no             also build the NVIDIA open modules
#   OZI_ZFS     yes | no             also build the ZFS modules
#   OZI_KERNEL_REF   branch or tag of CachyOS/linux-cachyos (default master)
#   OZI_KERNEL_DATE  YYYY-MM-DD: use the recipe as it was on that day. Set it to
#               the build date of the CachyOS ISO being converted, so the kernel
#               and the NVIDIA modules match that ISO's driver packages.
#   OZI_KERNEL_WORK  scratch directory (default ~/ozios-kernel)
#   OZI_CHECK_ONLY   set to anything: stop after the rename check, no build
#
# Needs roughly 30 GB of disk, 8 GB of RAM and one to three hours.
set -euo pipefail

die() { echo "kernel: $*" >&2; exit 1; }
step() { printf '\n==> %s (%s)\n' "$*" "$(date +%H:%M:%S)"; }

[ "$(id -u)" != 0 ] || die "run as a normal user; makepkg refuses to run as root"
for tool in git makepkg; do
  command -v "$tool" >/dev/null || die "$tool is missing (pacman -S base-devel git)"
done

out="$(readlink -f "${1:-./out/kernel}")"
work="${OZI_KERNEL_WORK:-$HOME/ozios-kernel}"
ref="${OZI_KERNEL_REF:-master}"
upstream="https://github.com/CachyOS/linux-cachyos.git"
mkdir -p "$out" "$work"

step "Fetching the CachyOS kernel recipe ($ref)"
rm -rf "$work/linux-cachyos"
if [ -n "${OZI_KERNEL_DATE:-}" ]; then
  git clone --quiet --filter=blob:none --branch "$ref" "$upstream" "$work/linux-cachyos"
  commit="$(git -C "$work/linux-cachyos" rev-list -1 --before="$OZI_KERNEL_DATE 23:59:59" "$ref")"
  [ -n "$commit" ] || die "the recipe has no commit on or before $OZI_KERNEL_DATE"
  git -C "$work/linux-cachyos" checkout --quiet "$commit"
else
  git clone --quiet --depth 1 --branch "$ref" "$upstream" "$work/linux-cachyos"
fi
cd "$work/linux-cachyos/linux-cachyos"
[ -f PKGBUILD ] || die "upstream layout changed: no linux-cachyos/PKGBUILD"
echo "recipe commit: $(git -C "$work/linux-cachyos" rev-parse --short HEAD)"

step "Renaming to ozios"
# The package base, every package name, the module directory and the kernel
# release string all derive from this one variable.
sed -i -E 's/^([[:space:]]*)_pkgsuffix=.*/\1_pkgsuffix=ozios/' PKGBUILD
grep -c '^[[:space:]]*_pkgsuffix=ozios$' PKGBUILD | sed 's/^/_pkgsuffix lines rewritten: /'

# Settings are read by the recipe as ${var:=default}, so the environment wins.
export _processor_opt="${OZI_CPU:-generic_v2}"
export _use_llvm_lto="${OZI_LTO:-none}"
export _build_nvidia_open="${OZI_NVIDIA:-yes}"
export _build_zfs="${OZI_ZFS:-yes}"
export _build_debug=no _use_lto_suffix=no _use_gcc_suffix=no
export MAKEFLAGS="${MAKEFLAGS:--j$(nproc)}"

# Check before spending hours: every package must carry the new name and none
# may still say cachyos.
step "Checking the package names"
names="$(makepkg --printsrcinfo | sed -n 's/^pkgname = //p')"
echo "$names"
[ -n "$names" ] || die "the recipe lists no packages"
echo "$names" | grep -qx 'linux-ozios' || die "linux-ozios is not among the packages"
if echo "$names" | grep -qi 'cachyos'; then
  die "a package still carries the old name; the recipe changed upstream, check _pkgsuffix"
fi
release="$(makepkg --printsrcinfo | sed -n 's/^\tpkgver = //p;s/^pkgver = //p' | head -n1)"
release_no="$(makepkg --printsrcinfo | sed -n 's/^\tpkgrel = //p;s/^pkgrel = //p' | head -n1)"
version="${release:-unknown}-${release_no:-1}"
echo "kernel version: $version"
echo "cpu level: $_processor_opt, lto: $_use_llvm_lto, nvidia: $_build_nvidia_open, zfs: $_build_zfs"

if [ -n "${OZI_CHECK_ONLY:-}" ]; then
  echo "check only: stopping before the build"
  exit 0
fi

step "Building (this takes a long time)"
# The recipe's b2sums list matches only its own default options (thin LTO, no
# NVIDIA, no ZFS); with other options the source array is a different length.
# The kernel tarball is still verified through its PGP signature, so the
# checksums are skipped rather than the signature check.
for key in E18447AC260021D31F3FF6C4C8A2A4774B8B63C4 E8B9AA39F054E30E8290D492C3C4820857F654FE; do
  for server in keyserver.ubuntu.com keys.openpgp.org; do
    gpg --batch --keyserver "hkps://$server" --recv-keys "$key" >/dev/null 2>&1 && break
  done
done
gpg --list-keys E18447AC260021D31F3FF6C4C8A2A4774B8B63C4 >/dev/null 2>&1 \
  || echo "warning: signing keys could not be fetched; relying on the HTTPS download only" >&2
makepkg_flags=(--syncdeps --noconfirm --needed --force --skipchecksums)
gpg --list-keys E18447AC260021D31F3FF6C4C8A2A4774B8B63C4 >/dev/null 2>&1 || makepkg_flags+=(--skippgpcheck)
makepkg "${makepkg_flags[@]}"

step "Collecting the packages"
find . -maxdepth 1 -name 'linux-ozios*.pkg.tar.*' ! -name '*.sig' -exec cp -v {} "$out/" \;
ls "$out"/linux-ozios-*.pkg.tar.* >/dev/null 2>&1 || ls "$out"/linux-ozios*.pkg.tar.* >/dev/null || die "no packages were produced"
(cd "$out" && sha256sum linux-ozios*.pkg.tar.* > SHA256SUMS)
{
  echo "version: $version"
  echo "recipe: CachyOS/linux-cachyos $(git -C "$work/linux-cachyos" rev-parse HEAD)"
  echo "cpu: $_processor_opt  lto: $_use_llvm_lto  nvidia: $_build_nvidia_open  zfs: $_build_zfs"
  echo "built: $(date -u +%FT%TZ)"
} > "$out/BUILDINFO.txt"

step "Done"
ls -lh "$out"
