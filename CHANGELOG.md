# Changelog

All notable changes to OziOS. Versions follow [Semantic Versioning](https://semver.org/);
the rules for releases are in [docs/RELEASING.md](docs/RELEASING.md).

## 0.4.0 (unreleased)

"Öz": a desktop of OziOS's own, written from scratch. `oziwm` (a Wayland
compositor in Rust, on Smithay) and `ozi-shell` (Qt/QML) come in the
`ozi-desktop` package, from the OziOS repository or the AUR.

- Removed: the Windows guest. `ozi-winsetup`, `ozi-winrun`, `ozi winsetup`,
  `ozi reboot-windows`, `ozi hw`, the Windows tile in the quick settings and the
  control widget, the Welcome row and the installer slide are gone, and the ISO
  no longer carries QEMU, libvirt or FreeRDP for it. OziOS no longer promises to
  run Windows programs. Opening the shared folders of Windows computers on the
  network still works.

## 0.3.0 (unreleased)

"Akış" (flow): a desktop that no longer looks like Plasma, with rounded frames
that glow, windows that flow, a bar of three islands and tiling one key away,
and is still as easy to use as Plasma. The plan is in `docs/PLAN-0.3.md`.

- Window frames of our own (`org.ozios.decoration`, a KDecoration3 plugin):
  rounded windows, the program's content included; an outline in the accent
  colour on the active window and a faint one on the others; a soft glow in the
  theme's two colours; a centred title and round buttons that light up. They are
  compiled, so they come in a package of their own, `ozios-decoration`, built on
  the ISO for any x86-64 processor (not only the build machine's). The package
  carries their source: when Plasma moves to a new feature release, which an
  online installation can bring on its first day, a pacman hook builds the
  frames again on the computer, in a minute or two, with cmake and
  extra-cmake-modules that the installer puts in. Only when that cannot be done
  does it put them aside, and KWin draws Breeze frames until
  `sudo /usr/lib/ozios/decoration-guard` builds them. `ozi doctor` says which is
  the case.
- Windows flow: maximised, restored or tiled, a window moves from its old frame
  to the new one (`ozios_morph`); minimised, it goes into its dock icon and
  comes back out of it (`ozios_minimize`). Both take the place of KWin's own
  effects. The slide between desktops keeps the wallpaper still.
- The top bar is three floating islands: the launcher and the desktops on the
  left, the clock in the middle, the tray and the control centre on the right.
  The desktops are lights (`org.ozios.workspaces`): the one in use is a pill in
  the accent colours, desktops with windows are filled dots, and a click or the
  wheel switches. The clock (`org.ozios.clock`) opens a calendar.
- While music plays in any player (MPRIS: browsers, music and video players),
  the clock's island grows to show the track after three bars in the accent
  colours; the bars dance for a few seconds when a track starts, then rest. A
  click on the track pauses it, and the calendar shows the cover with buttons
  to go back, pause and skip. In the C locale of the live session the calendar
  named the weekdays 1 to 7; it now shows Mo, Tu, We.
- The control centre at the right of the bar starts with quick settings:
  tiles for Wi-Fi (with the network's name), Bluetooth, night light, do not
  disturb and game mode, filled with the accent colours while on, and a volume
  slider. A tile the computer has no use for, Wi-Fi without a Wi-Fi card say,
  is left out. `ozi quick` does the same in a terminal; it uses the system's
  own tools (wpctl, nmcli, rfkill, KWin's night light, kde-inhibit), so
  Plasma's settings and tray show the same state. Night light turned on here
  warms the screen at once unless it has a schedule of its own.
- Four desktops: Meta+1…4 switches, Meta+Ctrl+1…4 takes the window along.
- Tiling (`ozios-tiling`, a KWin script): Meta+T tiles the windows of a desktop
  in a spiral of halves with gaps between them, and each new window takes half
  of the one in use. Dragging a window onto another swaps the two, and resizing
  one moves the line beside it. Meta+F lets a window float above the tiles.
  Dialogs and fixed-size windows stay out of it. Turned off again, the windows
  go back where they were. It is off until Meta+T, or on everywhere from Look.
- Look (`ozi-look`, "Görünüm" in Turkish) sets the corner radius, the outline,
  the glow, title bars, the gaps, tiling, animation speed and blur. It shows each
  change on a small desktop and applies it at once. Its presets are Fluid,
  Tiling and Light. `ozi look` does the same in a terminal.
- Meta+K shows the keys worth knowing. A few keys from tiling desktops are
  added on top of Plasma's: Meta+Q closes a window (activities move to
  Meta+Shift+Q), Meta+Enter opens a terminal, and KWin's tile editor moves to
  Meta+Shift+T.
- Each theme's second colour, used by the glow, the desktop pill and today in
  the calendar, leans toward violet: cyan goes blue, ember pink, mint blue.
- Logging out, restarting and shutting down have a screen of their own: the
  desktop dims to ink with a soft glow of the theme's two colours, the time and
  a goodbye come down from above, and large tiles rise in one after another
  (lock, sleep, hibernate, restart, shut down, log out), drawn in lines of our
  own rather than taken from the icon theme. The tile under the pointer or the
  keyboard fills with the accent colours and glows; the arrows and Enter
  choose, Esc or a click beside the tiles goes back. When a program asks for one
  thing, a restart say, that tile is offered alone and counts down 30 seconds;
  any key stops the count. Updates waiting to be installed get tiles of their
  own. It is Plasma's logout greeter with the OziOS look-and-feel's
  `logout/Logout.qml`. From Plasma 6.8 on the greeter takes that screen from
  the desktop shell instead, so a shell package of ours that holds only this
  screen is named to the greeter alone (the desktop stays Plasma's); should a
  later Plasma reject the screen, the greeter shows its own.
- The first login of a new installation shows the OziOS splash rather than
  Plasma's (the look is set for each person during that login, after its
  splash), and the lock screen shows the OziOS figure, standing still, rather
  than Plasma's picture. Both are system-wide defaults in `/etc/xdg` that each
  person can still change.
- Welcome points to Look and to the keys card, next to getting software.
- The installer no longer gives up when the network drops while it downloads
  the base system. A few seconds without a network (Wi-Fi that drops, a router
  that restarts) failed every mirror at once and ended the installation with
  "Failed to run pacstrap". pacstrap now runs through `retry-download`, which
  waits until a mirror answers again and carries on where the download stopped,
  up to four tries; the files already downloaded are kept. Any other failure
  still stops the installation at once.
- Tested in KWin 6.7.4 in VirtualBox: the islands, the desktop keys and the
  slide; tiling on and off, new windows, floating, dragging and resizing; and
  Look in Turkish with its Tiling preset.

## 0.2.0 (unreleased)

The OziOS desktop of its own, tried in a real Plasma session this time, and an
installer that gets through the driver step on NVIDIA cards.

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
- Alt+Tab shows the OziOS switcher: the open windows as live pictures in one
  row, the chosen one forward in the accent colour, the row gliding to keep
  it in the middle (`org.ozios.switcher`).
- The wallpaper takes the theme's colours, breathes, and has motes of light
  drifting through it; all of it stops while a window covers the desktop.
- The control widget and the new applets speak Turkish in a Turkish session.
- Tested in a Plasma session (VirtualBox): the launcher loads (its avatar left
  Kirigami in Frameworks 6), popups and tool tips are solid where nothing blurs
  behind them, and files copied from a VirtualBox shared folder are readable.
- Animations stay on where KWin draws in software, as in a virtual machine
  without 3D, where KWin used to switch every one of them off and the desktop
  felt dead (`/usr/lib/environment.d/60-ozios-animations.conf`). `ozi doctor`
  says when the desktop is drawn in software and, in VirtualBox, where to turn
  3D acceleration on.
- Idle means idle: the wallpaper moves on one clock at 25 frames a second and
  holds still in the light effects profile; the Welcome mark and the terminal's
  pinned tesseract turn when something happens, then rest. Measured in the VM,
  an idle desktop went from more than two processor cores to under one percent.
- Soft shadows under popups, tool tips and the floating bar and dock.
- Developer and test tools (Avahi browsers, Qt's tools, v4l2 tests, lstopo,
  lftp) stay installed but out of the program menu.
- Windows: in VirtualBox the folders shared with Windows open in the file
  manager (the live user and the installed system's people are in `vboxsf`);
  installed next to Windows, the hardware clock keeps local time so the clock is
  right in both systems. The Welcome window opens the shared folders of Windows
  computers on the network.
- Installed in a virtual machine, the system gets that machine's guest tools
  (VirtualBox, VMware, KVM): shared folders, a shared clipboard, a screen that
  follows the window. The driver step only looks at real hardware, so before
  this a system installed in VirtualBox had none.
- `ozi doctor` reads the global theme's values from `kdedefaults`, so a fresh
  system no longer says its Plasma style is not OziOS's.

## 0.1.1 (unreleased)

CachyOS is out of the way: the OziOS image and the system the installer
creates carry no CachyOS kernel, no CachyOS programs and no CachyOS artwork.
The CachyOS repositories, keyring and mirror lists stay, because the installer
and the hardware tools are built on them (see `docs/DEVELOPMENT.md`).

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
