"""No test reaches the machine: the fixture floor is under every test (plan 02, criterion 6).

Two halves. At test time, every path `runtime.machine` answers is under the
floor and every command the runtime would run resolves to a stand-in under
`tests/fakes/bin/`, so a test cannot open a window, touch a subscription or
reach a daemon. Statically, nothing under `runtime/` names a home path,
reads the environment or resolves a command except `runtime/machine.py`, the
one door the floor redirects — a second door would be a path around it.
"""

import ast
from pathlib import Path

from runtime import machine
from tests.floor import FAKE_BIN, Floor
from tests.ratchets.paths import REPO, python_files

THE_ONE_DOOR = REPO / "runtime" / "machine.py"
COMMANDS = (
    "claude",
    "claude-acct",
    "hyprctl",
    "omarchy-launch-tui",
    "busctl",
    "curl",
    "journalctl",
)
FORBIDDEN_CALLS = {"home", "expanduser", "getenv", "which"}
FORBIDDEN_NAMES = {"environ"}


def test_every_path_the_runtime_reads_is_under_the_floor(machine_floor: Floor):
    root = machine_floor.root.resolve()
    for read in (
        machine.slot_root(),
        machine.claude_home(),
        machine.handoff_dir(),
        machine.transcripts_root(),
        machine.roles_path(),
        machine.meminfo_path(),
    ):
        assert read.resolve().is_relative_to(root), f"{read} is not under the floor {root}"
    assert not machine.slot_root().resolve().is_relative_to(Path.home() / ".claude-accounts")


def test_every_command_the_runtime_runs_is_a_stand_in(machine_floor: Floor):
    for name in COMMANDS:
        found = Path(machine.which(name)).resolve()
        assert found.parent == FAKE_BIN.resolve(), f"{name} resolves to {found}, not to the floor"


def _reaches_the_machine(source: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any(n.split(".")[0] in {"subprocess", "shutil"} for n in names):
                found.append(f"import {', '.join(names)}")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_CALLS | FORBIDDEN_NAMES:
            base = node.value
            if isinstance(base, ast.Name) and base.id in {"Path", "os", "shutil"}:
                found.append(f"{base.id}.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith(("/home/", "~", "/proc", "/tmp/cc-daemon")):
                found.append(f"path literal {node.value!r}")
    return found


def test_only_the_machine_door_reaches_the_machine():
    offenders: dict[str, list[str]] = {}
    for path in python_files("runtime"):
        if path.resolve() == THE_ONE_DOOR.resolve():
            continue
        hits = _reaches_the_machine(path.read_text(encoding="utf-8"))
        if hits:
            offenders[str(path.relative_to(REPO))] = hits
    assert not offenders, f"only runtime/machine.py may reach the machine: {offenders}"


def test_the_ratchet_sees_what_it_looks_for():
    assert _reaches_the_machine("from pathlib import Path\nPath.home()") == ["Path.home"]
    assert _reaches_the_machine("import os\nos.environ['X']") == ["os.environ"]
    assert _reaches_the_machine("x = '/home/someone/.claude'") == [
        "path literal '/home/someone/.claude'"
    ]
    assert _reaches_the_machine("import subprocess") == ["import subprocess"]
    assert _reaches_the_machine("from runtime import machine\nmachine.run([])") == []
