# OziOS kernel

`linux-ozios` is the CachyOS kernel recipe built under another name, so
`uname -r` reads `7.1.6-1-ozios` instead of `7.1.6-1-cachyos`. Nothing else
about the kernel changes: same patches, same scheduler, same configuration.

Packages produced: `linux-ozios`, `linux-ozios-headers`, and (by default)
`linux-ozios-nvidia-open` and `linux-ozios-zfs`.

## Build on GitHub (recommended)

The laptop used for development is too small for this. GitHub's free runners
are enough.

1. Push this repository to GitHub.
2. Actions, "Build the OziOS kernel", Run workflow.
   - `cpu`: `generic_v2` runs on nearly every PC; `generic_v3` is a little
     faster but needs a 2013 or newer processor.
   - `recipe_date`: set it to the build date of the CachyOS ISO you convert
     (the ISO in `CachyOS.iso` was built on `2026-08-09`). The NVIDIA modules
     must match the driver packages already on the ISO, and the recipe's
     driver version follows its date.
   - `lto`: leave `none`. `thin` needs more memory and time than a free runner
     has.
3. Download the `linux-ozios` artifact (one to three hours later).

## Build on your own Arch or CachyOS machine

```sh
OZI_KERNEL_DATE=2026-08-09 kernel/build.sh ~/ozios-kernel-out
```

Needs a normal user, `base-devel` and `git`, about 30 GB of disk and 8 GB of
RAM. `OZI_CHECK_ONLY=1` stops after the name check, which takes a minute and is
a good way to see whether the upstream recipe changed shape.

## Put it in the ISO

```sh
sudo iso/remaster.sh --kernel ~/ozios-kernel-out
```

This replaces the `linux-cachyos*` packages inside the live image, rebuilds the
live initramfs for the new kernel, swaps the boot files on the ISO and points
the boot menus at them. The long-term-support kernel entry stays as it was.

## Not done yet

- A system installed from the ISO still gets the CachyOS kernel from the
  CachyOS repository. Installing `linux-ozios` into the target during setup,
  including the boot loader entry, is the next step.
- CachyOS tools that look for packages by name (`chwd`, CachyOS Hello) may
  still ask for `linux-cachyos-*`.
- Nothing here has been built end to end yet. What has been checked: the
  rename produces the four expected package names against the real upstream
  recipe, and pinning by date reproduces kernel 7.1.6 with NVIDIA 610.57.04,
  the same versions as the ISO.
