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
if [ "$1" = sh ]; then
  case "$*" in
    *repo-add*) [ -n "$FAKE_NO_REPO" ] && exit 1; touch "$root/opt/ozios/ozios.db.tar.gz" ;;
  esac
  exit 0
fi
[ "$1" = pacman ] || exit 0
shift
args="$*"
last="${args##* }"
fails() { [ -n "$FAKE_FAIL" ] && echo "$1" | grep -q "$FAKE_FAIL"; }
ours() { mkdir -p "$root/usr/lib/modules/7.1.6-1-ozios"; touch "$root/usr/lib/modules/7.1.6-1-ozios/vmlinuz"; }
case "$args" in
  *-Qq*) cat "$FAKE_INSTALLED" 2>/dev/null; exit 0 ;;
  *-U\ *)
    fails "$last" && exit 1
    case "$last" in
      */linux-ozios-7*) ours ;;
    esac
    exit 0 ;;
  *-S\ linux-ozios\ *)
    { fails linux-ozios || [ -n "$FAKE_NO_REPO" ]; } && exit 1
    ours; exit 0 ;;
  *-S\ linux\ linux-headers)
    [ -n "$FAKE_NO_ARCH_KERNEL" ] && exit 1
    mkdir -p "$root/usr/lib/modules/6.99-arch"; touch "$root/usr/lib/modules/6.99-arch/vmlinuz"; exit 0 ;;
esac
exit 0
"""
PLAIN = '#!/bin/bash\necho "$(basename "$0") $*" >> "$FAKE_LOG"\n'
GRUB_DEFAULTS = 'GRUB_DISTRIBUTOR="CachyOS"\n#GRUB_THEME="/usr/share/grub/themes/cachyos/theme.txt"\nGRUB_TIMEOUT=5\n'
PACMAN_CONF = "[options]\nArchitecture = auto\n\n[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\n\n[core]\nInclude = /etc/pacman.d/mirrorlist\n"


def executable(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


class Target(unittest.TestCase):
    """A fake installation target and stand-ins for the programs the stages call."""
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
        # Never the real os-prober: it would scan this machine's disks.
        executable(os.path.join(self.bin, "os-prober"), '#!/bin/bash\nprintf "%s" "$FAKE_OS_PROBER"\n')
        for name in ("ozios-settings-0.1.1-1-any", "ozios-edu-0.1.1-1-any", "linux-ozios-7.1.6-1-x86_64",
                     "linux-ozios-headers-7.1.6-1-x86_64", "linux-ozios-nvidia-open-7.1.6-1-x86_64",
                     "linux-ozios-zfs-7.1.6-1-x86_64"):
            for suffix in (".pkg.tar.zst", ".pkg.tar.zst.sig"):
                open(os.path.join(self.packages, name + suffix), "w").close()
        os.makedirs(os.path.join(self.target, "etc"))
        with open(self.pacman_conf(), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(PACMAN_CONF)

    def tearDown(self):
        self.tmp.cleanup()

    def pacman_conf(self):
        return os.path.join(self.target, "etc", "pacman.conf")

    def run_stage(self, stage, **extra):
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], OZIOS_PACKAGES=self.packages,
                   OZIOS_TARGET=self.target, FAKE_LOG=self.log, FAKE_INSTALLED=self.installed,
                   FAKE_FAIL="", FAKE_NO_ARCH_KERNEL="", FAKE_NO_REPO="", FAKE_OS_PROBER="")
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

    def has_our_kernel(self):
        return os.path.isfile(os.path.join(self.target, "usr", "lib", "modules", "7.1.6-1-ozios", "vmlinuz"))


@unittest.skipUnless(BASH, "bash is not available here")
class Stages(Target):
    # --- kernel stage: before the driver step -------------------------------------

    def test_the_kernel_stage_makes_a_package_source_of_the_ozios_packages(self):
        self.run_stage("kernel")
        repo_add = [line for line in self.calls() if "repo-add" in line]
        self.assertEqual(len(repo_add), 1)
        for name in ("linux-ozios-7.1.6-1-x86_64.pkg.tar.zst", "linux-ozios-headers-7.1.6-1-x86_64.pkg.tar.zst",
                     "ozios-settings-0.1.1-1-any.pkg.tar.zst"):
            self.assertIn(name, repo_add[0])
        self.assertNotIn(".sig", repo_add[0])
        with open(self.pacman_conf(), encoding="utf-8") as fh:
            conf = fh.read()
        self.assertTrue(conf.startswith(PACMAN_CONF))                     # the rest of the file is kept
        self.assertIn("[ozios]\nSigLevel = Optional TrustAll\nServer = file:///opt/ozios\n", conf)
        self.assertTrue(os.path.isfile(os.path.join(self.target, "var", "lib", "pacman", "sync", "ozios.db")))

    def test_the_kernel_and_its_headers_are_installed_by_name(self):
        self.run_stage("kernel")
        self.assertTrue([line for line in self.calls() if line.endswith("pacman --noconfirm --needed -S linux-ozios linux-ozios-headers")])
        self.assertEqual(self.installs(), [])
        self.assertTrue(self.has_our_kernel())

    def test_the_package_source_is_added_once(self):
        self.run_stage("kernel")
        self.run_stage("kernel")
        with open(self.pacman_conf(), encoding="utf-8") as fh:
            self.assertEqual(fh.read().count("[ozios]"), 1)

    def test_without_the_package_source_the_kernel_comes_from_the_files(self):
        self.run_stage("kernel", FAKE_NO_REPO="1")
        names = [re.sub(r"-[0-9].*", "", n) for n in self.installs()]
        self.assertEqual(names, ["linux-ozios", "linux-ozios-headers"])
        self.assertTrue(self.has_our_kernel())

    def test_prebuilt_nvidia_and_zfs_modules_are_left_to_the_driver_step(self):
        # The driver step builds the NVIDIA module for the driver version it installs (DKMS);
        # a module built months earlier would not match it after the first update.
        self.run_stage("kernel", FAKE_NO_REPO="1")
        self.run_stage("early")
        installing = [line for line in self.calls() if " -S " in line or " -U " in line]
        self.assertFalse([line for line in installing if "nvidia" in line or "zfs" in line])

    def test_the_packages_are_kept_in_the_new_system_for_later(self):
        self.run_stage("kernel")
        kept = os.listdir(os.path.join(self.target, "opt", "ozios"))
        self.assertIn("linux-ozios-nvidia-open-7.1.6-1-x86_64.pkg.tar.zst", kept)

    def test_without_our_kernel_the_arch_one_is_installed(self):
        self.run_stage("kernel", FAKE_FAIL="linux-ozios")
        self.assertTrue([line for line in self.calls() if line.endswith("pacman --noconfirm --needed -S linux linux-headers")])

    # --- early stage: after the extra packages ------------------------------------

    def test_the_settings_come_first_then_the_edition(self):
        self.run_stage("kernel")
        self.run_stage("early")
        names = [re.sub(r"-[0-9].*", "", n) for n in self.installs()]
        self.assertEqual(names, ["ozios-settings", "ozios-edu"])
        self.assertEqual(len([line for line in self.calls() if "-S linux-ozios" in line]), 1)   # not again

    def test_signatures_are_left_alone(self):
        self.run_stage("early")
        self.assertFalse([n for n in self.installs() if n.endswith(".sig")])

    def test_an_installer_without_the_kernel_stage_still_gets_the_kernel(self):
        self.run_stage("early")
        self.assertTrue(self.has_our_kernel())

    def test_the_boot_splash_is_set_before_the_initramfs_is_built(self):
        theme = os.path.join(self.target, "usr", "share", "plymouth", "themes", "ozios")
        os.makedirs(theme)
        open(os.path.join(theme, "ozios.plymouth"), "w").close()
        tool = os.path.join(self.target, "usr", "bin", "plymouth-set-default-theme")
        os.makedirs(os.path.dirname(tool))
        executable(tool, "#!/bin/sh\n")
        self.run_stage("early")
        self.assertTrue([line for line in self.calls() if line.endswith("plymouth-set-default-theme ozios")])

    def test_without_plymouth_the_splash_is_left_alone(self):
        self.run_stage("early")
        self.assertFalse([line for line in self.calls() if "plymouth" in line])

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

    def test_when_nothing_boots_the_cachyos_kernel_is_not_taken_away(self):
        with open(self.installed, "w") as fh:
            fh.write("linux-cachyos\n")
        out = self.run_stage("early", FAKE_FAIL="linux-ozios", FAKE_NO_ARCH_KERNEL="1")
        self.assertFalse([line for line in self.calls() if " -Rdd " in line])
        self.assertIn("could not install the Arch kernel", out)

    def test_a_failing_package_manager_never_fails_the_installation(self):
        self.run_stage("kernel", FAKE_FAIL="ozios", FAKE_NO_REPO="1")
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


@unittest.skipUnless(BASH, "bash is not available here")
class LateStage(Target):
    """The last step: VirtualBox's shared folders, and the clock next to Windows."""

    def write(self, relative, text):
        path = os.path.join(self.target, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return path

    def adjtime(self):
        try:
            with open(os.path.join(self.target, "etc", "adjtime"), encoding="utf-8") as fh:
                return fh.read().splitlines()
        except OSError:
            return None

    def test_people_can_open_the_virtualbox_shared_folders(self):
        self.write("etc/group", "root:x:0:\nwheel:x:998:tester\nvboxsf:x:109:\n")
        self.write("etc/passwd", "root:x:0:0::/root:/bin/bash\nsvc:x:970:970::/:/usr/bin/nologin\n"
                                 "tester:x:1000:1000::/home/tester:/bin/bash\nnobody:x:65534:65534::/:/usr/bin/nologin\n")
        self.run_stage("late")
        self.assertEqual([c for c in self.calls() if "gpasswd" in c],
                         ["chroot %s gpasswd -a tester vboxsf" % self.target])

    def test_outside_virtualbox_the_groups_are_left_alone(self):
        self.write("etc/group", "root:x:0:\nwheel:x:998:tester\n")
        self.write("etc/passwd", "tester:x:1000:1000::/home/tester:/bin/bash\n")
        self.run_stage("late")
        self.assertFalse([c for c in self.calls() if "gpasswd" in c])

    def test_next_to_windows_the_hardware_clock_keeps_local_time(self):
        self.write("boot/EFI/Microsoft/Boot/bootmgfw.efi", "")
        self.run_stage("late")
        self.assertEqual(self.adjtime()[2], "LOCAL")

    def test_windows_on_another_partition_counts_too(self):
        self.run_stage("late", FAKE_OS_PROBER="/dev/sda1@/EFI/Microsoft/Boot/bootmgfw.efi:Windows Boot Manager:Windows:efi\n")
        self.assertEqual(self.adjtime()[2], "LOCAL")

    def test_without_windows_the_clock_is_left_alone(self):
        self.run_stage("late")
        self.assertIsNone(self.adjtime())
