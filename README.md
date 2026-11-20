# OziOS

An Arch-based desktop system for gaming and everyday use, built on CachyOS
packages and KDE Plasma 6. It aims to be quick on ordinary hardware and easy
for people who do not want to learn Arch first.

![The OziOS desktop](docs/img/desktop.png)

The desktop after a fresh install, the login screen and the Welcome window:

![Login screen](docs/img/login.png)
![Welcome](docs/img/welcome.png)

**Status: early development.** A live ISO boots to the OziOS desktop on the
OziOS kernel in a virtual machine, the installer puts it on a disk and the
result starts, and the package installer works for `.deb`, AppImage and Arch
packages. The Windows layer has not run on a real guest yet
and nothing has been tried on real hardware. See
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

To try it, follow [docs/INSTALL.md](docs/INSTALL.md): put the ISO on a USB stick,
start from it, press Install.

## What it is

- **A desktop of its own on top of KWin.** Its own dock (icons grow toward the
  pointer, hop while a program starts), its own launcher, window motion, a
  Plasma style for the bar and every popup, and a living tesseract wallpaper
  that stops whenever a window covers it. Six colour themes (`ozi theme`):
  Cyan `#00E5FF` on ink `#080B10` by default, plus Aurora, Ember, Mint, Rose
  and a light Frost. See [desktop/README.md](desktop/README.md).
- **A package installer that explains itself.** It reviews a package before
  installing it, runs Debian and Ubuntu `.deb` files in an isolated rootless
  container and AppImages in a sandbox, builds AUR packages in a throwaway
  container, and gives every contained app one set of permissions: internet,
  files, camera, sound, devices.
- **Windows programs from the file manager** (in progress). `.exe` and `.msi`
  files open through a Windows guest that is installed from your own Windows
  ISO, with telemetry and bundled apps removed. OziOS does not ship Windows.
- **Next to Windows.** The shared folders of Windows computers on the network
  open from the Welcome window; in VirtualBox the folders shared with a Windows
  host open in the file manager; installed beside Windows, the clock stays right
  in both systems.
- **Its own kernel.** The CachyOS kernel recipe, built as `linux-ozios` and
  released from this repository. The image and the installed system carry no
  CachyOS kernel, program or artwork.
- **An Education edition** for smart boards: board layout, a screen pen,
  whiteboard, a classroom app (student picker, groups, timer), Turkish
  defaults. See [docs/EDUCATION.md](docs/EDUCATION.md); a Turkish guide for
  teachers is in [docs/EGITIM.md](docs/EGITIM.md).

## Layout

| Folder | What is in it |
|---|---|
| `branding/` | logo, wallpaper, colour schemes, terminal greeting |
| `desktop/` | Plasma theme, layout, splash and the wallpaper plugin |
| `edu/` | the Education edition: board layout, school defaults, links |
| `python/ozipkg/` | package review, containment and permissions (no GUI code) |
| `packages/` | the `ozios-settings` package and the `ozi` command |
| `winbridge/`, `winimage/` | Windows guest setup and launcher |
| `kernel/` | build the OziOS kernel |
| `iso/` | turn a CachyOS ISO into an OziOS ISO |
| `docs/` | design, development notes, releasing, licences |
| `tools/` | build and test helpers |
| `tests/` | unit tests: `python -m unittest discover -s tests` |

## Licence

MIT for the code in this repository. Files derived from KDE, CachyOS or other
projects keep their own licences.

Turkish: [README.tr.md](README.tr.md)
