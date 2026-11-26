import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from ozipkg import tray  # noqa: E402


def v(t, d):
    return {"type": t, "data": d}


class Tray(unittest.TestCase):
    def test_where_an_item_lives(self):
        self.assertEqual(tray.split_service(":1.4"), (":1.4", "/StatusNotifierItem"))
        self.assertEqual(tray.split_service("/org/ayatana/NotificationItem/x", ":1.9"), (":1.9", "/org/ayatana/NotificationItem/x"))
        self.assertEqual(tray.split_service(":1.9/StatusNotifierItem"), (":1.9", "/StatusNotifierItem"))

    def test_item_properties(self):
        reply = {"type": "a{sv}", "data": [{
            "Id": v("s", "vesktop"), "Title": v("s", "Vesktop"), "IconName": v("s", "vesktop"),
            "Status": v("s", "Active"), "Menu": v("o", "/MenuBar"), "ItemIsMenu": v("b", False),
            "ToolTip": v("(sa(iiay)ss)", ["", [], "Vesktop", "2 new messages"])}]}
        item = tray.item_view(":1.4/StatusNotifierItem", tray.parse_props(reply))
        self.assertEqual(item["title"], "Vesktop")
        self.assertEqual(item["icon"], "vesktop")
        self.assertEqual(item["menu"], "/MenuBar")

    def test_largest_fitting_pixmap(self):
        small = [16, 16, [0] * 16 * 16 * 4]
        big = [64, 64, [0] * 64 * 64 * 4]
        broken = [32, 32, [0, 1]]
        self.assertEqual(tray.best_pixmap([small, big, broken], 48)[0], 64)
        self.assertEqual(tray.best_pixmap([small], 48)[0], 16)
        self.assertIsNone(tray.best_pixmap([broken]))

    def test_menu_layout(self):
        def node(i, props, kids=()):
            return v("(ia{sv}av)", [i, {k: v("s", x) if isinstance(x, str) else v("b", x) for k, x in props.items()}, list(kids)])
        reply = {"type": "u(ia{sv}av)", "data": [3, [0, {}, [
            node(1, {"label": "_Open"}),
            node(2, {"type": "separator"}),
            node(3, {"type": "separator"}),
            node(4, {"label": "Hidden", "visible": False}),
            node(5, {"label": "Status", "children-display": "submenu"}, [node(6, {"label": "Online"})]),
            node(7, {"label": "Quit", "enabled": False}),
            node(8, {"type": "separator"}),
        ]]]}
        entries = tray.parse_menu(reply)
        self.assertEqual([e["label"] for e in entries], ["Open", "", "Status", "Online", "Quit"])
        self.assertEqual(entries[3]["depth"], 1)
        self.assertFalse(entries[4]["enabled"])


if __name__ == "__main__":
    unittest.main()
