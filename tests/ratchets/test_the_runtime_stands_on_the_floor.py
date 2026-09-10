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

import pytest

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
    "systemctl",
    "curl",
    "journalctl",
    "codex",
    "notify-send",
    "pw-play",
    "ssh",
    "tmux",
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
        machine.codex_home(),
        machine.cgroup_root(),
        machine.acct_cache_dir(),
        machine.applications_dir(),
        machine.control_path(),
    ):
        assert read.resolve().is_relative_to(root), f"{read} is not under the floor {root}"
    # The floor's identity is the floor's, never this laptop's kernel's (card #83).
    assert machine.machine_id() == machine_floor.machine_id
    assert machine.machine_id() != Path("/etc/machine-id").read_text().strip()
    assert not machine.slot_root().resolve().is_relative_to(Path.home() / ".claude-accounts")


MOUNT_TABLE = Path("/proc/mounts")
IN_MEMORY = {"tmpfs", "ramfs"}


def mount_under(path: Path) -> tuple[Path, str]:
    """The mount point the resolved path stands on and its filesystem type:
    the longest mount-point prefix in the kernel's own table. The type is
    read from the table and never guessed from the path, so a machine whose
    temp folder is a disk passes and a `--basetemp` given by hand into
    memory is refused wherever it points (card #109, ruling 4)."""
    resolved = path.resolve()
    best: tuple[Path, str] | None = None
    for line in MOUNT_TABLE.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        point = Path(fields[1].encode("utf-8").decode("unicode_escape"))
        if resolved.is_relative_to(point) and (
            best is None or len(point.parts) > len(best[0].parts)
        ):
            best = (point, fields[2])
    assert best is not None, f"{resolved} is under no mount in {MOUNT_TABLE}"
    return best


def test_the_floors_stand_on_disk(tmp_path_factory: pytest.TempPathFactory):
    """A floor laid in memory is memory the board's floor cannot see and the
    machine kills work for (card #109): the root every floor is laid under
    must stand on a filesystem that is not memory-backed."""
    if not MOUNT_TABLE.exists():
        pytest.skip(f"no mount table at {MOUNT_TABLE}; the floors' filesystem cannot be read")
    root = tmp_path_factory.getbasetemp()
    point, kind = mount_under(root)
    assert kind not in IN_MEMORY, (
        f"the floors' root {root} stands on {point}, a {kind} filesystem in memory: "
        "a test run must never take the memory the work needs (card #109). "
        "Point --basetemp or PYTEST_DEBUG_TEMPROOT at a directory on disk, or unset both "
        "and the suite chooses one under the cache (tests/conftest.py::floors_root)."
    )


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
