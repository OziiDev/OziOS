#!/usr/bin/env bash
# Publish the OziOS pacman repository as the GitHub release "repo".
#
#   tools/publish-repo.sh            build the repository in out/repo and upload it
#   tools/publish-repo.sh --dry-run  only build out/repo
#
# Systems find it through /etc/pacman.conf:
#   [ozios]
#   SigLevel = Optional TrustAll
#   Server = https://github.com/OziiDev/OziOS/releases/download/repo
# so a new upload here reaches everyone with `pacman -Syu`. The release keeps
# one version of each package; older files are removed from it.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
out="$here/out/repo"
tag=repo
dry=false
[ "${1:-}" = --dry-run ] && dry=true

newest() {  # newest file for a package name pattern among the given dirs
  local name="$1"; shift
  ls -t "$@" 2>/dev/null | grep -E "/$name-[0-9][^/]*-(any|x86_64)\.pkg\.tar\.zst$" | head -n 1
}

rm -rf "$out"
mkdir -p "$out"
for name in ozios-settings ozi-desktop; do
  file="$(newest "$name" "$here"/out/*.pkg.tar.zst)"
  [ -n "$file" ] || { echo "no $name package in out/; build it first" >&2; exit 1; }
  cp "$file" "$out/"
done
file="$(newest ozios-decoration "$here"/out/*.pkg.tar.zst /opt/ozios/*.pkg.tar.zst)"
[ -n "$file" ] && cp "$file" "$out/"
cp "$here"/.kernel-pkgs/linux-ozios*.pkg.tar.zst "$out/" 2>/dev/null || echo "no kernel packages in .kernel-pkgs; the repository will not carry the kernel" >&2

(cd "$out" && repo-add -q ozios.db.tar.gz ./*.pkg.tar.zst)
# GitHub release assets cannot be symlinks: real copies under the names pacman asks for.
(cd "$out" && rm -f ozios.db ozios.files && cp ozios.db.tar.gz ozios.db && cp ozios.files.tar.gz ozios.files)
ls -la "$out"
$dry && exit 0

if ! gh release view "$tag" >/dev/null 2>&1; then
  gh release create "$tag" --prerelease --title "OziOS paket deposu" --notes \
"pacman deposu: OziOS sistemleri güncellemeleri buradan alır.

\`\`\`
[ozios]
SigLevel = Optional TrustAll
Server = https://github.com/OziiDev/OziOS/releases/download/repo
\`\`\`"
fi
gh release upload "$tag" "$out"/* --clobber
# Old versions out of the release.
keep="$(cd "$out" && ls)"
gh release view "$tag" --json assets --jq '.assets[].name' | while read -r asset; do
  grep -qxF "$asset" <<<"$keep" || gh release delete-asset "$tag" "$asset" --yes
done
echo "published: https://github.com/OziiDev/OziOS/releases/tag/$tag"
