# Licences

## OziOS itself

Everything in this repository that is not listed below is MIT licensed, see
[`LICENSE`](../LICENSE). That covers the `ozi` commands, `ozipkg`, the Software and
Welcome apps, the Plasma theme, wallpaper and control widget, the build scripts and
the artwork (the tesseract mark and the palette).

The Software and Welcome apps use PyQt6, which is GPL-3.0 (or commercial). The MIT
sources stay MIT, but an image that ships them together with PyQt6 is distributed
under the GPL for that combination. The source for everything is public.

## What the ISO contains

An OziOS image is a CachyOS live image with OziOS added, and CachyOS's kernels,
programs and artwork taken out. What remains of CachyOS (repositories, keyring,
tuning packages, the installer build) is listed in `docs/DEVELOPMENT.md`. The packages inside keep
their own licences, and their sources are available from the places they come from:

| Part | Licence | Source |
| --- | --- | --- |
| Linux kernel (`linux-ozios`) | GPL-2.0-only | the CachyOS recipe pinned in `kernel/`, built unchanged except for the package name |
| NVIDIA open kernel modules | MIT / GPL-2.0 | NVIDIA, through the same recipe |
| CachyOS packages and patches | mostly GPL, per package | https://github.com/CachyOS |
| Arch Linux packages | per package | https://archlinux.org/packages/ |
| KDE Plasma and Frameworks | GPL / LGPL, per component | https://invent.kde.org |
| Qt 6 | LGPL-3.0 / GPL-3.0 | https://code.qt.io |
| Podman, crun, netavark | Apache-2.0 | https://github.com/containers |
| Bubblewrap | LGPL-2.0-or-later | https://github.com/containers/bubblewrap |
| Education edition: Xournal++, Okular, KCalc, KolourPaint | GPL-2.0 or later | https://github.com/xournalpp, https://invent.kde.org |
| Education edition: LibreOffice | MPL-2.0 | https://www.libreoffice.org |
| Education edition: Maliit keyboard | LGPL-2.1 / BSD-3-Clause | https://github.com/maliit |

`pacman -Qi <package>` shows the licence of any installed package, and
`pacman -Qo <file>` tells which package a file belongs to.

## Not included

- **Windows.** OziOS does not contain or distribute it. `ozi-winsetup` installs a
  copy from an ISO you provide and you accept Microsoft's terms for that copy.
- **virtio-win drivers.** Fetched by `ozi-winsetup` on first use (Red Hat, mostly
  BSD-3-Clause and GPL-2.0).
- **Ubuntu base images** used for `.deb` boxes are downloaded on first use from the
  upstream registry and carry Ubuntu's own licences.

## Names

CachyOS, Arch Linux, KDE, Plasma, Qt, NVIDIA, Windows and Ubuntu are names of their
owners. OziOS is an independent project and is not endorsed by any of them.
