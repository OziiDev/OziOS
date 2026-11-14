"""Imported first by the tests that touch ozipkg: they expect English, so the
language of the machine running them must not leak in (the Education ISO's
live session is Turkish). test_i18n sets the language itself where it needs one."""
import os

for _key in ("LC_ALL", "LC_MESSAGES", "LANGUAGE"):
    os.environ.pop(_key, None)
os.environ["LANG"] = "C"
