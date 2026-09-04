"""The board reads what runs; it never is the thing that runs (INTENT.md, lesson 1).

Nothing under `board/`, `domain/`, `infrastructure/` or `api/` may spawn a
process, open a window or reach for a shell. The runtime is the one package
that runs things, and inside it `runtime/machine.py` is the one file that
does: every other module of the runtime asks that door, so the fixture floor
can stand in for the machine whole.
"""

import ast

from tests.ratchets.paths import python_files

FORBIDDEN_MODULES = {"subprocess", "multiprocessing", "pty", "webbrowser", "asyncio.subprocess"}
FORBIDDEN_OS_CALLS = {"system", "popen", "fork", "forkpty", "kill", "killpg", "startfile"}
THE_ONE_DOOR = "runtime/machine.py"


def _violations(source: str) -> list[str]:
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES or alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module in FORBIDDEN_MODULES or node.module.split(".")[0] in FORBIDDEN_MODULES:
                found.append(f"from {node.module} import …")
            if node.module == "os" and any(
                a.name in FORBIDDEN_OS_CALLS or a.name.startswith(("exec", "spawn"))
                for a in node.names
            ):
                found.append(f"from os import {', '.join(a.name for a in node.names)}")
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and (node.attr in FORBIDDEN_OS_CALLS or node.attr.startswith(("exec", "spawn")))
        ):
            found.append(f"os.{node.attr}")
    return found


def _offenders(*packages: str) -> dict[str, list[str]]:
    found = {
        str(path.relative_to(path.parents[1])): _violations(path.read_text(encoding="utf-8"))
        for path in python_files(*packages)
    }
    return {k: v for k, v in found.items() if v}


def test_the_board_spawns_nothing():
    offenders = _offenders("board", "domain", "infrastructure", "api")
    assert not offenders, f"the board must never run anything: {offenders}"


def test_only_the_machine_door_of_the_runtime_spawns():
    offenders = {k: v for k, v in _offenders("runtime").items() if k != THE_ONE_DOOR}
    assert not offenders, f"only {THE_ONE_DOOR} may run a process: {offenders}"
    assert _offenders("runtime").get(THE_ONE_DOOR), (
        f"{THE_ONE_DOOR} is the door and should run things"
    )


def test_the_ratchet_sees_what_it_looks_for():
    assert _violations("import subprocess") == ["import subprocess"]
    assert _violations("import os\nos.system('x')") == ["os.system"]
    assert _violations("from os import execv") == ["from os import execv"]
    assert _violations("import os\nos.path.join('a')") == []
