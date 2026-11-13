"""Turkish translations for user-facing text.

Source strings are English. `tr()` looks them up in data/i18n/tr.json when the
session language is Turkish and returns the English text otherwise, so a
missing entry never breaks anything.
"""
import json
import os

from . import paths

_table = None


def _language():
    for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(name, "")
        if value:
            return value.split(":")[0].split("_")[0].split(".")[0].lower()
    return "en"


def _load():
    global _table
    if _table is None:
        _table = {}
        if _language() == "tr":
            try:
                with open(paths.data_file("i18n", "tr.json"), encoding="utf-8") as fh:
                    _table = json.load(fh)
            except (OSError, ValueError):
                _table = {}
    return _table


def tr(text, /, **values):
    out = _load().get(text, text)
    return out.format(**values) if values else out


def reset():
    """Forget the loaded table (tests change the language between cases)."""
    global _table
    _table = None
