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
- Windows guest scripts: unattended setup, launcher with fallbacks.
- `linux-ozios` kernel build (CachyOS recipe under the OziOS name), GitHub
  workflow with release publishing.
- ISO conversion script with optional kernel swap.
