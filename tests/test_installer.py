import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

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


DESKTOPS = """\
mode: required
method: netinstall-select
default: KDE-Desktop

items:
    - id: ""
      # packages: [] # This item installs no packages
      name: "No Desktop"
      screenshot: ":/images/no-selection.png"

    - id: KDE-Desktop
      name: "Plasma Desktop"
      description: "Use Plasma to surf the web."
      screenshot: "/etc/calamares/images/kde.webp"

    - id: GNOME-Desktop
      name: "GNOME"
      screenshot: "/etc/calamares/images/gnome.webp"

    - id: Openbox
      name: "Openbox"
      screenshot: "/etc/calamares/images/openbox.jxl"
"""

BOOTLOADERS = """\
items:
    - id: grub
      name: "GRUB"
      description: "GRUB is the oldest."
      screenshot: "/etc/calamares/images/bootloaders/grub.jxl"
    - id: limine
      name: "Limine"
      screenshot: "/etc/calamares/images/bootloaders/limine.jxl"
"""

MORE_GROUPS = NETINSTALL + """\
- name: "GNOME-Desktop"
  description: "GNOME desktop environment"
  packages:
    - gnome-shell
    - cachyos-gnome-settings
- name: "CachyOS Handhelds"
  packages:
    - cachyos-handheld
- name: "Openbox"
  packages:
    - openbox
- name: "Printing-Support"
  description: "Printers, as CachyOS configures them"
  packages:
    - cups
"""


class Choosers(unittest.TestCase):
    def test_only_plasma_and_no_desktop_are_offered(self):
        text = installer.patch_packagechooser_desktop(DESKTOPS)
        ids = [line.strip() for line in text.split("\n") if line.startswith("    - id:")]
        self.assertEqual(ids, ['- id: ""', "- id: KDE-Desktop"])
        self.assertNotIn("GNOME", text)
        self.assertIn("default: KDE-Desktop", text)

    def test_plasma_gets_our_picture_and_no_desktop_keeps_its_own(self):
        text = installer.patch_packagechooser_desktop(DESKTOPS)
        self.assertIn('screenshot: "%s"' % installer.DESKTOP_PREVIEW, text)
        self.assertIn('screenshot: ":/images/no-selection.png"', text)
        self.assertNotIn("kde.webp", text)

    def test_the_desktop_chooser_is_idempotent(self):
        once = installer.patch_packagechooser_desktop(DESKTOPS)
        self.assertEqual(installer.patch_packagechooser_desktop(once), once)

    def test_a_file_without_items_is_left_alone(self):
        self.assertEqual(installer.patch_packagechooser_desktop("mode: required\n"), "mode: required\n")

    def test_the_boot_loader_chooser_loses_the_cachyos_pictures(self):
        text = installer.patch_packagechooser_bootloader(BOOTLOADERS)
        self.assertNotIn("screenshot", text)
        self.assertIn('name: "Limine"', text)
        self.assertIn("GRUB is the oldest.", text)

    def test_other_desktops_and_handhelds_leave_the_package_list(self):
        text = installer.patch_netinstall_yaml(MORE_GROUPS)
        for name in ("GNOME-Desktop", "CachyOS Handhelds", "Openbox", "gnome-shell", "cachyos-handheld"):
            self.assertNotIn(name, text)
        for name in ("KDE-Desktop", "Printing-Support", "plasma-meta", "cups"):
            self.assertIn(name, text)

    def test_descriptions_that_are_shown_name_oziOS(self):
        text = installer.patch_netinstall_yaml(MORE_GROUPS)
        self.assertIn('description: "Printers, as OziOS configures them"', text)


class Timeouts(unittest.TestCase):
    def test_a_step_without_a_timeout_gets_room(self):
        out = installer.patch_shellprocess_timeout("---\ndontChroot: true\nscript:\n - a\n")
        self.assertEqual(out.split("\n")[:3], ["---", "timeout: 600", "dontChroot: true"])

    def test_a_short_timeout_is_raised_and_a_long_one_kept(self):
        self.assertIn("timeout: 600", installer.patch_shellprocess_timeout("timeout: 10\nscript:\n"))
        self.assertEqual(installer.patch_shellprocess_timeout("timeout: 3600\nscript:\n"), "timeout: 3600\nscript:\n")

    def test_a_file_without_a_document_marker_gets_the_key_first(self):
        self.assertTrue(installer.patch_shellprocess_timeout("script:\n - a\n").startswith("timeout: 600\n"))

    def test_idempotent(self):
        once = installer.patch_shellprocess_timeout("---\nscript:\n")
        self.assertEqual(installer.patch_shellprocess_timeout(once), once)


class Welcome(unittest.TestCase):
    def test_the_internet_check_does_not_ask_cachyos(self):
        out = installer.patch_welcome("    internetCheckUrl:   https://wiki.cachyos.org\n    #internetCheckUrl: x\n")
        self.assertIn("https://archlinux.org", out)
        self.assertNotIn("cachyos", out)


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
