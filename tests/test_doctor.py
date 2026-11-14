import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

sys.path.insert(0, os.path.dirname(__file__))
import lang  # noqa: E402,F401  tests run in English

from ozipkg import doctor  # noqa: E402

GIB = 1024 ** 3

OS_RELEASE = 'NAME="OziOS"\nOZIOS_VERSION=0.1.1\nID=cachyos\n'
LSPCI_NVIDIA_INTEL = (
    "00:02.0 VGA compatible controller [0300]: Intel Corporation HD Graphics 5500 [8086:1616] (rev 09)\n"
    "01:00.0 3D controller [0302]: NVIDIA Corporation GM108M [GeForce 940M] [10de:134d] (rev a2)\n"
    "00:1f.3 Audio device [0403]: Intel Corporation Wildcat Point-LP High Definition Audio [8086:9ca0]\n")


class Fake(doctor.Probe):
    """A machine that exists only in the test."""

    def __init__(self, files=None, commands=None, programs=(), disk=None, release="7.1.6-1-ozios", user="ozi"):
        self.files = dict(files or {})
        self.commands = dict(commands or {})
        self.programs = set(programs)
        self.disk = dict(disk or {})
        self.rel = release
        self.usr = user

    def read(self, path):
        return self.files.get(path)

    def exists(self, path):
        return path in self.files

    def which(self, name):
        return name in self.programs

    def run(self, argv, timeout=15):
        return self.commands.get(tuple(argv), (127, ""))

    def usage(self, path):
        return self.disk.get(path)

    def release(self):
        return self.rel

    def user(self):
        return self.usr


def levels(checks):
    return {c.id: c.level for c in checks}


class Helpers(unittest.TestCase):
    def test_keyvalue_strips_quotes_and_comments(self):
        self.assertEqual(doctor.parse_keyvalue('# x\nNAME="OziOS"\nID=cachyos\nbad line\n'), {"NAME": "OziOS", "ID": "cachyos"})

    def test_sizes(self):
        self.assertEqual(doctor.human_size(3 * GIB // 2), "1.5 GiB")
        self.assertEqual(doctor.human_size(300 * 1024 ** 2), "300.0 MiB")

    def test_gpus_are_found_by_class_and_vendor(self):
        self.assertEqual([v for v, _ in doctor.pci_gpus(LSPCI_NVIDIA_INTEL)], ["intel", "nvidia"])
        self.assertIn("GeForce 940M", doctor.pci_gpus(LSPCI_NVIDIA_INTEL)[1][1])

    def test_meminfo(self):
        self.assertEqual(doctor.parse_meminfo("MemTotal:  4096 kB\nSwapTotal: 8 kB\n")["MemTotal"], 4096 * 1024)


class Kernel(unittest.TestCase):
    def test_our_kernel_is_fine(self):
        fake = Fake(files={"/usr/lib/modules/7.1.6-1-ozios": ""})
        self.assertEqual(levels(doctor.check_kernel(fake)), {"kernel": "ok"})

    def test_another_kernel_is_a_warning_with_a_fix(self):
        fake = Fake(release="6.12.1-arch1", files={"/usr/lib/modules/6.12.1-arch1": ""})
        (check,) = doctor.check_kernel(fake)
        self.assertEqual(check.level, "warn")
        self.assertIn("linux-ozios", check.hint)

    def test_missing_modules_means_restart(self):
        self.assertEqual(levels(doctor.check_kernel(Fake()))["kernel-modules"], "warn")


class Identity(unittest.TestCase):
    def test_ours(self):
        (check,) = doctor.check_identity(Fake(files={"/etc/os-release": OS_RELEASE}))
        self.assertEqual((check.level, check.title), ("ok", "OziOS 0.1.1"))

    def test_the_edition_is_named(self):
        text = OS_RELEASE + 'VARIANT="Education"\n'
        (check,) = doctor.check_identity(Fake(files={"/etc/os-release": text}))
        self.assertIn("Education", check.title)

    def test_somebody_elses_os_release(self):
        (check,) = doctor.check_identity(Fake(files={"/etc/os-release": 'NAME="Arch Linux"\n'}))
        self.assertEqual(check.level, "warn")
        self.assertIn("identity", check.hint)


class Virtualization(unittest.TestCase):
    def test_on(self):
        fake = Fake(files={"/proc/cpuinfo": "flags : fpu vmx sse", "/dev/kvm": ""})
        self.assertEqual(levels(doctor.check_virtualization(fake)), {"kvm": "ok"})

    def test_capable_but_off(self):
        fake = Fake(files={"/proc/cpuinfo": "flags : fpu svm sse"})
        self.assertEqual(levels(doctor.check_virtualization(fake)), {"kvm": "warn"})

    def test_not_capable_is_only_information(self):
        fake = Fake(files={"/proc/cpuinfo": "flags : fpu sse"})
        self.assertEqual(levels(doctor.check_virtualization(fake)), {"kvm": "info"})


class Gpu(unittest.TestCase):
    commands = {("lspci", "-nn"): (0, LSPCI_NVIDIA_INTEL)}

    def test_everything_loaded(self):
        fake = Fake(files={"/proc/modules": "i915 1 0\nnvidia 1 0\n"}, commands=self.commands)
        result = doctor.check_gpu(fake)
        self.assertEqual([c.level for c in result], ["ok", "ok", "info"])
        self.assertIn("ozi play", result[-1].hint)

    def test_a_missing_nvidia_driver_is_a_warning_with_a_fix(self):
        fake = Fake(files={"/proc/modules": "i915 1 0\n"}, commands=self.commands)
        warn = [c for c in doctor.check_gpu(fake) if c.level == "warn"]
        self.assertEqual(len(warn), 1)
        self.assertIn("chwd", warn[0].hint)

    def test_no_lspci(self):
        self.assertEqual(levels(doctor.check_gpu(Fake())), {"gpu": "info"})


class Disk(unittest.TestCase):
    def test_plenty(self):
        self.assertEqual(levels(doctor.check_disk(Fake(disk={"/": (100 * GIB, 60 * GIB)}))), {"disk": "ok"})

    def test_getting_full(self):
        # under a tenth free, or under 5 GiB, is a warning
        self.assertEqual(levels(doctor.check_disk(Fake(disk={"/": (100 * GIB, 12 * GIB)}))), {"disk": "ok"})
        self.assertEqual(levels(doctor.check_disk(Fake(disk={"/": (100 * GIB, 8 * GIB)}))), {"disk": "warn"})
        self.assertEqual(levels(doctor.check_disk(Fake(disk={"/": (20 * GIB, 4 * GIB)}))), {"disk": "warn"})

    def test_almost_full_is_a_failure(self):
        (check,) = doctor.check_disk(Fake(disk={"/": (100 * GIB, 1 * GIB)}))
        self.assertEqual((check.level, check.hint), ("fail", "ozi clean"))

    def test_a_small_boot_partition(self):
        fake = Fake(disk={"/": (100 * GIB, 60 * GIB), "/boot": (512 * 1024 ** 2, 40 * 1024 ** 2)})
        self.assertEqual(levels(doctor.check_disk(fake)), {"disk": "ok", "boot-space": "warn"})

    def test_boot_on_the_same_disk_is_not_checked_twice(self):
        fake = Fake(disk={"/": (100 * GIB, 60 * GIB), "/boot": (100 * GIB, 60 * GIB)})
        self.assertEqual(levels(doctor.check_disk(fake)), {"disk": "ok"})


class Packages(unittest.TestCase):
    conf = "[options]\nHoldPkg = pacman\n[cachyos]\nInclude = x\n[core]\nInclude = y\n[extra]\nInclude = y\n"

    def test_a_stale_lock_is_reported_when_no_pacman_runs(self):
        fake = Fake(files={"/var/lib/pacman/db.lck": "", "/etc/pacman.conf": self.conf},
                    commands={("pgrep", "-x", "pacman"): (1, "")})
        self.assertEqual(levels(doctor.check_packages(fake))["pacman-lock"], "warn")

    def test_a_lock_while_pacman_runs_is_normal(self):
        fake = Fake(files={"/var/lib/pacman/db.lck": "", "/etc/pacman.conf": self.conf},
                    commands={("pgrep", "-x", "pacman"): (0, "123\n")})
        self.assertNotIn("pacman-lock", levels(doctor.check_packages(fake)))

    def test_repositories_are_listed_without_options(self):
        result = doctor.check_packages(Fake(files={"/etc/pacman.conf": self.conf}))
        repos = [c for c in result if c.id == "repos"][0]
        self.assertEqual(repos.title, "Repositories: cachyos, core, extra")

    def test_no_repositories_is_a_failure(self):
        self.assertEqual(levels(doctor.check_packages(Fake(files={"/etc/pacman.conf": "[options]\n"})))["repos"], "fail")

    def test_updates_and_orphans(self):
        fake = Fake(files={"/etc/pacman.conf": self.conf}, programs=["checkupdates"],
                    commands={("checkupdates",): (0, "a 1 -> 2\nb 3 -> 4\n"), ("pacman", "-Qdtq"): (0, "old1\nold2\nold3\n")})
        result = {c.id: c for c in doctor.check_packages(fake)}
        self.assertEqual(result["updates"].title, "2 updates waiting")
        self.assertEqual(result["orphans"].title, "3 packages are no longer needed")

    def test_up_to_date_and_offline(self):
        base = {"files": {"/etc/pacman.conf": self.conf}, "programs": ["checkupdates"]}
        self.assertEqual(levels(doctor.check_packages(Fake(commands={("checkupdates",): (2, "")}, **base)))["updates"], "ok")
        self.assertEqual(levels(doctor.check_packages(Fake(commands={("checkupdates",): (1, "")}, **base)))["updates"], "info")


class Boxes(unittest.TestCase):
    helper = {"/usr/lib/ozios/ozi-pkg-helper": "", "/usr/share/polkit-1/actions/org.ozios.pkg.manage.policy": ""}

    def test_everything_there(self):
        fake = Fake(programs=["podman", "bwrap"], files={**self.helper, "/etc/subuid": "ozi:100000:65536\n", "/etc/subgid": "ozi:100000:65536\n"})
        self.assertEqual(levels(doctor.check_boxes(fake)), {"podman": "ok"})

    def test_missing_subids_are_information(self):
        fake = Fake(programs=["podman", "bwrap"], files={**self.helper, "/etc/subuid": "", "/etc/subgid": ""})
        self.assertEqual(levels(doctor.check_boxes(fake))["subids"], "info")

    def test_missing_programs_and_helper(self):
        result = levels(doctor.check_boxes(Fake()))
        self.assertEqual(result, {"podman": "info", "bwrap": "info", "helper": "fail"})


class Snapshots(unittest.TestCase):
    def test_not_btrfs(self):
        fake = Fake(files={"/proc/mounts": "/dev/sda2 / ext4 rw 0 0\n"})
        self.assertEqual(levels(doctor.check_snapshots(fake)), {"snapshots": "info"})

    def test_btrfs_without_snapper(self):
        fake = Fake(files={"/proc/mounts": "/dev/sda2 / btrfs rw 0 0\n"})
        self.assertEqual(levels(doctor.check_snapshots(fake)), {"snapshots": "warn"})

    def test_btrfs_with_a_root_config(self):
        fake = Fake(files={"/proc/mounts": "/dev/sda2 / btrfs rw 0 0\n"}, programs=["snapper"],
                    commands={("snapper", "list-configs"): (0, "Config | Subvolume\n-------+----------\nroot   | /\n")})
        self.assertEqual(levels(doctor.check_snapshots(fake)), {"snapshots": "ok"})


class Rest(unittest.TestCase):
    def test_time(self):
        cmd = ("timedatectl", "show", "-p", "NTPSynchronized", "--value")
        self.assertEqual(levels(doctor.check_time(Fake(commands={cmd: (0, "yes\n")}))), {"time": "ok"})
        self.assertEqual(levels(doctor.check_time(Fake(commands={cmd: (0, "no\n")}))), {"time": "warn"})
        self.assertEqual(doctor.check_time(Fake()), [])

    def test_failed_services_are_named(self):
        cmd = ("systemctl", "--failed", "--no-legend", "--plain")
        text = "".join("svc%d.service loaded failed failed X\n" % n for n in range(7))
        (check,) = doctor.check_services(Fake(commands={cmd: (0, text)}))
        self.assertEqual(check.level, "warn")
        self.assertIn("svc0.service", check.title)
        self.assertIn("...", check.title)
        self.assertEqual(levels(doctor.check_services(Fake(commands={cmd: (0, "")}))), {"services": "ok"})

    def test_network(self):
        table = "Iface\tDestination\tGateway\nenp0s3\t00000000\t0102000A\n"
        self.assertEqual(levels(doctor.check_network(Fake(files={"/proc/net/route": table}))), {"network": "ok"})
        self.assertEqual(levels(doctor.check_network(Fake(files={"/proc/net/route": "Iface\tDestination\n"}))), {"network": "info"})

    def test_memory_and_zram(self):
        small = Fake(files={"/proc/meminfo": "MemTotal: 2000000 kB\n", "/proc/swaps": "/dev/zram0 partition\n"})
        self.assertEqual(levels(doctor.check_memory(small)), {"memory": "warn", "zram": "ok"})
        big = Fake(files={"/proc/meminfo": "MemTotal: 8000000 kB\n"})
        self.assertEqual(levels(doctor.check_memory(big)), {"memory": "ok"})

    def test_firmware(self):
        self.assertEqual(doctor.check_firmware(Fake(files={"/sys/firmware/efi": ""}))[0].title, "Started in UEFI mode")
        self.assertEqual(doctor.check_firmware(Fake())[0].title, "Started in BIOS mode")

    def test_the_education_edition_is_only_checked_where_it_exists(self):
        self.assertEqual(doctor.check_edition(Fake()), [])
        edu = Fake(files={"/usr/share/ozios/edition": "edu\n"}, programs=["ozi-pen", "ozi-classroom", "xournalpp", "okular"])
        self.assertEqual(levels(doctor.check_edition(edu)), {"edu": "ok"})
        stale = Fake(files={"/usr/share/ozios/edition": "edu\n"}, programs=["ozi-pen", "xournalpp", "okular"])
        self.assertIn("ozi-classroom", doctor.check_edition(stale)[0].title)
        self.assertEqual(levels(doctor.check_edition(Fake(files={"/usr/share/ozios/edition": "edu\n"}))), {"edu": "warn"})


class Whole(unittest.TestCase):
    def machine(self):
        return Fake(files={"/etc/os-release": OS_RELEASE, "/usr/lib/modules/7.1.6-1-ozios": "",
                           "/etc/pacman.conf": "[core]\n", "/proc/meminfo": "MemTotal: 8000000 kB\n",
                           "/usr/lib/ozios/ozi-pkg-helper": "",
                           "/usr/share/polkit-1/actions/org.ozios.pkg.manage.policy": ""},
                    disk={"/": (100 * GIB, 60 * GIB)}, programs=["podman", "bwrap"])

    def test_a_healthy_machine(self):
        checks = doctor.run_checks(self.machine())
        self.assertNotIn(doctor.worst(checks), ("warn", "fail"))
        lines = []
        self.assertEqual(doctor.main([], out=lines.append, probe=self.machine()), 0)
        self.assertIn("Everything looks fine.", lines[0])

    def test_a_broken_check_does_not_hide_the_others(self):
        probe = self.machine()
        probe.read = lambda path: (_ for _ in ()).throw(RuntimeError("boom"))
        checks = doctor.run_checks(probe)
        self.assertTrue(any("boom" in c.title for c in checks))
        self.assertGreater(len(checks), 3)

    def test_json_output(self):
        lines = []
        doctor.main(["--json"], out=lines.append, probe=self.machine())
        data = json.loads(lines[0])
        self.assertIn(data["worst"], doctor.LEVELS)
        self.assertTrue(all({"id", "level", "title", "detail", "hint"} <= set(c) for c in data["checks"]))

    def test_quiet_shows_only_what_needs_a_look(self):
        probe = self.machine()
        probe.disk = {"/": (100 * GIB, 1 * GIB)}
        lines = []
        code = doctor.main(["--quiet"], out=lines.append, probe=probe)
        self.assertEqual(code, 1)
        self.assertIn("FAIL", lines[0])
        self.assertNotIn("Kernel", lines[0])
        self.assertIn("1 problems need attention.", lines[0])


if __name__ == "__main__":
    unittest.main()
