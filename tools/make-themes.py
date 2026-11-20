"""Write the OziOS colour schemes from the table in python/ozipkg/themes.py.

    python3 tools/make-themes.py

The cyan theme is branding/OziOS.colors (the original file, kept where it was);
the others go to branding/themes/.
"""
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(root, "python"))

from ozipkg import themes  # noqa: E402


def target(theme):
    if theme.id == themes.DEFAULT:
        return os.path.join(root, "branding", theme.file_name)
    return os.path.join(root, "branding", "themes", theme.file_name)


def main():
    os.makedirs(os.path.join(root, "branding", "themes"), exist_ok=True)
    for theme in themes.THEMES:
        with open(target(theme), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(themes.render(theme))
        print(os.path.relpath(target(theme), root))


if __name__ == "__main__":
    main()
