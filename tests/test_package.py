"""Static checks that catch the mistakes a build in the VM would otherwise find."""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
BASH = shutil.which("bash")
FRAMES = os.path.join(ROOT, "packages", "ozios-decoration")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class Pkgbuild(unittest.TestCase):
    def test_every_installed_source_exists(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        missing = []
        for match in re.finditer(r'"\$(?:src|here|theme_src)/([^"]+)"', text):
            rel = match.group(1)
            if "$" in rel.replace("$wallpaper", "").replace("$control", ""):
                continue
            rel = rel.replace("$wallpaper", "org.ozios.tesseract").replace("$control", "org.ozios.control")
            base = "packages/ozios-settings/" if "$here" in match.group(0) else ""
            if "theme_src" in match.group(0):
                base = "desktop/look-and-feel/org.ozios.desktop/"
            if not glob.glob(os.path.join(ROOT, base + rel)):
                missing.append(base + rel)
        self.assertEqual(missing, [])

    def test_depends_on_what_the_apps_import(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        for dep in ("python-pyqt6", "qt6-declarative", "polkit", "podman", "bubblewrap"):
            self.assertRegex(text, r"depends=\([^)]*\b%s\b" % dep)


class EducationPackage(unittest.TestCase):
    def test_every_installed_source_exists(self):
        text = read("packages", "ozios-edu", "PKGBUILD")
        missing = []
        for match in re.finditer(r'"\$src/([^"]+)"', text):
            rel = match.group(1)
            if not glob.glob(os.path.join(ROOT, rel)):
                missing.append(rel)
        self.assertEqual(missing, [])

    def test_it_needs_the_base_package_and_the_school_programs(self):
        text = read("packages", "ozios-edu", "PKGBUILD")
        for dep in ("ozios-settings", "xournalpp", "plasma-keyboard", "libreoffice-still", "libreoffice-still-tr"):
            self.assertRegex(text, r"depends=\([^)]*\b%s\b" % dep)

    def test_it_marks_the_edition_the_rest_of_the_system_looks_for(self):
        self.assertIn("echo edu >", read("packages", "ozios-edu", "PKGBUILD"))
        self.assertIn("/usr/share/ozios/edition", read("packages", "ozios-settings", "identity"))
        self.assertIn("ozios-edu", read("packages", "ozios-settings", "zz-ozios.hook"))

    def test_the_school_links_are_plain_links(self):
        for path in glob.glob(os.path.join(ROOT, "edu", "applications", "*.desktop")):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertRegex(text, r"(?m)^Exec=xdg-open https://[a-z0-9.-]+\.gov\.tr", path)


class InstallerPieces(unittest.TestCase):
    def test_branding_and_boot_files_are_in_the_package_and_exist(self):
        text = read("packages", "ozios-settings", "PKGBUILD")
        for rel in ("branding/calamares/ozios/branding.desc", "branding/boot/theme.txt", "branding/boot/background.png",
                    "branding/boot/limine-splash.png", "branding/boot/desktop.png"):
            self.assertIn(rel, text)
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)), rel)

    def test_branding_names_the_system_and_uses_our_palette(self):
        desc = read("branding", "calamares", "ozios", "branding.desc")
        self.assertIn("componentName: ozios", desc)
        self.assertIn("@VERSION@", desc)
        self.assertIn("#00E5FF", desc)
        self.assertNotIn("cachyos", desc.lower())

    def test_the_installer_steps_take_a_stage_argument(self):
        text = read("packages", "ozios-settings", "install-to-target")
        for stage in ("early", "late"):
            self.assertIn("%s)" % stage, text)


class WindowFramesPackage(unittest.TestCase):
    """packages/ozios-decoration: the compiled window frames, built on the ISO."""
    def test_it_builds_the_plugin_from_the_checkout_and_installs_its_guard(self):
        text = read("packages", "ozios-decoration", "PKGBUILD")
        self.assertIn('-S "$src/desktop/decoration"', text)
        for name in ("decoration-guard", "decoration-rebuild", "zz-ozios-decoration.hook"):
            self.assertIn('"$here/%s"' % name, text)
            self.assertTrue(os.path.isfile(os.path.join(FRAMES, name)), name)
        self.assertIn("/usr/share/ozios/decoration-built-with", text)
        self.assertRegex(text, r"\ndepends=\([^)]*\bkdecoration\b")
        self.assertRegex(text, r"makedepends=\([^)]*\bextra-cmake-modules\b")

    def test_the_source_comes_along_so_the_frames_can_be_built_again(self):
        pkgbuild = read("packages", "ozios-decoration", "PKGBUILD")
        rebuild = read("packages", "ozios-decoration", "decoration-rebuild")
        guard = read("packages", "ozios-decoration", "decoration-guard")
        src = re.search(r"(?m)^src=(\S+)$", rebuild).group(1)
        self.assertIn('-t "$pkgdir%s"' % src, pkgbuild)
        for name in ("CMakeLists.txt", "ozios.json"):
            self.assertIn('"$src/%s"' % name, pkgbuild)
        self.assertIn('"$src"/*.cpp "$src"/*.h', pkgbuild)
        # The guard finds the builder where the package puts it, and both mean the same plugin.
        self.assertIn('"$pkgdir/usr/lib/ozios/decoration-rebuild"', pkgbuild)
        self.assertIn("$root/usr/lib/ozios/decoration-rebuild", guard)
        plugin = re.search(r"(?m)^plugin=(\S+)$", rebuild).group(1)
        self.assertIn('plugin="$root%s"' % plugin, guard)
        for tool in ("cmake", "extra-cmake-modules"):
            self.assertRegex(pkgbuild, r"optdepends=\([^)]*'%s:" % tool)

    @unittest.skipUnless(BASH, "bash is not available here")
    def test_a_build_without_its_tools_says_what_to_install(self):
        done = subprocess.run([BASH, os.path.join(FRAMES, "decoration-rebuild")], capture_output=True, text=True,
                              env=dict(os.environ, PATH=""), timeout=30)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("without cmake", done.stdout)
        self.assertIn("(sudo pacman -S cmake", done.stdout)

    @unittest.skipUnless(BASH, "bash is not available here")
    def test_it_is_built_for_any_x86_64_processor_not_the_build_machines(self):
        text = read("packages", "ozios-decoration", "PKGBUILD")
        self.assertIn('CFLAGS="$(baseline "$CFLAGS")"', text)
        self.assertIn('CXXFLAGS="$(baseline "$CXXFLAGS")"', text)
        cachyos = "-march=native -O3 -pipe -fno-plt -mtune=native -Wp,-D_GLIBCXX_ASSERTIONS"
        done = subprocess.run([BASH, "-c", 'source "$1"; baseline "$2"', "bash", os.path.join(FRAMES, "PKGBUILD"), cachyos],
                              capture_output=True, text=True, timeout=30)
        flags = done.stdout.split()
        self.assertEqual([f for f in flags if f.startswith(("-march", "-mtune"))], ["-march=x86-64", "-mtune=generic"])
        self.assertEqual(flags[:4], ["-O3", "-pipe", "-fno-plt", "-Wp,-D_GLIBCXX_ASSERTIONS"])

    def test_pacman_runs_the_guard_when_plasma_or_the_frames_change(self):
        hook = read("packages", "ozios-decoration", "zz-ozios-decoration.hook")
        for line in ("Type = Package", "Target = kdecoration", "Target = ozios-decoration", "When = PostTransaction"):
            self.assertIn(line + "\n", hook)
        guard = re.search(r"(?m)^Exec = (\S+)$", hook).group(1)
        self.assertIn('"$pkgdir%s"' % guard, read("packages", "ozios-decoration", "PKGBUILD"))

    def test_the_theme_and_the_branding_name_the_plugin_that_is_built(self):
        plugin = json.loads(read("desktop", "decoration", "ozios.json"))["KPlugin"]["Id"]
        self.assertIn("add_library(%s MODULE" % plugin, read("desktop", "decoration", "CMakeLists.txt"))
        self.assertIn("[kwinrc][org.kde.kdecoration2]\nlibrary=%s\n" % plugin,
                      read("desktop", "look-and-feel", "org.ozios.desktop", "contents", "defaults"))
        self.assertIn("decoration=%s " % plugin, read("tools", "apply-branding.sh"))
        self.assertIn("/org.kde.kdecoration3/%s.so" % plugin, read("packages", "ozios-decoration", "decoration-guard"))

    def test_the_iso_compiles_them_and_installs_them_with_the_settings(self):
        remaster = read("iso", "remaster.sh")
        self.assertIn('"$repo/packages/ozios-decoration/PKGBUILD"', remaster)
        self.assertIn('"${pm[@]}" -U "$package" "$decoration_package"', remaster)
        self.assertIn('install -Dm644 "$decoration_package" "$root/opt/ozios/', remaster)
        self.assertIn("extra-cmake-modules", read("tools", "build-iso-in-vm.sh"))
        self.assertIn('"$src"/ozios-decoration-*.pkg.tar.*', read("packages", "ozios-settings", "install-to-target"))

    def test_a_build_goes_on_while_the_archive_does_not_answer(self):
        # The build's tools: the snapshot first, then today's mirrors, and only what is missing,
        # since today's version of something installed (the compiler) would be refused.
        build = read("tools", "build-iso-in-vm.sh")
        self.assertIn("for source in 2026/08/09 2026/08/09 2026/08/09 current; do", build)
        self.assertIn('command -v g++ >/dev/null || tools="$tools gcc"', build)
        self.assertNotIn("archive-install.sh 2026/08/09 cmake extra-cmake-modules gcc", build)
        archive = read("tools", "archive-install.sh")
        self.assertIn('server="Include = /etc/pacman.d/mirrorlist"', archive)
        self.assertIn("--needed --print --print-format '%n'", archive)
        self.assertIn("today's packages would replace what the live system has", archive)
        # The image's own additions: the snapshot's files an earlier build left in the cache.
        remaster = read("iso", "remaster.sh")
        self.assertIn('if ! "${pm[@]}" -Sy --needed $add; then', remaster)
        self.assertIn('"${pm[@]}" -U --needed "${cached[@]}"', remaster)
        self.assertIn('die "the archive does not answer and $name is not cached"', remaster)
        self.assertIn("org.ozios.decoration.so", read("tools", "check-image.sh"))


@unittest.skipUnless(BASH, "bash is not available here")
class DecorationGuard(unittest.TestCase):
    """A plugin built for another feature release of Plasma is kept away from KWin."""
    PLUGIN = ("usr", "lib", "qt6", "plugins", "org.kde.kdecoration3", "org.ozios.decoration.so")
    ASIDE = ("usr", "lib", "ozios", "decoration-aside", "org.ozios.decoration.so")
    BUILT = ("usr", "share", "ozios", "decoration-built-with")
    HERE = ("var", "lib", "ozios", "decoration-built-here")
    REBUILD = ("usr", "lib", "ozios", "decoration-rebuild")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.put(self.PLUGIN, "plugin")
        self.put(self.BUILT, "1:6.7.4-1\n")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, parts, text):
        path = os.path.join(self.tmp.name, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def has(self, parts):
        return os.path.isfile(os.path.join(self.tmp.name, *parts))

    def text(self, parts):
        with open(os.path.join(self.tmp.name, *parts), encoding="utf-8") as fh:
            return fh.read().strip()

    def builder(self, works=True):
        """A stand-in for decoration-rebuild where the guard looks for it: it 'builds' the plugin."""
        script = ["#!/bin/bash", 'echo built >> "$OZI_FAKE_ROOT/builds"']
        if not works:
            script.append("exit 1")
        script.append('echo "plugin built for $OZI_KDECORATION_VERSION" > "$OZI_FAKE_ROOT/%s"' % "/".join(self.PLUGIN))
        self.put(self.REBUILD, "\n".join(script) + "\n")

    def builds(self):
        path = os.path.join(self.tmp.name, "builds")
        return len(self.text(("builds",)).split()) if os.path.isfile(path) else 0

    def guard(self, plasma):
        env = dict(os.environ, OZI_KDECORATION_VERSION=plasma, OZI_FAKE_ROOT=self.tmp.name)
        env.pop("OZI_DECORATION_REBUILD", None)
        done = subprocess.run([BASH, os.path.join(FRAMES, "decoration-guard"), self.tmp.name],
                              capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def test_a_bugfix_release_of_the_same_plasma_keeps_them(self):
        self.assertEqual(self.guard("1:6.7.5-1"), "")
        self.assertTrue(self.has(self.PLUGIN))
        self.assertFalse(self.has(self.ASIDE))

    def test_a_newer_plasma_with_no_way_to_build_them_puts_them_aside(self):
        said = self.guard("1:6.8.0-1")
        self.assertFalse(self.has(self.PLUGIN))
        self.assertTrue(self.has(self.ASIDE))
        self.assertIn("Plasma 6.7", said)
        self.assertIn("Plasma 6.8", said)
        self.guard("1:6.8.0-1")                       # again: nothing more to do
        self.assertTrue(self.has(self.ASIDE))
        # ozios-decoration built for 6.8 comes with a new plugin; the old copy goes.
        self.put(self.BUILT, "1:6.8.0-1\n")
        self.put(self.PLUGIN, "plugin for 6.8")
        self.guard("1:6.8.0-1")
        self.assertTrue(self.has(self.PLUGIN))
        self.assertFalse(self.has(self.ASIDE))

    def test_going_back_to_the_plasma_they_were_built_for_brings_them_back(self):
        self.guard("1:6.8.0-1")
        self.assertIn("fit Plasma 6.7 again", self.guard("6.7.4-2"))   # with or without an epoch
        self.assertTrue(self.has(self.PLUGIN))
        self.assertFalse(self.has(self.ASIDE))

    def test_without_both_versions_it_leaves_everything_alone(self):
        os.remove(os.path.join(self.tmp.name, *self.BUILT))
        self.assertEqual(self.guard("1:6.8.0-1"), "")
        self.assertTrue(self.has(self.PLUGIN))

    # --- with decoration-rebuild: the frames are built on the computer ----------------

    def test_a_newer_plasma_gets_frames_built_on_the_computer(self):
        self.builder()
        self.assertIn("are built for Plasma 6.8", self.guard("1:6.8.3-1"))
        self.assertEqual(self.text(self.PLUGIN), "plugin built for 1:6.8.3-1")
        self.assertEqual(self.text(self.ASIDE), "plugin")       # the package's, for a Plasma going back
        self.assertEqual(self.text(self.HERE).splitlines()[0], "1:6.8.3-1")
        # A bugfix release of that Plasma, or the guard run again: nothing to build.
        self.assertEqual(self.guard("1:6.8.4-1"), "")
        self.assertEqual(self.builds(), 1)
        self.assertTrue(self.has(self.ASIDE))

    def test_the_next_plasma_builds_them_again(self):
        self.builder()
        self.guard("1:6.8.3-1")
        self.assertIn("are built for Plasma 6.9", self.guard("1:6.9.0-1"))
        self.assertEqual(self.text(self.PLUGIN), "plugin built for 1:6.9.0-1")
        self.assertEqual(self.text(self.ASIDE), "plugin")       # still the package's own
        self.assertEqual(self.builds(), 2)

    def test_going_back_brings_the_packages_own_back(self):
        self.builder()
        self.guard("1:6.8.3-1")
        self.assertIn("fit Plasma 6.7 again", self.guard("1:6.7.4-2"))
        self.assertEqual(self.text(self.PLUGIN), "plugin")
        self.assertFalse(self.has(self.ASIDE))
        self.assertFalse(self.has(self.HERE))
        self.assertEqual(self.builds(), 1)

    def test_a_package_built_for_the_new_plasma_takes_over_from_the_build(self):
        self.builder()
        self.guard("1:6.8.3-1")
        self.put(self.BUILT, "1:6.8.3-1\n")                    # pacman puts the new package's plugin in place
        self.put(self.PLUGIN, "plugin for 6.8")
        self.assertEqual(self.guard("1:6.8.3-1"), "")
        self.assertEqual(self.text(self.PLUGIN), "plugin for 6.8")
        self.assertFalse(self.has(self.ASIDE))
        self.assertFalse(self.has(self.HERE))
        self.assertEqual(self.builds(), 1)

    def test_the_same_package_put_back_by_pacman_is_built_over_again(self):
        self.builder()
        self.guard("1:6.8.3-1")
        self.put(self.PLUGIN, "plugin")                         # ozios-decoration reinstalled
        self.assertIn("are built for Plasma 6.8", self.guard("1:6.8.3-1"))
        self.assertEqual(self.builds(), 2)
        self.assertEqual(self.text(self.PLUGIN), "plugin built for 1:6.8.3-1")
        self.assertEqual(self.text(self.ASIDE), "plugin")

    def test_when_the_build_fails_windows_get_breeze_frames_until_it_works(self):
        self.builder(works=False)
        said = self.guard("1:6.8.3-1")
        self.assertIn("windows have Breeze frames", said)
        self.assertIn("sudo /usr/lib/ozios/decoration-guard", said)
        self.assertFalse(self.has(self.PLUGIN))
        self.assertTrue(self.has(self.ASIDE))
        self.assertFalse(self.has(self.HERE))
        self.builder()                                          # cmake is installed, say
        self.assertIn("are built for Plasma 6.8", self.guard("1:6.8.3-1"))
        self.assertEqual(self.text(self.PLUGIN), "plugin built for 1:6.8.3-1")
        self.assertEqual(self.text(self.ASIDE), "plugin")


class Metadata(unittest.TestCase):
    def test_json_files_parse(self):
        for path in glob.glob(os.path.join(ROOT, "desktop", "**", "*.json"), recursive=True) + \
                glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                json.load(fh)

    def test_plasma_packages_carry_an_id_matching_their_folder(self):
        for path in glob.glob(os.path.join(ROOT, "desktop", "*", "org.ozios.*", "metadata.json")):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["KPlugin"]["Id"], os.path.basename(os.path.dirname(path)))

    def test_desktop_files_have_the_basics(self):
        for path in glob.glob(os.path.join(ROOT, "apps", "*.desktop")) + glob.glob(os.path.join(ROOT, "winbridge", "*.desktop")):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertTrue(text.startswith("[Desktop Entry]"), path)
            for key in ("Type=", "Name=", "Exec="):
                self.assertIn("\n" + key, text, path)


class Layouts(unittest.TestCase):
    NAMES = ("default", "deck", "classic")

    def test_every_layout_has_a_script_that_clears_the_old_panels_first(self):
        for name in self.NAMES:
            text = read("desktop", "layouts", name + ".js")
            code = [line for line in text.splitlines() if line.strip() and not line.startswith("//")]
            self.assertEqual(code[0], "panels().forEach(function (p) { p.remove() })", name)

    def test_the_ozi_command_finds_layouts_in_both_trees(self):
        text = read("packages", "ozi-cli", "ozi")
        self.assertIn("layout_file", text)
        self.assertIn("/usr/share/ozios/layouts", text)
        self.assertEqual(sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "desktop", "layouts", "*.js"))),
                         sorted(self.NAMES))

    def test_the_education_board_layout_clears_the_old_panels_and_pins_the_pen(self):
        text = read("edu", "layouts", "board.js")
        code = [line for line in text.splitlines() if line.strip() and not line.startswith("//")]
        self.assertEqual(code[0], "panels().forEach(function (p) { p.remove() })")
        self.assertIn("applications:ozi-pen.desktop", text)

    def test_the_theme_layout_is_the_default_one(self):
        def body(text):
            lines = [line for line in text.splitlines() if not line.startswith("//") and "panels()" not in line]
            return "\n".join(lines).strip()

        theme = read("desktop", "look-and-feel", "org.ozios.desktop", "contents", "layouts", "org.kde.plasma.desktop-layout.js")
        theme = theme.split("var desktops")[0]          # the wallpaper lines are the theme's own
        self.assertEqual(body(theme), body(read("desktop", "layouts", "default.js")))


class DesktopEntries(unittest.TestCase):
    def entries(self):
        patterns = ("apps/*.desktop", "winbridge/*.desktop", "edu/applications/*.desktop", "packages/*/*.desktop")
        return [p for pattern in patterns for p in glob.glob(os.path.join(ROOT, pattern))]

    def test_there_are_entries_to_check(self):
        self.assertGreater(len(self.entries()), 8)

    def test_exec_lines_have_no_dollar_signs(self):
        """systemd's autostart generator escapes `$`, so "$HOME" in an Exec line
        reaches the shell as a literal. The first-login marker was never found
        because of it. Anything that needs a variable belongs in a script."""
        for path in self.entries():
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("Exec=") or line.startswith("TryExec="):
                        self.assertNotIn("$", line, "%s: %s" % (path, line.strip()))

    def test_first_login_is_a_script_that_creates_its_marker(self):
        script = read("packages", "ozios-settings", "first-login")
        self.assertIn("ozios-applied", script)
        self.assertIn("touch", script)
        self.assertIn("/usr/lib/ozios/first-login", read("packages", "ozios-settings", "first-login.desktop"))
        self.assertIn("first-login", read("packages", "ozios-settings", "PKGBUILD"))


class Qml(unittest.TestCase):
    """No Qt here, so only the mistakes that can be seen in the text."""

    def files(self):
        return glob.glob(os.path.join(ROOT, "apps", "**", "*.qml"), recursive=True) + \
            glob.glob(os.path.join(ROOT, "desktop", "**", "*.qml"), recursive=True)

    @staticmethod
    def strip(text):
        text = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)      # strings first: they may contain "//"
        return re.sub(r"//[^\n]*", "", text)

    def test_brackets_balance(self):
        for path in self.files():
            with open(path, encoding="utf-8") as fh:
                text = self.strip(fh.read())
            for open_, close in ("{}", "()", "[]"):
                self.assertEqual(text.count(open_), text.count(close), "%s: %s%s" % (path, open_, close))

    def test_components_are_listed_in_the_module(self):
        listed = set(re.findall(r"^(?:singleton )?(\w+) 1\.0 ", read("apps", "OziUi", "qmldir"), re.M))
        files = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, "apps", "OziUi", "*.qml"))}
        self.assertEqual(listed, files)

    def test_apps_use_only_known_backend_calls(self):
        for app in ("ozi-store", "ozi-welcome"):
            qml = read("apps", app, "Main.qml")
            py = read("apps", app, app)
            names = set(re.findall(r'backend\.call\("[^"]*",\s*"(\w+)"', qml)) | set(re.findall(r'run\("[^"]*",\s*"(\w+)"', qml))
            for name in names:
                self.assertIn('"%s":' % name, py, "%s calls %s, which the backend does not allow" % (app, name))


if __name__ == "__main__":
    unittest.main()
