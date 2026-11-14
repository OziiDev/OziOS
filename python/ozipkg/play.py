"""`ozi play`: run a game with the settings that matter, and put things back after.

    ozi play -- <game command>
    ozi play --gpu discrete --mangohud -- <game command>

For Steam, set the launch options of a game to `ozi play -- %command%`.
Game mode (`ozi mode game on`) is switched on while the game runs and off
again when it ends, unless it was already on. On a laptop with two graphics
cards `--gpu discrete` asks for the stronger one.
"""
import os
import shutil
import signal
import subprocess
from dataclasses import dataclass, field

from . import doctor, paths
from .i18n import tr

NVIDIA_OFFLOAD = {"__NV_PRIME_RENDER_OFFLOAD": "1", "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
                  "__VK_LAYER_NV_optimus": "NVIDIA_only"}


@dataclass
class Plan:
    argv: list
    env: dict = field(default_factory=dict)       # variables to add
    notes: list = field(default_factory=list)


def gpu_environment(choice, vendors):
    """(variables, note) that select a graphics card, given the vendors present."""
    if choice == "auto":
        return {}, ""
    if len(vendors) < 2:
        return {}, tr("Only one graphics card was found; nothing to choose.")
    if choice == "discrete":
        if "nvidia" in vendors:
            return dict(NVIDIA_OFFLOAD), ""
        return {"DRI_PRIME": "1"}, ""
    if choice == "integrated":
        return ({"DRI_PRIME": "0"} if "nvidia" not in vendors else {}), ""
    return {}, tr("Unknown graphics choice: {name}", name=choice)


def plan(command, gpu="auto", mangohud=False, gamemode=True, vendors=(), which=shutil.which):
    notes = []
    env, note = gpu_environment(gpu, list(vendors))
    if note:
        notes.append(note)
    argv = list(command)
    if mangohud:
        if which("mangohud"):
            argv = ["mangohud"] + argv
        else:
            notes.append(tr("mangohud is not installed; starting without it."))
    if gamemode and which("gamemoderun"):
        argv = ["gamemoderun"] + argv
    return Plan(argv, env, notes)


def game_mode_active():
    return (paths.state_dir() / "game-mode").exists()


def main(argv=None, out=print, probe=None, run=None, set_mode=None, which=shutil.which):
    import argparse
    parser = argparse.ArgumentParser(prog="ozi play", description=tr("Run a game with game mode on, then put things back."),
                                     usage="ozi play [options] -- command [arguments]")
    parser.add_argument("--gpu", choices=("auto", "integrated", "discrete"), default="auto",
                        help=tr("which graphics card to use on a computer with two"))
    parser.add_argument("--mangohud", action="store_true", help=tr("show the performance overlay"))
    parser.add_argument("--no-gamemode", action="store_true", help=tr("do not use the gamemode helper"))
    parser.add_argument("--no-mode", action="store_true", help=tr("leave game mode alone"))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error(tr("give the game's command after --"))

    probe = probe or doctor.Probe()
    code, text = probe.run(["lspci", "-nn"]) if args.gpu != "auto" else (0, "")
    vendors = [vendor for vendor, _ in doctor.pci_gpus(text)] if code == 0 else []
    chosen = plan(command, gpu=args.gpu, mangohud=args.mangohud, gamemode=not args.no_gamemode, vendors=vendors, which=which)
    for note in chosen.notes:
        out(note)

    if set_mode is None:
        def set_mode(state):
            if which("ozi"):
                subprocess.run(["ozi", "mode", "game", state], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run = run or (lambda argv, env: subprocess.call(argv, env=env))

    turned_on = not args.no_mode and not game_mode_active()
    if turned_on:
        set_mode("on")
    environment = dict(os.environ)
    environment.update(chosen.env)
    old = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        return run(chosen.argv, environment)
    except FileNotFoundError:
        out(tr("{program} was not found.", program=chosen.argv[0]))
        return 127
    except KeyboardInterrupt:
        return 130
    finally:
        signal.signal(signal.SIGTERM, old)
        if turned_on:
            set_mode("off")
