# OziOS

An Arch-based desktop system for gaming and everyday use, built on CachyOS
packages and KDE Plasma 6. It aims to be quick on ordinary hardware and easy
for people who do not want to learn Arch first.

![OziOS](branding/logo.svg)

**Status: early development.** A live ISO boots to the OziOS desktop in a
virtual machine. Installing from that ISO, the Windows layer and the package
installer are not finished. See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## What it is

- **A desktop of its own on top of Plasma.** Top bar, floating dock, a
  tesseract wallpaper that stops moving whenever a window covers it, matching
  terminal, boot menu and login splash. Cyan `#00E5FF` on ink `#080B10` with
  ice `#F4FCFF` for text.
- **A package installer that explains itself** (in progress). It reviews a
  package before installing it, runs Debian and Ubuntu `.deb` files in an
  isolated rootless container, and gives every contained app one set of
  permissions: internet, files, camera, sound, devices.
- **Windows programs from the file manager** (in progress). `.exe` and `.msi`
  files open through a Windows guest that is installed from your own Windows
  ISO, with telemetry and bundled apps removed. OziOS does not ship Windows.
- **Its own kernel name** (in progress). The CachyOS kernel recipe, built as
  `linux-ozios`.

## Layout

| Folder | What is in it |
|---|---|
| `branding/` | logo, wallpaper, colour schemes, terminal greeting |
| `desktop/` | Plasma theme, layout, splash and the wallpaper plugin |
| `python/ozipkg/` | package review, containment and permissions (no GUI code) |
| `packages/` | the `ozios-settings` package and the `ozi` command |
| `winbridge/`, `winimage/` | Windows guest setup and launcher |
| `kernel/` | build the OziOS kernel |
| `iso/` | turn a CachyOS ISO into an OziOS ISO |
| `tools/` | build and test helpers |
| `tests/` | unit tests: `python -m unittest discover -s tests` |

## Licence

MIT for the code in this repository. Files derived from KDE, CachyOS or other
projects keep their own licences.

Turkish: [README.tr.md](README.tr.md)
