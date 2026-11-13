import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import installer  # noqa: E402

SETTINGS = """\
---
modules-search: [ local ]

instances:
- id:       online
  module:   packages
  config:   packages_online.conf
- id:       bootloader
  module:   packagechooser
  config:   packagechooser_bootloader.conf

sequence:
- exec:
  - partition
  - mount
  - pacstrap
  - chwd
  - packages@online
  - luksbootkeyfile
  - plymouthcfg
  - initcpio
  - bootloader
  - umount
- show:
  - finished
branding: cachyos
"""

NETINSTALL = """\
- name: "CachyOS required (hidden)"
  hidden: true
  packages:
     - cachyos-hooks
     - chwd
- name: "CachyOS kernels (hidden)"
  hidden: true
  packages:
     - linux-cachyos
     - linux-cachyos-headers
     - linux-cachyos-lts
- name: "CachyOS kernels (hidden/handheld)"
  packages:
     - linux-cachyos-deckify
- name: "CachyOS Packages"
  packages:
     - cachyos-hello
     - cachyos-kernel-manager
     - cachyos-settings
     - cachyos-wallpapers
- name: "KDE-Desktop"
  packages:
    - plasma-meta
    - cachyos-kde-settings
    - cachy-update
    - cachyos-nord-kde-theme-git
"""


class Settings(unittest.TestCase):
    def test_adds_both_steps_in_the_right_places(self):
        text = installer.patch_settings(SETTINGS)
        steps = [line.strip("- ").strip() for line in text.split("\n") if line.startswith("  - ")]
        self.assertEqual(steps[steps.index("packages@online") + 1], installer.EARLY)
        self.assertEqual(steps[steps.index("umount") - 1], installer.STEP)
        self.assertLess(steps.index(installer.EARLY), steps.index("initcpio"))
        self.assertLess(steps.index(installer.EARLY), steps.index("bootloader"))

    def test_instances_are_declared(self):
        text = installer.patch_settings(SETTINGS)
        self.assertIn("- id: ozios\n  module: shellprocess\n  config: shellprocess_ozios.conf", text)
        self.assertIn("- id: ozios_early\n  module: shellprocess\n  config: shellprocess_ozios_early.conf", text)

    def test_branding_and_no_cachyos_boot_animation(self):
        text = installer.patch_settings(SETTINGS)
        self.assertIn("branding: ozios", text)
        self.assertNotIn("plymouthcfg", text)
        self.assertNotIn("branding: cachyos", text)

    def test_running_twice_changes_nothing(self):
        once = installer.patch_settings(SETTINGS)
        self.assertEqual(installer.patch_settings(once), once)

    def test_an_older_patched_file_gets_the_early_step(self):
        old = SETTINGS.replace("  - umount", "  - shellprocess@ozios\n  - umount")
        new = installer.patch_settings(old)
        self.assertIn(installer.EARLY, new)
        self.assertEqual(new.count("- shellprocess@ozios\n"), 1)


class PackageLists(unittest.TestCase):
    def test_no_cachyos_kernels_or_programs_remain(self):
        text = installer.patch_netinstall_yaml(NETINSTALL)
        for name in ("linux-cachyos", "cachyos-hello", "cachyos-kernel-manager", "cachyos-wallpapers",
                     "cachy-update", "cachyos-nord-kde-theme-git", "CachyOS kernels"):
            self.assertNotIn(name, text)

    def test_what_the_system_needs_stays(self):
        text = installer.patch_netinstall_yaml(NETINSTALL)
        for name in ("cachyos-hooks", "chwd", "cachyos-settings", "plasma-meta", "cachyos-kde-settings"):
            self.assertIn(name, text)

    def test_shown_group_names_are_ours(self):
        text = installer.patch_netinstall_yaml(NETINSTALL)
        self.assertIn('"System packages"', text)
        self.assertNotIn('"CachyOS Packages"', text)

    def test_idempotent_and_keeps_the_layout(self):
        once = installer.patch_netinstall_yaml(NETINSTALL)
        self.assertEqual(installer.patch_netinstall_yaml(once), once)
        self.assertTrue(once.startswith('- name: "CachyOS required (hidden)"'))

    def test_only_the_local_list_is_used(self):
        conf = "groupsUrl:\n - https://raw.githubusercontent.com/CachyOS/x/netinstall.yaml\n - file:///etc/calamares/modules/netinstall.yaml\nrequired: true\n"
        out = installer.patch_netinstall_conf(conf)
        self.assertNotIn("https://", out)
        self.assertIn("file:///etc/calamares/modules/netinstall.yaml", out)

    def test_pacstrap_loses_the_cachyos_boot_animation(self):
        text = "basePackages:\n  - base\n  - cachyos-plymouth-bootanimation\n  - cachyos-plymouth-theme\n  - cachyos-settings\n"
        out = installer.patch_pacstrap(text)
        self.assertNotIn("plymouth", out)
        self.assertIn("cachyos-settings", out)


class Boot(unittest.TestCase):
    def test_grub_uses_our_theme_and_kernel(self):
        text = 'defaults:\n    GRUB_TOP_LEVEL: "/boot/vmlinuz-linux-cachyos"\n    GRUB_THEME: "/usr/share/grub/themes/cachyos/theme.txt"\n'
        out = installer.patch_grubcfg(text)
        self.assertIn('"/boot/vmlinuz-linux-ozios"', out)
        self.assertIn(installer.THEME, out)
        self.assertNotIn("cachyos", out)

    def test_bootloader_entry_name_and_kernel_list(self):
        text = 'efiBootloaderId: "cachyos"\nrefindKernelList: [ "linux-cachyos","linux" ]\nlimineSplashLogo: "/usr/share/wallpapers/cachyos-wallpapers/limine-splash.png"\n'
        out = installer.patch_bootloader(text)
        self.assertIn('efiBootloaderId: "ozios"', out)
        self.assertIn('[ "linux-ozios","linux-cachyos"', out)
        self.assertIn(installer.SPLASH, out)
        self.assertEqual(installer.patch_bootloader(out), out)

    def test_hostname_template_and_installer_messages(self):
        self.assertIn('template: "ozios-${cpu}"', installer.patch_users('  template: "cachyos-${cpu}"\n'))
        out = installer.patch_names('     name: "Preparing your system for CachyOS"\n     other: "CachyOS"\n')
        self.assertIn('Preparing your system for OziOS', out)
        self.assertIn('other: "CachyOS"', out)

    def test_scripts_name_the_system(self):
        out = installer.patch_script('sed -i s/x/TARGET_OS_NAME="CachyOS"/\n--description "Fresh CachyOS Installation"\n')
        self.assertNotIn("CachyOS", out)


class Apply(unittest.TestCase):
    def test_rewrites_a_tree_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "calamares")
            os.makedirs(os.path.join(base, "modules"))
            os.makedirs(os.path.join(base, "scripts"))
            with open(os.path.join(base, "settings.conf"), "w", encoding="utf-8") as fh:
                fh.write(SETTINGS)
            with open(os.path.join(base, "modules", "netinstall.yaml"), "w", encoding="utf-8") as fh:
                fh.write(NETINSTALL)
            with open(os.path.join(base, "scripts", "bootloader-post-setup"), "w", encoding="utf-8") as fh:
                fh.write('TARGET_OS_NAME="CachyOS"\n')
            changed = installer.apply(bases=(base,), etc=base)
            self.assertEqual(len(changed), 3)
            self.assertTrue(os.path.isfile(os.path.join(base, "modules", "shellprocess_ozios_early.conf")))
            with open(os.path.join(base, "modules", "shellprocess_ozios.conf"), encoding="utf-8") as fh:
                self.assertIn("install-to-target late", fh.read())
            self.assertEqual(installer.apply(bases=(base,), etc=base), [])


if __name__ == "__main__":
    unittest.main()
