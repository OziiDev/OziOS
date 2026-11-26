"""Translations of user-facing text.

Source strings are English. `tr()` looks them up in data/i18n/<language>.json
(pt_BR.json before pt.json) for the session language and returns the English
text when there is no table or no entry, so a missing one never breaks anything.
"""
import json
import os

from . import paths

_table = None


def locale_name():
    """The session's locale, like "tr_TR" or "pt_BR"; "en" when none is set."""
    for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(name, "")
        if value and value not in ("C", "POSIX") and not value.startswith("C."):
            return value.split(":")[0].split(".")[0].split("@")[0]
    return "en"


def _language():
    return locale_name().split("_")[0].lower()


def languages():
    """The languages there is a table for (file names without .json)."""
    try:
        folder = os.path.dirname(paths.data_file("i18n", "tr.json"))
        return sorted(f[:-5] for f in os.listdir(folder) if f.endswith(".json"))
    except OSError:
        return []


def _load():
    global _table
    if _table is None:
        _table = {}
        full = locale_name()
        for name in (full, _language()):
            if name == "en":
                break
            try:
                with open(paths.data_file("i18n", name + ".json"), encoding="utf-8") as fh:
                    _table = json.load(fh)
                break
            except (OSError, ValueError):
                continue
    return _table


def tr(text, /, **values):
    out = _load().get(text, text)
    return out.format(**values) if values else out


def reset():
    """Forget the loaded table (tests change the language between cases)."""
    global _table
    _table = None
