# Changelog

All notable changes to OziOS. Versions follow [Semantic Versioning](https://semver.org/);
the rules for releases are in [docs/RELEASING.md](docs/RELEASING.md).

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
