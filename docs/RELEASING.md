# Releasing

## Version numbers

- **OziOS** follows Semantic Versioning: `MAJOR.MINOR.PATCH`. The number lives
  in `VERSION`; `packages/ozios-settings/PKGBUILD` must carry the same
  `pkgver` (`tests/test_version.py` checks it). Use `tools/bump-version.sh
  <new-version>` to change both and add a changelog heading.
  While the major number is 0, minor releases may change anything.
- **The kernel** keeps the version of the CachyOS recipe it is built from, for
  example `7.1.6-1`. OziOS adds its own revision when the same version is built
  again with other settings: the tag is `kernel-<version>-ozios<revision>`,
  for example `kernel-7.1.6-1-ozios1`.
- **ISO files** are named `ozios-<version>-<yymmdd>-x86_64.iso`, where the date
  is the day the conversion ran.

## Kernel release

1. Actions, "Build the OziOS kernel", Run workflow.
2. Set `recipe_date` to the build date of the CachyOS ISO being converted so the
   NVIDIA modules match its driver. Leave `publish` on.
3. When the run finishes the release `kernel-<version>-ozios<revision>` holds the
   packages and `SHA256SUMS`.

## ISO release

The ISO is made on a machine, not in CI (the conversion needs the live session
of the source ISO).

1. `tools/bump-version.sh <version>`, commit, tag `v<version>`.
2. Convert, in the live session of the source ISO (the date is the day that ISO
   was built; it must match the kernel's `recipe_date`):

   ```
   sudo iso/remaster.sh --kernel <dir with the kernel packages> \
        --archive 2026/08/09 --add "python-pyqt6 podman bubblewrap"
   ```

   `--add` lists what `ozios-settings` depends on and the source ISO lacks.
3. Test the result in a virtual machine and on real hardware.
4. Publish `ozios-...iso` and its `.sha256` where people can download it.
   GitHub release files are limited to 2 GiB and the ISO is larger, so host
   the ISO elsewhere and link it from the release notes, or split it.
5. Create the GitHub release for tag `v<version>` with the changelog section as
   the notes.
