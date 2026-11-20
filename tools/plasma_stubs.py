"""Stand-ins for the Plasma modules that OziOS's desktop QML imports, so the real
files can be loaded, driven and pictured without a Plasma session.

    tools/shell-preview.py      pictures of the dock, launcher, control widget and wallpaper
    tests/test_desktop.py       loads every OziOS applet and the wallpaper and fails on any Qt warning

The stand-ins behave like the real types only as far as OziOS uses them: the
property names, enums and calls are the ones checked against KDE's sources
(plasma-workspace and plasma-desktop 6.7). What they cannot tell is whether
Plasma itself behaves as assumed; for that the desktop has to run in a session.
"""
import enum
import json
import os
import re
import sys

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QObject, QRect, Qt, QUrl, pyqtEnum, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtQml import QQmlPropertyMap, qmlRegisterSingletonInstance, qmlRegisterSingletonType, qmlRegisterType, qmlTypeId

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STUBS = os.path.join(ROOT, "tools", "qml-stubs")
sys.path.insert(0, os.path.join(ROOT, "python"))

from ozipkg import themes  # noqa: E402

USER_ROLE = Qt.ItemDataRole.UserRole.value
STATE = None          # what every `Plasmoid` attached object shows
CALLS = []            # what the stand-ins were asked to do, for tests: (who, what, detail)


def _settable(namespace, spec):
    """Add a notifying, writable property per entry of {name: (type, default)} to a class namespace."""
    for name, (kind, default) in spec.items():
        signal = pyqtSignal()
        namespace[name + "Changed"] = signal

        def getter(self, _n=name, _d=default):
            return getattr(self, "_p_" + _n, _d)

        def setter(self, value, _n=name):
            if getattr(self, "_p_" + _n, object()) != value:
                setattr(self, "_p_" + _n, value)
                getattr(self, _n + "Changed").emit()
        namespace[name] = pyqtProperty(kind, getter, setter, notify=signal)


# --- org.kde.plasma.plasmoid -------------------------------------------------------------

class Containment(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._geometry = QRect(0, 0, 1920, 1080)

    @pyqtProperty(QRect, constant=True)
    def screenGeometry(self):
        return self._geometry


def _state_class():
    """`Plasmoid` in an applet's QML. In Plasma it is an attached object; PyQt6 cannot make
    attached objects that QML reads, so here it is one shared singleton, and an applet's
    `Plasmoid.x: value` lines become Bindings in the copy that is loaded (see prepared())."""
    ns = {"configurationChanged": pyqtSignal(),
          "ConstraintHint": pyqtEnum(enum.Enum("ConstraintHint", {"NoHint": 0, "CanFillArea": 1, "MarginAreasSeparator": 2}))}
    _settable(ns, {"icon": (str, ""), "status": (int, 1), "formFactor": (int, 2), "location": (int, 4),
                   "constraintHints": (int, 0), "title": (str, "OziOS"), "pluginName": (str, ""),
                   "backgroundHints": (int, 1), "busy": (bool, False)})

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self._config = QQmlPropertyMap(self)
        self._containment = Containment(self)

    def reset(self, config, form_factor, location):
        self._config = QQmlPropertyMap(self)
        for key, value in config.items():
            self._config.insert(key, value)
        self.configurationChanged.emit()
        self.formFactor = form_factor
        self.location = location
        self.icon = ""
        self.status = 1

    ns.update({"__init__": __init__, "reset": reset,
               "configuration": pyqtProperty(QObject, lambda self: self._config, notify=ns["configurationChanged"]),
               "containment": pyqtProperty(QObject, lambda self: self._containment, constant=True),
               "id": pyqtProperty(int, lambda self: 7, constant=True)})
    return type("PlasmoidState", (QObject,), ns)


PlasmoidState = _state_class()

ATTACHED_ASSIGNMENT = re.compile(r"^(\s*)Plasmoid\.(\w+)\s*:\s*(.+?)\s*$", re.M)


def prepared(ui_folder, into):
    """A copy of an applet's ui folder that loads with the stand-ins: `Plasmoid.x: value` becomes
    `Binding { target: Plasmoid; property: "x"; value: value }`. Nothing else changes."""
    target = os.path.join(into, os.path.basename(os.path.dirname(os.path.dirname(ui_folder))))
    os.makedirs(target, exist_ok=True)
    for name in os.listdir(ui_folder):
        source = os.path.join(ui_folder, name)
        if not os.path.isfile(source):
            continue
        with open(source, encoding="utf-8") as fh:
            text = fh.read()
        if name.endswith(".qml"):
            text = ATTACHED_ASSIGNMENT.sub(r'\1Binding { target: Plasmoid; property: "\2"; value: \3 }', text)
        with open(os.path.join(target, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return target


# --- org.kde.taskmanager --------------------------------------------------------------------

TASK_ROLES = ("AppId", "AppName", "GenericName", "LauncherUrl", "LauncherUrlWithoutIcon", "WinIdList", "MimeType",
              "MimeData", "IsWindow", "IsStartup", "IsLauncher", "HasLauncher", "IsGroupParent", "ChildCount",
              "IsGroupable", "IsActive", "IsClosable", "IsMovable", "IsResizable", "IsMaximizable", "IsMaximized",
              "IsMinimizable", "IsMinimized", "IsHidden", "IsKeepAbove", "IsKeepBelow", "IsFullScreenable",
              "IsFullScreen", "IsShadeable", "IsShaded", "IsVirtualDesktopsChangeable", "VirtualDesktops",
              "IsOnAllVirtualDesktops", "ScreenGeometry", "Activities", "IsDemandingAttention", "SkipTaskbar",
              "SkipPager", "AppPid", "StackingOrder", "LastActivated", "IsHovered", "CanLaunchNewInstance")
ROLE = {name: USER_ROLE + 1 + i for i, name in enumerate(TASK_ROLES)}


class AbstractTasksModel(QObject):
    AdditionalRoles = pyqtEnum(enum.IntEnum("AdditionalRoles", {name: ROLE[name] for name in TASK_ROLES}))


def task(name, icon, **flags):
    out = {"display": name, "decoration": icon, "AppId": icon, "AppName": name, "ChildCount": 0,
           "LauncherUrl": "applications:%s.desktop" % icon, "LauncherUrlWithoutIcon": "applications:%s.desktop" % icon,
           "CanLaunchNewInstance": True, "IsWindow": False, "IsLauncher": False, "IsStartup": False,
           "IsActive": False, "IsDemandingAttention": False, "IsGroupParent": False, "IsMinimized": False,
           "IsMaximized": False, "IsFullScreen": False}
    out.update(flags)
    return out


DEMO_TASKS = [
    task("Firefox", "firefox", IsWindow=True, IsActive=True),
    task("Dosyalar", "org.kde.dolphin", IsWindow=True, IsGroupParent=True, ChildCount=2),
    task("Konsole", "org.kde.konsole", IsLauncher=True),
    task("Steam", "steam", IsStartup=True),
    task("Discord", "discord", IsWindow=True, IsDemandingAttention=True),
    task("Yazılım", "ozi-store", IsLauncher=True),
    task("Sistem Ayarları", "systemsettings", IsLauncher=True),
]


INSTANCES = []        # the Python side of every TasksModel QML created (QML sees a proxy of it)


class TasksModelBase(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = [dict(t) for t in DEMO_TASKS]
        self._launchers = []
        INSTANCES.append(self)

    def change(self, row, **values):
        """Change a task the way Plasma would report it, for tests."""
        self._tasks[row].update(values)
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [])

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._tasks)

    def roleNames(self):
        names = {Qt.ItemDataRole.DisplayRole.value: b"display", Qt.ItemDataRole.DecorationRole.value: b"decoration"}
        names.update({number: name.encode() for name, number in ROLE.items()})
        return names

    def data(self, index, role=Qt.ItemDataRole.DisplayRole.value):
        if not index.isValid() or not 0 <= index.row() < len(self._tasks):
            return None
        item = self._tasks[index.row()]
        role = int(role.value if hasattr(role, "value") else role)
        if role == Qt.ItemDataRole.DisplayRole.value:
            return item["display"]
        if role == Qt.ItemDataRole.DecorationRole.value:
            return item["decoration"]
        for name, number in ROLE.items():
            if number == role:
                return item.get(name)
        return None

    def _get_launchers(self):
        return list(self._launchers)

    def _set_launchers(self, value):
        value = [str(v) for v in (value or [])]
        if value != self._launchers:
            self._launchers = value
            self.launcherListChanged.emit()

    @pyqtSlot(int, result=QModelIndex)
    @pyqtSlot(int, int, result=QModelIndex)
    def makeModelIndex(self, row, child=-1):
        return self.index(row, 0)

    def _record(self, what, index):
        CALLS.append(("tasks", what, index.row() if isinstance(index, QModelIndex) else index))

    @pyqtSlot(QModelIndex)
    def requestActivate(self, index):
        self._record("activate", index)

    @pyqtSlot(QModelIndex)
    def requestNewInstance(self, index):
        self._record("new-instance", index)

    @pyqtSlot(QModelIndex)
    def requestClose(self, index):
        self._record("close", index)

    @pyqtSlot(QModelIndex)
    def requestToggleMinimized(self, index):
        self._record("toggle-minimized", index)

    @pyqtSlot(QModelIndex, QRect, QObject)
    def requestPublishDelegateGeometry(self, index, rect, delegate):
        self._record("geometry", index)

    @pyqtSlot(str, result=int)
    def launcherPosition(self, url):
        return self._launchers.index(url) if url in self._launchers else -1

    @pyqtSlot(str, result=bool)
    def requestAddLauncher(self, url):
        if url in self._launchers:
            return False
        self._set_launchers(self._launchers + [url])
        CALLS.append(("tasks", "pin", url))
        return True

    @pyqtSlot(str, result=bool)
    def requestRemoveLauncher(self, url):
        if url not in self._launchers:
            return False
        self._set_launchers([u for u in self._launchers if u != url])
        CALLS.append(("tasks", "unpin", url))
        return True


def _tasks_class():
    ns = {
        "SortMode": pyqtEnum(enum.Enum("SortMode", {"SortDisabled": 0, "SortManual": 1, "SortAlpha": 2,
                                                    "SortVirtualDesktop": 3, "SortActivity": 4, "SortLastActivated": 5,
                                                    "SortWindowPositionHorizontal": 6})),
        "GroupMode": pyqtEnum(enum.Enum("GroupMode", {"GroupDisabled": 0, "GroupApplications": 1})),
        "launcherListChanged": pyqtSignal(),
        "countChanged": pyqtSignal(),
    }
    _settable(ns, {"virtualDesktop": ("QVariant", None), "screenGeometry": (QRect, QRect()), "regionGeometry": (QRect, QRect()),
                   "activity": (str, ""), "filterByVirtualDesktop": (bool, False), "filterByCurrentVirtualDesktop": (bool, False),
                   "filterByScreen": (bool, False), "filterByActivity": (bool, False), "filterByRegion": (int, 0),
                   "filterMinimized": (bool, False), "filterNotMinimized": (bool, False), "filterNotMaximized": (bool, False),
                   "filterHidden": (bool, False), "hideActivatedLaunchers": (bool, True), "separateLaunchers": (bool, True),
                   "launchInPlace": (bool, False), "sortMode": (int, 1), "groupMode": (int, 1), "groupInline": (bool, False),
                   "taskReorderingEnabled": (bool, True), "groupingWindowTasksThreshold": (int, -1)})
    ns["launcherList"] = pyqtProperty(list, TasksModelBase._get_launchers, TasksModelBase._set_launchers, notify=ns["launcherListChanged"])
    ns["count"] = pyqtProperty(int, lambda self: self.rowCount(), notify=ns["countChanged"])
    ns["launcherCount"] = pyqtProperty(int, lambda self: len(self._launchers), notify=ns["launcherListChanged"])
    ns["anyTaskDemandsAttention"] = pyqtProperty(bool, lambda self: any(t["IsDemandingAttention"] for t in self._tasks), constant=True)
    return type("TasksModel", (TasksModelBase,), ns)


TasksModel = _tasks_class()


# --- org.kde.plasma.private.kicker ------------------------------------------------------------

DEMO_APPS = [
    ("Firefox", "firefox", "İnternet"), ("Thunderbird", "thunderbird", "İnternet"), ("Discord", "discord", "İnternet"),
    ("Steam", "steam", "Oyunlar"), ("Lutris", "lutris", "Oyunlar"), ("Heroic", "heroic", "Oyunlar"),
    ("Dosyalar", "org.kde.dolphin", "Sistem"), ("Konsole", "org.kde.konsole", "Sistem"), ("Yazılım", "ozi-store", "Sistem"),
    ("Sistem Ayarları", "systemsettings", "Ayarlar"), ("Hoş geldin", "ozios", "Sistem"),
    ("LibreOffice Writer", "libreoffice-writer", "Ofis"), ("LibreOffice Calc", "libreoffice-calc", "Ofis"),
    ("Okular", "okular", "Ofis"), ("GIMP", "gimp", "Grafik"), ("Krita", "krita", "Grafik"), ("Gwenview", "gwenview", "Grafik"),
    ("VLC", "vlc", "Çoklu ortam"), ("Elisa", "elisa", "Çoklu ortam"), ("OBS Studio", "obs", "Çoklu ortam"),
    ("Kate", "kate", "Geliştirme"), ("VS Code", "code", "Geliştirme"), ("Hesap makinesi", "kcalc", "Araçlar"),
    ("Spectacle", "spectacle", "Araçlar"), ("Ark", "ark", "Araçlar"), ("KDE Connect", "kdeconnect", "Araçlar"),
]
FAVORITES_ROW, ALL_ROW = 0, 1


class FavoritesModel(QObject):
    countChanged = pyqtSignal()

    @pyqtProperty(int, notify=countChanged)
    def count(self):
        return 0

    @pyqtSlot(str)
    def initForClient(self, client):
        CALLS.append(("favorites", "init", client))

    @pyqtSlot(str, result=bool)
    def isFavorite(self, favorite_id):
        return False

    @pyqtSlot(str, int)
    def addFavorite(self, favorite_id, index=-1):
        pass

    @pyqtSlot(str)
    def removeFavorite(self, favorite_id):
        pass

    @pyqtSlot("QStringList")
    def portOldFavorites(self, ids):
        pass


class AppsModel(QAbstractListModel):
    countChanged = pyqtSignal()

    def __init__(self, entries=(), name="", parent=None):
        super().__init__(parent)
        self._entries = list(entries)
        self._name = name

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._entries)

    def roleNames(self):
        return {Qt.ItemDataRole.DisplayRole.value: b"display", Qt.ItemDataRole.DecorationRole.value: b"decoration",
                USER_ROLE + 1: b"description", USER_ROLE + 2: b"favoriteId", USER_ROLE + 3: b"group",
                USER_ROLE + 4: b"hasActionList", USER_ROLE + 5: b"isSeparator"}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole.value):
        if not index.isValid() or not 0 <= index.row() < len(self._entries):
            return None
        name, icon, category = self._entries[index.row()]
        role = int(role.value if hasattr(role, "value") else role)
        return {Qt.ItemDataRole.DisplayRole.value: name, Qt.ItemDataRole.DecorationRole.value: icon,
                USER_ROLE + 1: category, USER_ROLE + 2: "applications:%s.desktop" % icon, USER_ROLE + 3: category,
                USER_ROLE + 4: False, USER_ROLE + 5: False}.get(role)

    @pyqtProperty(int, notify=countChanged)
    def count(self):
        return len(self._entries)

    @pyqtProperty(str, constant=True)
    def description(self):
        return self._name

    @pyqtSlot(int, str, "QVariant", result=bool)
    def trigger(self, row, action, argument):
        if not 0 <= row < len(self._entries):
            return False
        CALLS.append(("apps", "launch", self._entries[row][0]))
        return True


def _root_class():
    ns = {"refreshed": pyqtSignal(), "countChanged": pyqtSignal()}
    _settable(ns, {"autoPopulate": (bool, True), "appletInterface": (QObject, None), "appNameFormat": (int, 0),
                   "flat": (bool, False), "sorted": (bool, False), "showSeparators": (bool, False),
                   "showRootSeparator": (bool, False), "showTopLevelItems": (bool, False), "showAllApps": (bool, False),
                   "showAllAppsCategorized": (bool, False), "showRecentApps": (bool, False), "showRecentDocs": (bool, False),
                   "showPowerSession": (bool, False), "showFavoritesPlaceholder": (bool, False),
                   "highlightNewlyInstalledApps": (bool, False), "paginate": (bool, False), "pageSize": (int, 24)})

    def __init__(self, parent=None):
        QAbstractListModel.__init__(self, parent)
        self._favorites = FavoritesModel(self)
        self._system_favorites = FavoritesModel(self)
        self._rows = []

    def refresh(self):
        self.beginResetModel()
        categories = []
        for _, _, category in DEMO_APPS:
            if category not in categories:
                categories.append(category)
        self._rows = [("Sık kullanılanlar", AppsModel([], "favorites", self)),
                      ("Tüm uygulamalar", AppsModel(sorted(DEMO_APPS, key=lambda a: a[0].lower()), "all", self))]
        for category in sorted(categories):
            self._rows.append((category, AppsModel(sorted((a for a in DEMO_APPS if a[2] == category), key=lambda a: a[0].lower()),
                                                   category, self)))
        self.endResetModel()
        self.countChanged.emit()
        self.refreshed.emit()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def roleNames(self):
        return {Qt.ItemDataRole.DisplayRole.value: b"display", Qt.ItemDataRole.DecorationRole.value: b"decoration"}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole.value):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        role = int(role.value if hasattr(role, "value") else role)
        return self._rows[index.row()][0] if role == Qt.ItemDataRole.DisplayRole.value else None

    def modelForRow(self, row):
        return self._rows[row][1] if 0 <= row < len(self._rows) else None

    ns.update({
        "__init__": __init__,
        "refresh": pyqtSlot()(refresh),
        "rowCount": rowCount,
        "roleNames": roleNames,
        "data": data,
        "modelForRow": pyqtSlot(int, result=QObject)(modelForRow),
        "count": pyqtProperty(int, lambda self: len(self._rows), notify=ns["countChanged"]),
        "favoritesModel": pyqtProperty(QObject, lambda self: self._favorites, constant=True),
        "systemFavoritesModel": pyqtProperty(QObject, lambda self: self._system_favorites, constant=True),
    })
    return type("RootModel", (QAbstractListModel,), ns)


RootModel = _root_class()


def _runner_class():
    ns = {"countChanged": pyqtSignal(), "queryChanged": pyqtSignal(), "requestUpdateQuery": pyqtSignal(str)}
    _settable(ns, {"appletInterface": (QObject, None), "mergeResults": (bool, False), "favoritesModel": (QObject, None),
                   "runners": (list, []), "deleteWhenEmpty": (bool, False)})

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self._query = ""
        self._results = AppsModel([], "results", self)

    def get_query(self):
        return self._query

    def set_query(self, value):
        if value == self._query:
            return
        self._query = value
        words = value.lower().split()
        hits = [a for a in DEMO_APPS if words and all(w in (a[0] + " " + a[2]).lower() for w in words)]
        self._results = AppsModel(sorted(hits, key=lambda a: a[0].lower()), "results", self)
        self.queryChanged.emit()
        self.countChanged.emit()

    def modelForRow(self, row):
        return self._results if row == 0 and self._results.rowCount() else None

    ns.update({
        "__init__": __init__,
        "query": pyqtProperty(str, get_query, set_query, notify=ns["queryChanged"]),
        "count": pyqtProperty(int, lambda self: 1 if self._results.rowCount() else 0, notify=ns["countChanged"]),
        "modelForRow": pyqtSlot(int, result=QObject)(modelForRow),
    })
    return type("RunnerModel", (QObject,), ns)


RunnerModel = _runner_class()

SYSTEM_ENTRIES = [("lock-screen", "Ekranı kilitle", "lock"), ("logout", "Oturumu kapat", "system-log-out"),
                  ("suspend", "Uyku", "system-suspend"), ("reboot", "Yeniden başlat", "system-reboot"),
                  ("shutdown", "Kapat", "system-shutdown")]


def _system_class():
    ns = {}
    _settable(ns, {"favoritesModel": (QObject, None)})

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(SYSTEM_ENTRIES)

    def roleNames(self):
        return {Qt.ItemDataRole.DisplayRole.value: b"display", Qt.ItemDataRole.DecorationRole.value: b"decoration",
                USER_ROLE + 2: b"favoriteId"}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole.value):
        if not index.isValid() or not 0 <= index.row() < len(SYSTEM_ENTRIES):
            return None
        favorite, name, icon = SYSTEM_ENTRIES[index.row()]
        role = int(role.value if hasattr(role, "value") else role)
        return {Qt.ItemDataRole.DisplayRole.value: name, Qt.ItemDataRole.DecorationRole.value: icon,
                USER_ROLE + 2: favorite}.get(role)

    def trigger(self, row, action, argument):
        CALLS.append(("system", "trigger", SYSTEM_ENTRIES[row][0]))
        return True

    ns.update({"rowCount": rowCount, "roleNames": roleNames, "data": data,
               "trigger": pyqtSlot(int, str, "QVariant", result=bool)(trigger),
               "count": pyqtProperty(int, lambda self: len(SYSTEM_ENTRIES), constant=True)})
    return type("SystemModel", (QAbstractListModel,), ns)


SystemModel = _system_class()


# --- what KWin hands a window switcher ---------------------------------------------------------

DEMO_WINDOWS = [("Firefox — OziOS", "firefox", 101), ("Dosyalar — Ev", "org.kde.dolphin", 102),
                ("Konsole — ~", "org.kde.konsole", 103), ("Discord", "discord", 104), ("Steam", "steam", 105)]


class TabBoxModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._windows = list(DEMO_WINDOWS)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._windows)

    def roleNames(self):
        return {USER_ROLE + 1: b"caption", USER_ROLE + 2: b"icon", USER_ROLE + 3: b"windowId",
                USER_ROLE + 4: b"closeable", USER_ROLE + 5: b"minimized", USER_ROLE + 6: b"desktopName"}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole.value):
        if not index.isValid() or not 0 <= index.row() < len(self._windows):
            return None
        caption, icon, window = self._windows[index.row()]
        role = int(role.value if hasattr(role, "value") else role)
        return {USER_ROLE + 1: caption, USER_ROLE + 2: icon, USER_ROLE + 3: window, USER_ROLE + 4: True,
                USER_ROLE + 5: False, USER_ROLE + 6: "1"}.get(role)

    @pyqtSlot(int)
    def activate(self, index):
        CALLS.append(("tabbox", "activate", index))

    @pyqtSlot(int)
    def close(self, index):
        CALLS.append(("tabbox", "close", index))


# --- the shell behind Plasma5Support.DataSource -------------------------------------------------

class Shell(QObject):
    """Answers the commands the control widget runs."""

    def __init__(self, theme_id, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id

    @pyqtSlot(str, result="QVariantMap")
    def run(self, command):
        CALLS.append(("shell", "run", command))
        if "status --json" in command:
            out = json.dumps({"version": "0.1.1", "kernel": "7.1.6-1-ozios", "effects": "full", "game_mode": False,
                              "layout": "default", "power_profile": "balanced", "windows_guest": "missing", "updates": 3})
        elif "theme --json" in command:
            items = themes.listing(os.devnull)
            for item in items:
                item["current"] = item["id"] == self.theme_id
            out = json.dumps(items, ensure_ascii=False)
        else:
            out = ""
        return {"exit code": 0, "exit status": 0, "stdout": out, "stderr": ""}


# --- putting it together ---------------------------------------------------------------------------

def _url(*parts):
    return QUrl.fromLocalFile(os.path.join(STUBS, *parts))


_registered = False


def register():
    """Register every stand-in type with Qt's QML type system (once per process)."""
    global _registered, STATE
    if _registered:
        return
    _registered = True
    STATE = PlasmoidState()
    plasmoid = "org.kde.plasma.plasmoid"
    qmlRegisterSingletonInstance(plasmoid, 1, 0, "Plasmoid", STATE)
    qmlRegisterType(_url("plasma", "PlasmoidItem.qml"), plasmoid, 1, 0, "PlasmoidItem")
    qmlRegisterType(_url("plasma", "WallpaperItem.qml"), plasmoid, 1, 0, "WallpaperItem")
    for name in ("Types", "ToolTipArea", "Dialog"):
        qmlRegisterType(_url("plasma", name + ".qml"), "org.kde.plasma.core", 1, 0, name)
    for name in ("TabBoxSwitcher", "WindowThumbnail"):
        qmlRegisterType(_url("plasma", name + ".qml"), "org.kde.kwin", 3, 0, name)
    for name in ("Menu", "MenuItem", "SearchField"):
        qmlRegisterType(_url("plasma", name + ".qml"), "org.kde.plasma.extras", 1, 0, name)
    for name in ("Label", "Button", "ToolButton", "Switch", "TextField"):
        qmlRegisterType(_url("plasma", name + ".qml"), "org.kde.plasma.components", 3, 0, name)
    for name in ("Theme", "Units"):
        qmlRegisterSingletonType(_url("kirigami", name + ".qml"), "org.kde.kirigami", 2, 0, name)
    for name in ("Icon", "Avatar", "Separator"):
        qmlRegisterType(_url("kirigami", name + ".qml"), "org.kde.kirigami", 2, 0, name)
    qmlRegisterType(TasksModel, "org.kde.taskmanager", 0, 1, "TasksModel")
    # Only its enums are used; PyQt6 refuses qmlRegisterUncreatableType, so it is registered as creatable.
    qmlRegisterType(AbstractTasksModel, "org.kde.taskmanager", 0, 1, "AbstractTasksModel")
    for name in ("VirtualDesktopInfo", "ActivityInfo"):
        qmlRegisterType(_url("plasma", name + ".qml"), "org.kde.taskmanager", 0, 1, name)
    for kind, name in ((RootModel, "RootModel"), (RunnerModel, "RunnerModel"), (SystemModel, "SystemModel"), (AppsModel, "AppsModel")):
        qmlRegisterType(kind, "org.kde.plasma.private.kicker", 0, 1, name)
    qmlRegisterType(_url("plasma", "KUser.qml"), "org.kde.coreaddons", 1, 0, "KUser")
    qmlRegisterType(_url("plasma", "DataSource.qml"), "org.kde.plasma.plasma5support", 2, 0, "DataSource")


def theme_colors(theme_id):
    theme = themes.BY_ID[theme_id]
    hexa = "#%02x%02x%02x"
    return {"highlightColor": hexa % theme.accent, "textColor": hexa % theme.text, "backgroundColor": hexa % theme.ink,
            "alternateBackgroundColor": hexa % theme.raised, "disabledTextColor": hexa % theme.muted,
            "highlightedTextColor": hexa % (theme.on_accent or theme.ink)}


class Session:
    """One preview or test: the shared plasmoid state, the fake shell, and the theme applied to an engine."""

    def __init__(self, theme_id="cyan", config=None, form_factor=2, location=4, animations=True):
        register()
        CALLS.clear()
        STATE.reset(config or {}, form_factor, location)
        self.state = STATE
        self.theme_id = theme_id
        self.shell = Shell(theme_id)
        self.animations = animations

    def prepare(self, engine):
        engine.rootContext().setContextProperty("stubShell", self.shell)
        self.windows = TabBoxModel()
        engine.rootContext().setContextProperty("stubWindows", self.windows)
        theme = engine.singletonInstance(qmlTypeId("org.kde.kirigami", 2, 0, "Theme"))
        for key, value in theme_colors(self.theme_id).items():
            theme.setProperty(key, value)
        if not self.animations:
            units = engine.singletonInstance(qmlTypeId("org.kde.kirigami", 2, 0, "Units"))
            units.setProperty("longDuration", 0)
            units.setProperty("shortDuration", 0)
