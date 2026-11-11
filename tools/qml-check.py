"""Load a QML window of an OziOS app, let it run for a moment and report every
warning Qt printed. Run it inside a Plasma session or with
QT_QPA_PLATFORM=offscreen.

    python3 tools/qml-check.py apps/ozi-store [seconds]
"""
import importlib.machinery
import importlib.util
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(root, "apps"))
sys.path.insert(0, os.path.join(root, "python"))

from PyQt6.QtCore import QTimer, QUrl, qInstallMessageHandler  # noqa: E402
from PyQt6.QtGui import QGuiApplication  # noqa: E402
from PyQt6.QtQml import QQmlApplicationEngine  # noqa: E402

app_dir = os.path.join(root, sys.argv[1])
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
name = os.path.basename(app_dir)

messages = []
qInstallMessageHandler(lambda mode, context, message: messages.append("%s:%s: %s" % (
    os.path.basename(context.file or "?"), context.line, message)))

loader = importlib.machinery.SourceFileLoader("app_module", os.path.join(app_dir, name))
spec = importlib.util.spec_from_loader("app_module", loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
backend = next(getattr(module, n)() for n in dir(module) if n.endswith("Backend") and n != "Backend")

app = QGuiApplication(sys.argv[:1])
engine = QQmlApplicationEngine()
engine.addImportPath(os.path.join(root, "apps"))
engine.rootContext().setContextProperty("backend", backend)
engine.load(QUrl.fromLocalFile(os.path.join(app_dir, "Main.qml")))
loaded = bool(engine.rootObjects())
QTimer.singleShot(int(seconds * 1000), app.quit)
if loaded:
    app.exec()

for line in messages:
    print(line)
print("loaded:", loaded, "| warnings:", len(messages))
sys.exit(0 if loaded and not messages else 1)
