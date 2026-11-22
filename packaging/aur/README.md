# AUR

`ozi-desktop/PKGBUILD` is the AUR package: the OziOS desktop on any Arch-based
system (`yay -S ozi-desktop` or `paru -S ozi-desktop`). It builds a tagged
release from GitHub, so a new release needs a new `_tag`/`pkgver` here.

Publishing (needs an AUR account with an SSH key, once):

    git clone ssh://aur@aur.archlinux.org/ozi-desktop.git aur-ozi-desktop
    cp packaging/aur/ozi-desktop/PKGBUILD aur-ozi-desktop/
    cd aur-ozi-desktop
    updpkgsums                      # fills sha256sums from the release tarball
    makepkg --printsrcinfo > .SRCINFO
    makepkg -si                     # try it
    git add PKGBUILD .SRCINFO && git commit -m "ozi-desktop 0.4.0beta1" && git push

OziOS systems do not need the AUR: they get the same desktop and its updates
from the OziOS repository (tools/publish-repo.sh, the GitHub release "repo").
