#!/usr/bin/env python3
"""Merge new Turkish translations into data/i18n/tr.json, keeping it sorted.

    python tools/merge-tr.py new-entries.json

The argument is a JSON object of English text -> Turkish text. Existing
entries with the same key are replaced. Run the tests afterwards: they check
that every string in the code has an entry and that placeholders match.
"""
import json
import sys
from pathlib import Path

TABLE = Path(__file__).resolve().parent.parent / "data" / "i18n" / "tr.json"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    table.update(new)
    TABLE.write_text(json.dumps(dict(sorted(table.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("%d entries merged, %d in the table" % (len(new), len(table)))


if __name__ == "__main__":
    main()
