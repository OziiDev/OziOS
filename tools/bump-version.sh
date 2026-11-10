#!/usr/bin/env bash
# Set the OziOS version everywhere it is kept.
#
#   tools/bump-version.sh <new-version>      e.g. 0.2.0
set -euo pipefail

new="${1:?usage: bump-version.sh <new-version>}"
case "$new" in
  [0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "bump-version: '$new' is not MAJOR.MINOR.PATCH" >&2; exit 2 ;;
esac

root="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
old="$(tr -d '[:space:]' < "$root/VERSION")"

printf '%s\n' "$new" > "$root/VERSION"
sed -i "s/^pkgver=.*/pkgver=$new/; s/^pkgrel=.*/pkgrel=1/" "$root/packages/ozios-settings/PKGBUILD"

# A new heading for the changelog, below the introduction.
if ! grep -q "^## $new" "$root/CHANGELOG.md"; then
  tmp="$(mktemp)"
  awk -v v="$new" 'done || !/^## / { print; next } { print "## " v " (unreleased)\n\n- \n"; print; done = 1 }' \
    "$root/CHANGELOG.md" > "$tmp" && mv "$tmp" "$root/CHANGELOG.md"
fi

echo "version: $old -> $new"
echo "Edit CHANGELOG.md, then commit and tag v$new."
