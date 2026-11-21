#!/usr/bin/env python3
"""A pretend media player on the session bus, for trying the clock's music part
in a session without music: it speaks MPRIS (org.mpris.MediaPlayer2) like a real
player, plays nothing, and moves through a short list of tracks.

    python3 tools/fake-mpris.py [seconds]      (default 600, then it goes away)

Run it as the user of the session. Needs dbus-python and PyGObject, which the
OziOS image carries.
"""
import sys

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

NAME = "org.mpris.MediaPlayer2.ozidemo"
PATH = "/org/mpris/MediaPlayer2"
ROOT = "org.mpris.MediaPlayer2"
PLAYER = "org.mpris.MediaPlayer2.Player"
PROPS = "org.freedesktop.DBus.Properties"
TRACKS = [("Akış", "Ozi"), ("Gece Yolu", "Ozi"), ("Mavi", "Ozi")]


class Player(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, PATH)
        self.index = 0
        self.status = "Playing"

    def metadata(self):
        title, artist = TRACKS[self.index]
        return dbus.Dictionary({
            "mpris:trackid": dbus.ObjectPath("/org/ozios/track/%d" % self.index),
            "mpris:length": dbus.Int64(200 * 1000000),
            "xesam:title": dbus.String(title),
            "xesam:artist": dbus.Array([artist], signature="s"),
            "xesam:album": dbus.String("OziOS"),
        }, signature="sv")

    def values(self, interface):
        if interface == ROOT:
            return {"Identity": "OziOS demo", "DesktopEntry": "", "CanQuit": False, "CanRaise": False,
                    "HasTrackList": False, "SupportedUriSchemes": dbus.Array([], signature="s"),
                    "SupportedMimeTypes": dbus.Array([], signature="s")}
        if interface == PLAYER:
            return {"PlaybackStatus": self.status, "Metadata": self.metadata(), "Rate": 1.0, "Volume": 1.0,
                    "Position": dbus.Int64(0), "MinimumRate": 1.0, "MaximumRate": 1.0, "CanGoNext": True,
                    "CanGoPrevious": True, "CanPlay": True, "CanPause": True, "CanSeek": False, "CanControl": True}
        raise dbus.exceptions.DBusException("org.freedesktop.DBus.Error.UnknownInterface", interface)

    def changed(self, *names):
        player = self.values(PLAYER)
        self.PropertiesChanged(PLAYER, dbus.Dictionary({n: player[n] for n in names}, signature="sv"),
                               dbus.Array([], signature="s"))

    @dbus.service.method(PROPS, in_signature="ss", out_signature="v")
    def Get(self, interface, name):
        return self.values(interface)[name]

    @dbus.service.method(PROPS, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return dbus.Dictionary(self.values(interface), signature="sv")

    @dbus.service.method(PROPS, in_signature="ssv")
    def Set(self, interface, name, value):
        pass

    @dbus.service.signal(PROPS, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    @dbus.service.method(ROOT)
    def Raise(self):
        pass

    @dbus.service.method(ROOT)
    def Quit(self):
        GLib.idle_add(LOOP.quit)

    @dbus.service.method(PLAYER)
    def PlayPause(self):
        self.status = "Paused" if self.status == "Playing" else "Playing"
        self.changed("PlaybackStatus")

    @dbus.service.method(PLAYER)
    def Play(self):
        self.status = "Playing"
        self.changed("PlaybackStatus")

    @dbus.service.method(PLAYER)
    def Pause(self):
        self.status = "Paused"
        self.changed("PlaybackStatus")

    @dbus.service.method(PLAYER)
    def Stop(self):
        self.status = "Stopped"
        self.changed("PlaybackStatus")

    @dbus.service.method(PLAYER)
    def Next(self):
        self.index = (self.index + 1) % len(TRACKS)
        self.status = "Playing"
        self.changed("Metadata", "PlaybackStatus")

    @dbus.service.method(PLAYER)
    def Previous(self):
        self.index = (self.index - 1) % len(TRACKS)
        self.status = "Playing"
        self.changed("Metadata", "PlaybackStatus")

    @dbus.service.method(PLAYER, in_signature="x")
    def Seek(self, offset):
        pass


if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    name = dbus.service.BusName(NAME, bus)
    player = Player(bus)
    LOOP = GLib.MainLoop()
    GLib.timeout_add_seconds(int(sys.argv[1]) if len(sys.argv) > 1 else 600, LOOP.quit)
    print("playing as", NAME, flush=True)
    LOOP.run()
