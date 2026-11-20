# Changelog

All notable changes to OziOS. Versions follow [Semantic Versioning](https://semver.org/);
the rules for releases are in [docs/RELEASING.md](docs/RELEASING.md).

## 0.1.1 (unreleased)

CachyOS is out of the way: the OziOS image and the system the installer
creates carry no CachyOS kernel, no CachyOS programs and no CachyOS artwork.
The CachyOS repositories, keyring and mirror lists stay, because the installer
and the hardware tools are built on them (see `docs/DEVELOPMENT.md`).

- Installing on a machine with an NVIDIA card no longer stops at "Failed to run
  chwd". The OziOS kernel and its headers now go in right after the base system,
  before the driver step, from a package source the installer keeps on the new
  disk (`[ozios]`, `/opt/ozios`); NVIDIA modules are built for the installed
  driver (DKMS). A driver step that fails anyway no longer fails the
  installation; `ozi doctor` shows what it said.
- The OziOS shell, the desktop's own pieces on top of KWin: a dock whose icons
  grow toward the pointer, hop while a program starts and pulse for attention;
  a launcher (Meta key) with a greeting, search, category chips and a grid that
  flows in; window open and close motion (`ozios_motion`); the OziOS Plasma style
  for the bar, the dock and every popup. All motion is transforms and opacity,
  and it follows the animation speed setting (`ozi effects off` stops it).
- Colour themes: Cyan, Aurora, Ember, Mint, Rose and Frost (light). `ozi theme
  <name>` or the swatches in the control widget switch the bar, the dock,
  popups, the wallpaper and window frames at once. The OziOS apps (Welcome,
  Software, Classroom, Pen) open in the theme in use, and the terminal gets
  the theme's colours too. The Welcome window has a row of colour swatches:
  a click switches the desktop and the window flows into the new colours.
- `ozi theme auto` follows the time of day: a light theme from sunrise to
  sunset, a dark one at night, checked by a timer of the user's session.
- File search indexes names only by default (`/etc/xdg/baloofilerc`): reading
  every document after login kept an ordinary computer busy.
- A boot splash of our own: the tesseract turns while the computer starts
  (Plymouth, two-step plugin; tools/make-plymouth.py draws the frames). The
  installer sets it before the initramfs is built.
- The wallpaper takes the theme's colours, breathes, and has motes of light
  drifting through it; all of it stops while a window covers the desktop.
- The control widget and the new applets speak Turkish in a Turkish session.

- The long-term CachyOS kernel is gone from the ISO; the fallback entries of
  the boot menu, BIOS included, start the OziOS kernel.
- CachyOS Hello, its CLI installer and `cachy-chroot` are removed from the image.
- The installer is rewritten at boot (`ozipkg/installer.py`): its own branding,
  its own package list instead of the one the CachyOS project publishes (no
  CachyOS kernels, programs or wallpapers), boot loader entry and host name
  from OziOS, a GRUB theme and boot splash of our own.
- The OziOS kernel and packages are installed early in the installation, before
  the initramfs and boot loader steps, so they treat it like any other kernel.
  If it can not be installed the Arch kernel is, so the new system always boots.
- `os-release` and `lsb-release` name OziOS and point to this project; the hook
  runs after CachyOS's own so the last word is ours.
- Education edition (`ozios-edu`): board layout for smart boards, a screen pen
  (`ozi-pen`: pen, marker, line, arrow, box, circle, eraser, laser pointer,
  spotlight, saving to a PNG), a classroom app (`ozi-classroom`: class lists,
  picking a student without repeats, groups, a timer), Turkish defaults, an
  on-screen keyboard, no screen lock or sleep during a lesson, links to EBA,
  e-Okul and MEB, Xournal++ as whiteboard and LibreOffice. A separate ISO,
  built with `iso/remaster.sh --edition edu`.
- `ozi layout` takes any installed layout and waits for the desktop shell to
  start.
- New commands. `ozi doctor` checks the installation and says how to fix each
  finding. `ozi report` writes a text report for a bug report; nothing is sent
  anywhere, and names, addresses and serial numbers are replaced before the
  file is written. `ozi clean` shows what could be freed and, with `--yes`,
  removes old package versions, journal entries older than two weeks, orphaned
  packages and caches that rebuild themselves. `ozi play -- <game>` runs a game
  with game mode on for as long as it runs, and can ask for the discrete GPU or
  MangoHud. Manual pages for `ozi` and `ozi-pkg`; completions for bash, zsh
  and fish.
- `ozi gaming` installs Steam, game mode, MangoHud, Gamescope and the 32-bit
  graphics drivers that match the graphics card in the machine (`--yes` to do it;
  without it, only the list). Installing Steam by hand lets pacman pick the driver
  set, which may be for the wrong card.
- The login screen shows the OziOS wallpaper instead of the stock Plasma one.
- The apps are set in Overpass, which the package now brings (`ttf-overpass`); before,
  the font they asked for was not in the image and a fallback was used. The
  Welcome window lists its entries as plain rows and has a Games entry.
- A button in Welcome that fails now says why instead of doing nothing: in a live
  session the Windows layer explains that it needs an installed system, a computer
  without hardware virtualization is told to turn it on, and a program that stops
  at once shows its last error line. The Windows setup also checks for 70 GB of
  free disk and `kdialog` is a dependency.
- `ozi doctor` checks what games need: the memory map limit, Steam and the 32-bit
  Vulkan loader.
- Install guides: `docs/INSTALL.md` and `docs/KURULUM.md`.
- The boot menu of an installed system no longer lists CachyOS, and its default entry boots.
- The installer no longer downloads the CachyOS kernels it used to put on the
  new system and remove again, and does not offer ZFS as a root file system.
- The language and keyboard picked in the installer are kept on an installed Education system.
- The first-login setup now runs once: the autostart entry no longer relies on
  `$HOME` (systemd's generator escapes it), so the marker is written.
- Installer: steps that took longer than the default 30 seconds (pacman keyring,
  mirror ranking) are given ten minutes, so a slow network no longer fails the
  installation, and starting the installer a second time works. The desktop
  page offers Plasma only, and the page that asked which boot loader to use is
  gone: the installer takes its default.
- Tools for working on the image: `tools/qml-shot.py` takes pictures of an
  app's window offscreen and can drive it with pointer events, `tools/sync-live.sh`
  puts a checkout into a running live session, `tools/drive-calamares.sh`
  clicks through the installer, `tools/check-image.sh` checks a booted image.
- A workflow runs the unit tests and a syntax check of the shell scripts on
  every push.

## 0.1.0 (2026-11-13)

First public version. Early development: a live ISO converted from CachyOS
boots to the OziOS desktop on the OziOS kernel in a virtual machine. Nothing
has been run on real hardware yet.

- Desktop: top bar, floating dock, tesseract wallpaper and login splash,
  colour scheme, terminal greeting with a pinned turning tesseract.
- `ozios-settings` package: identity, theme, first-login setup, installer step.
- `ozipkg`: package review rules, `.deb` and Arch package inspection, permission
  model, rootless container command builders. Unit tested.
- `ozi-pkg` command: `review` a .deb, Arch package or AppImage, `install` a .deb
  into its own rootless box, `perms`, `run`, `list`, `remove`. Also reachable
  as `ozi review`, `ozi box`, `ozi apps`. Boxed apps start from the menu
  through `ozi-box`.
- Privileged helper (`ozi-pkg-helper`) with a polkit action: installs reviewed
  Arch packages by SHA-256, repository packages, removals, upgrades and
  snapshots, with strict argument checks. `ozi-pkg get|uninstall|upgrade|undo`.
- AUR support: `ozi-pkg aur` resolves dependencies, reviews each recipe
  (PKGBUILD rules, lookalike names, new or orphaned packages), builds in a
  throwaway container and installs the result through the helper.
- Turkish translations for every message (`data/i18n/tr.json`), checked for
  completeness by a test.
- AppImages: `ozi-pkg install` keeps the file under OziOS's own data folder
  and starts it only inside a bubblewrap sandbox with the saved permissions;
  it is never run during review.
- Boxes get a sub-id range for the user from the helper the first time one is
  needed, so rootless containers can unpack images on a fresh account.
- Panel layouts: `ozi layout default|deck|classic`, also in the control widget.
  Launchers for programs that are not installed are left out.
- Apps: Software (review and install packages, search, boxed apps and their
  permissions, system updates) and Welcome, both Qt Quick, sharing the
  OziUi components. Welcome starts the installer when run from the live
  medium. CachyOS Hello is hidden at the source (skeleton and live user).
- Control widget `org.ozios.control` in the top bar; `ozi effects`,
  `ozi mode game` and `ozi status --json`.
- The installer step installs `ozios-settings` and the `linux-ozios` packages
  into the new system through its own pacman, makes the OziOS kernel the first
  GRUB entry and names the menu OziOS. Tested against a base system with
  `tools/test-install-target.sh`; a full run through the Calamares windows is
  still open.
- Windows guest scripts: unattended setup, launcher with fallbacks.
- `linux-ozios` kernel build (CachyOS recipe under the OziOS name), GitHub
  workflow with release publishing.
- ISO conversion script with optional kernel swap and `--archive` for extra
  packages from the Arch Archive snapshot the ISO was built from.
- `docs/LICENSES.md`: what is MIT, what is not, and where the sources are.
