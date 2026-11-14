import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "packages", "ozios-settings", "install-to-target")
BASH = shutil.which("bash")

# Stands in for arch-chroot: logs what it was asked to run and does what pacman would to the files that matter.
ARCH_CHROOT = r"""#!/bin/bash
echo "chroot $*" >> "$FAKE_LOG"
root="$1"; shift
[ "$1" = pacman ] || exit 0
shift
args="$*"
last="${args##* }"
case "$args" in
  *-Qq*) cat "$FAKE_INSTALLED" 2>/dev/null; exit 0 ;;
  *-U\ *)
    if [ -n "$FAKE_FAIL" ] && echo "$last" | grep -q "$FAKE_FAIL"; then exit 1; fi
    case "$last" in
      */linux-ozios-7*) mkdir -p "$root/usr/lib/modules/7.1.6-1-ozios"; touch "$root/usr/lib/modules/7.1.6-1-ozios/vmlinuz" ;;
    esac
    exit 0 ;;
  *-S\ linux)
    [ -n "$FAKE_NO_ARCH_KERNEL" ] && exit 1
    mkdir -p "$root/usr/lib/modules/6.99-arch"; touch "$root/usr/lib/modules/6.99-arch/vmlinuz"; exit 0 ;;
esac
exit 0
"""
PLAIN = '#!/bin/bash\necho "$(basename "$0") $*" >> "$FAKE_LOG"\n'
GRUB_DEFAULTS = 'GRUB_DISTRIBUTOR="CachyOS"\n#GRUB_THEME="/usr/share/grub/themes/cachyos/theme.txt"\nGRUB_TIMEOUT=5\n'


def executable(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


@unittest.skipUnless(BASH, "bash is not available here")
class Stages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = self.tmp.name
        self.bin, self.packages, self.target = (os.path.join(base, n) for n in ("bin", "medium", "target"))
        self.log = os.path.join(base, "calls.log")
        self.installed = os.path.join(base, "installed")
        for folder in (self.bin, self.packages, self.target):
            os.mkdir(folder)
        executable(os.path.join(self.bin, "arch-chroot"), ARCH_CHROOT)
        for name in ("pacman", "kernel-install"):
            executable(os.path.join(self.bin, name), PLAIN)
        for name in ("ozios-settings-0.1.1-1-any", "ozios-edu-0.1.1-1-any", "linux-ozios-7.1.6-1-x86_64",
                     "linux-ozios-nvidia-open-7.1.6-1-x86_64", "linux-ozios-zfs-7.1.6-1-x86_64"):
            for suffix in (".pkg.tar.zst", ".pkg.tar.zst.sig"):
                open(os.path.join(self.packages, name + suffix), "w").close()

    def tearDown(self):
        self.tmp.cleanup()

    def run_stage(self, stage, **extra):
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], OZIOS_PACKAGES=self.packages,
                   OZIOS_TARGET=self.target, FAKE_LOG=self.log, FAKE_INSTALLED=self.installed,
                   FAKE_FAIL="", FAKE_NO_ARCH_KERNEL="")
        env.update(extra)
        done = subprocess.run([BASH, SCRIPT, stage], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout + done.stderr

    def calls(self):
        try:
            with open(self.log, encoding="utf-8") as fh:
                return fh.read().strip().split("\n")
        except OSError:
            return []

    def installs(self):
        """The package files handed to pacman -U, in order."""
        return [os.path.basename(line.split()[-1]) for line in self.calls() if " -U " in line]

    def test_the_settings_come_first_then_the_edition_then_the_kernel(self):
        self.run_stage("early")
        names = [re.sub(r"-[0-9].*", "", n) for n in self.installs()]
        self.assertEqual(names, ["ozios-settings", "ozios-edu", "linux-ozios", "linux-ozios-nvidia-open"])

    def test_signatures_and_the_zfs_modules_are_left_alone(self):
        self.run_stage("early")
        self.assertFalse([n for n in self.installs() if n.endswith(".sig") or "zfs" in n])

    def test_the_packages_are_kept_in_the_new_system_for_later(self):
        self.run_stage("early")
        kept = os.listdir(os.path.join(self.target, "opt", "ozios"))
        self.assertIn("linux-ozios-nvidia-open-7.1.6-1-x86_64.pkg.tar.zst", kept)

    def test_cachyos_kernels_and_programs_go_once_ours_is_in(self):
        with open(self.installed, "w") as fh:
            fh.write("base\nlinux-cachyos\nlinux-cachyos-headers\nlinux-cachyos-lts\ncachyos-hello\nlinux-ozios\ncachyos-settings\n")
        self.run_stage("early")
        removal = [line for line in self.calls() if " -Rdd " in line]
        self.assertEqual(len(removal), 1)
        for gone in ("linux-cachyos", "linux-cachyos-headers", "linux-cachyos-lts", "cachyos-hello"):
            self.assertRegex(removal[0], r"\b%s\b" % re.escape(gone))
        self.assertNotIn("linux-ozios", removal[0])
        self.assertNotIn("cachyos-settings", removal[0])      # not a kernel or a program people see

    def test_without_our_kernel_the_arch_one_is_installed(self):
        self.run_stage("early", FAKE_FAIL="linux-ozios")
        self.assertTrue([line for line in self.calls() if line.endswith("pacman --noconfirm --needed -S linux")])

    def test_when_nothing_boots_the_cachyos_kernel_is_not_taken_away(self):
        with open(self.installed, "w") as fh:
            fh.write("linux-cachyos\n")
        out = self.run_stage("early", FAKE_FAIL="linux-ozios", FAKE_NO_ARCH_KERNEL="1")
        self.assertFalse([line for line in self.calls() if " -Rdd " in line])
        self.assertIn("could not install the Arch kernel", out)

    def test_a_failing_package_manager_never_fails_the_installation(self):
        self.run_stage("early", FAKE_FAIL="ozios")
        self.run_stage("late")

    def test_nothing_mounted_means_nothing_to_do(self):
        executable(os.path.join(self.bin, "findmnt"), "#!/bin/sh\nexit 0\n")
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], OZIOS_PACKAGES=self.packages,
                   OZIOS_TARGET="", FAKE_LOG=self.log)
        done = subprocess.run([BASH, SCRIPT, "early"], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0)
        self.assertIn("nothing to do", done.stdout)
        self.assertEqual(self.calls(), [])

    def test_the_boot_menu_names_the_system_and_lists_our_kernel_first(self):
        for folder in ("boot/grub", "etc/default", "usr/share/grub/themes/ozios"):
            os.makedirs(os.path.join(self.target, folder))
        open(os.path.join(self.target, "boot", "grub", "grub.cfg"), "w").close()
        open(os.path.join(self.target, "usr", "share", "grub", "themes", "ozios", "theme.txt"), "w").close()
        defaults = os.path.join(self.target, "etc", "default", "grub")
        with open(defaults, "w") as fh:
            fh.write(GRUB_DEFAULTS)
        self.run_stage("late")
        with open(defaults) as fh:
            text = fh.read()
        self.assertIn('GRUB_DISTRIBUTOR="OziOS"', text)
        self.assertIn('GRUB_TOP_LEVEL="/boot/vmlinuz-linux-ozios"', text)
        self.assertIn('GRUB_THEME="/usr/share/grub/themes/ozios/theme.txt"', text)
        self.assertNotIn("CachyOS", text)
        self.assertTrue([line for line in self.calls() if "grub-mkconfig -o /boot/grub/grub.cfg" in line])

    def test_limine_loses_the_empty_group_the_installer_wrote_first(self):
        os.makedirs(os.path.join(self.target, "boot"))
        conf = os.path.join(self.target, "boot", "limine.conf")
        with open(conf, "w") as fh:
            fh.write("timeout: 5\ndefault_entry: 2\n\n/+CachyOS\n/+OziOS\ncomment: OziOS\n  //linux-ozios\n  protocol: linux\n")
        self.run_stage("late")
        with open(conf) as fh:
            text = fh.read()
        self.assertNotIn("CachyOS", text)
        self.assertIn("/+OziOS", text)
        self.assertIn("//linux-ozios", text)
        self.assertEqual(self.calls(), [])               # nothing was run for it

    def test_a_limine_config_without_the_group_is_left_alone(self):
        os.makedirs(os.path.join(self.target, "boot"))
        conf = os.path.join(self.target, "boot", "limine.conf")
        original = "timeout: 5\ndefault_entry: 2\n/+OziOS\n  //linux-ozios\n"
        with open(conf, "w") as fh:
            fh.write(original)
        self.run_stage("late")
        with open(conf) as fh:
            self.assertEqual(fh.read(), original)

    def test_a_boot_menu_that_is_not_grub_is_left_as_it_was(self):
        out = self.run_stage("late")
        self.assertEqual(self.calls(), [])
        self.assertNotIn("grub-mkconfig", out)


if __name__ == "__main__":
    unittest.main()
