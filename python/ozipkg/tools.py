"""The commands `ozi` hands to Python: doctor, report, clean and play."""
import sys

from . import clean, doctor, play, report

COMMANDS = {
    "doctor": doctor.main,
    "report": report.main,
    "clean": clean.main,
    "play": play.main,
}

USAGE = """usage: ozi-tools <command> [options]

  doctor    check that the system is in good shape
  report    write a bug report with names and addresses removed
  clean     free disk space
  play      run a game with game mode on
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0 if argv else 2
    command = COMMANDS.get(argv[0])
    if command is None:
        print("ozi: unknown command %r\n" % argv[0], file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    try:
        return command(argv[1:]) or 0
    except KeyboardInterrupt:
        return 130
    except OSError as err:
        print("ozi %s: %s" % (argv[0], err), file=sys.stderr)
        return 1
