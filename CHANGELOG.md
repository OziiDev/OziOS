# Changelog

All notable changes to OziOS. Versions follow [Semantic Versioning](https://semver.org/);
the rules for releases are in [docs/RELEASING.md](docs/RELEASING.md).

## 0.1.0 (unreleased)

First public version. Early development: a live ISO converted from CachyOS
boots to the OziOS desktop in a virtual machine.

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
- Apps: Software (review and install packages, search, boxed apps and their
  permissions, system updates) and Welcome, both Qt Quick, sharing the
  OziUi components. CachyOS Hello is hidden for the user.
- Control widget `org.ozios.control` in the top bar; `ozi effects`,
  `ozi mode game` and `ozi status --json`.
- The installer step also installs the `linux-ozios` packages into the new
  system when the medium carries them.
- Windows guest scripts: unattended setup, launcher with fallbacks.
- `linux-ozios` kernel build (CachyOS recipe under the OziOS name), GitHub
  workflow with release publishing.
- ISO conversion script with optional kernel swap.
