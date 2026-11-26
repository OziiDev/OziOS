"""Shared Qt glue for the OziOS apps: a worker that runs service calls off the
interface thread, and a function that starts a QML window.

The only code here that touches Qt. Everything it calls lives in ozipkg and
has no Qt in it.
"""
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
# Next to the apps first: a checkout runs its own code, an installed app finds /usr/lib/ozios/python.
for root in (os.path.join(HERE, "..", "python"), "/usr/lib/ozios/python"):
    if os.path.isdir(os.path.join(root, "ozipkg")):
        sys.path.insert(0, root)
        break

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot  # noqa: E402
from PyQt6.QtGui import QColor, QGuiApplication, QIcon  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent  # noqa: E402

from ozipkg import i18n, service, themes  # noqa: E402


class Backend(QObject):
    """QML calls `call(task, name, argsJson)`; results come back as signals.

    Only the names in `allowed` can be called, so the interface cannot reach
    anything else in the Python process.
    """
    done = pyqtSignal(str, str)       # task, JSON result
    failed = pyqtSignal(str, str)     # task, message
    log = pyqtSignal(str, str)        # task, one line of output

    allowed = {}                      # name -> (callable, takes_log)

    @pyqtSlot(str, str, str)
    def call(self, task, name, args_json):
        entry = self.allowed.get(name)
        if entry is None:
            self.failed.emit(task, "unknown call: " + name)
            return
        func, takes_log = entry
        try:
            args = json.loads(args_json or "[]")
        except ValueError:
            self.failed.emit(task, "bad arguments")
            return

        def work():
            try:
                kwargs = {"log": lambda line: self.log.emit(task, line)} if takes_log else {}
                self.done.emit(task, json.dumps(func(*args, **kwargs)))
            except (service.ServiceError, ValueError) as err:
                self.failed.emit(task, str(err))
            except Exception as err:           # never let a worker thread die silently
                self.failed.emit(task, "%s: %s" % (type(err).__name__, err))

        threading.Thread(target=work, daemon=True).start()

    @pyqtSlot(str, result=str)
    def tr(self, text):
        return i18n.tr(text)

    @pyqtSlot(result=str)
    def startFile(self):
        """The file the app was started with (from a file manager), if any."""
        for arg in sys.argv[1:]:
            if not arg.startswith("-") and os.path.isfile(arg):
                return os.path.abspath(arg)
        return ""

    @pyqtSlot(str, result=str)
    def fileFromUrl(self, url):
        return QUrl(url).toLocalFile() if url.startswith("file:") else url


def desktop_palette():
    """The OziUi palette from the OziOS desktop's look (~/.config/ozios/desktop.json):
    the wallpaper's colours with the "auto" theme. None outside the OziOS desktop."""
    from ozipkg import shell
    if not os.path.exists(shell.desktop_config_path()):
        return None
    look = shell.look()
    c = shell.palette(look["theme"], look.get("colors"))

    def mix(a, b, t):
        a, b = QColor(a), QColor(b)
        return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                      round(a.blue() + (b.blue() - a.blue()) * t)).name()
    return {"ink": c["ink"], "raised": c["raised"], "control": c["control"], "cyan": c["accent"],
            "mid": mix(c["accent"], c["ink"], 0.35), "far": mix(c["accent"], c["ink"], 0.7), "ice": c["text"],
            "muted": c["muted"], "onAccent": c["onAccent"], "light": bool(c.get("light"))}


def apply_theme(engine, theme_id=None):
    """Give the OziUi palette the colours of the desktop, before any window exists:
    the OziOS desktop's look (from the wallpaper), else the older `ozi theme`."""
    palette = None if theme_id or os.environ.get("OZIOS_THEME") else desktop_palette()
    palette = palette or themes.app_palette(theme_id or themes.theme_for_apps())
    component = QQmlComponent(engine)
    component.setData(b"import QtQuick\nimport OziUi\nQtObject { property QtObject theme: Theme }",
                      QUrl.fromLocalFile(os.path.join(HERE, "theme-probe.qml")))
    probe = component.create()
    if probe is None:
        return False
    singleton = probe.property("theme")
    for key, value in palette.items():
        singleton.setProperty(key, value if isinstance(value, bool) else QColor(value))
    probe.deleteLater()
    return True


def run(qml_file, backend, title, desktop_name, icon="ozios", setup=None):
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName(title)
    app.setDesktopFileName(desktop_name)
    app.setWindowIcon(QIcon.fromTheme(icon))
    engine = QQmlApplicationEngine()
    engine.addImportPath(HERE)
    engine.rootContext().setContextProperty("backend", backend)
    apply_theme(engine)
    if setup:
        setup(engine)
    engine.load(QUrl.fromLocalFile(qml_file))
    if not engine.rootObjects():
        return 1
    return app.exec()
