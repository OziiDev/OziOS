"""Drive an OziOS app's window without a desktop and save pictures of it.

Runs offscreen, so it works over SSH or inside a build. Steps run in order:

    js:<expression>   evaluated on the window's root object, for example js:tab = 2;
                      a value it returns is printed, so a step can check state
    mouse:<what>:x,y  a pointer event on the window: down, move or up
    wait:<ms>         let the interface settle (animations, calls to the backend)
    shot:<file.png>   save what the window shows
    shots:<prefix>    save every window the app has open as <prefix>-<n>.png
                      (a toolbar that lives in its own window, for example)

Arguments that start with -- are left for the app itself, for example --demo.
A transparent window is saved on a grey background so it can be seen.

    QT_QPA_PLATFORM=offscreen python3 tools/qml-shot.py apps/ozi-classroom \\
        'js:createClass("5-A")' wait:600 shot:/tmp/created.png

The app's state folders point at a temporary directory, so nothing the steps
create outlives the run.
"""
import importlib.machinery
import importlib.util
import os
import sys
import tempfile

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(root_dir, "apps"))
sys.path.insert(0, os.path.join(root_dir, "python"))

if len(sys.argv) < 3:
    sys.exit(__doc__)

scratch = tempfile.mkdtemp(prefix="qml-shot-")
for variable in ("XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
    os.environ[variable] = os.path.join(scratch, variable.lower())
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PyQt6 import sip  # noqa: E402
from PyQt6.QtCore import QPoint, QTimer, QUrl, Qt, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine, QQmlExpression  # noqa: E402
from PyQt6.QtQuick import QQuickWindow  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402

app_dir = os.path.join(root_dir, sys.argv[1])
name = os.path.basename(app_dir)
steps = [arg for arg in sys.argv[2:] if not arg.startswith("--")]

messages = []
running = True


def remember(mode, context, message):
    if not running:                  # the backend goes away before the window does: not worth reporting
        return
    line = "%s:%s: %s" % (os.path.basename(context.file or "?"), context.line, message)
    messages.append(line)
    print(line, file=sys.stderr, flush=True)       # a crash would otherwise take the list with it


qInstallMessageHandler(remember)

loader = importlib.machinery.SourceFileLoader("app_module", os.path.join(app_dir, name))
spec = importlib.util.spec_from_loader("app_module", loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
backend = next(getattr(module, n)() for n in dir(module) if n.endswith("Backend") and n != "Backend")

app = QGuiApplication(sys.argv[:1])
engine = QQmlApplicationEngine()
engine.addImportPath(os.path.join(root_dir, "apps"))
engine.rootContext().setContextProperty("backend", backend)
engine.load(QUrl.fromLocalFile(os.path.join(app_dir, "Main.qml")))
if not engine.rootObjects():
    print("\n".join(messages))
    sys.exit("the window did not load")
window = engine.rootObjects()[0]
picture = sip.cast(window, QQuickWindow)          # the engine hands back a plain QWindow
failures = []


def save(quick_window, path):
    image = quick_window.grabWindow()
    if image.isNull():
        return False
    if image.hasAlphaChannel():
        flat = QImage(image.size(), QImage.Format.Format_RGB32)
        flat.fill(QColor("#2B3340"))
        painter = QPainter(flat)
        painter.drawImage(0, 0, image)
        painter.end()
        image = flat
    if not image.save(path):
        return False
    print("saved", path, "%dx%d" % (image.width(), image.height()))
    return True


def next_step():
    if not steps:
        app.quit()
        return
    kind, _, argument = steps.pop(0).partition(":")
    delay = 50
    try:
        delay = run_step(kind, argument) or delay
    except Exception as err:             # an exception in a Qt callback would abort the whole run
        failures.append("%s:%s: %s" % (kind, argument, err))
    QTimer.singleShot(delay, next_step)


def run_step(kind, argument):
    delay = 0
    if kind == "js":
        expression = QQmlExpression(engine.rootContext(), window, argument)
        value, undefined = expression.evaluate()
        if expression.hasError():
            failures.append("%s: %s" % (argument, expression.error().description()))
        elif not undefined and value is not None:
            print("%s => %s" % (argument, value))
    elif kind == "mouse":
        action, _, where = argument.partition(":")
        x, y = (int(part) for part in where.split(","))
        point = QPoint(x, y)
        left, none = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
        if action == "down":
            QTest.mousePress(picture, left, none, point)
        elif action == "up":
            QTest.mouseRelease(picture, left, none, point)
        elif action == "move":
            QTest.mouseMove(picture, point)
        else:
            failures.append("unknown mouse action: " + action)
    elif kind == "wait":
        delay = int(argument)
    elif kind == "shot":
        if not save(picture, argument):
            failures.append("could not save " + argument)
    elif kind == "shots":
        for number, other in enumerate(app.allWindows()):
            if not save(sip.cast(other, QQuickWindow), "%s-%d.png" % (argument, number)):
                failures.append("could not save window %d" % number)
    else:
        failures.append("unknown step: " + kind)
    return delay


QTimer.singleShot(800, next_step)         # give the first frame time to appear
app.exec()
running = False

for line in failures:
    print(line)
sys.exit(1 if failures or messages else 0)
