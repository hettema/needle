"""The board reads what runs; it never is the thing that runs (INTENT.md, lesson 1).

Nothing under `board/` or `domain/` may spawn a process, open a window or reach
for a shell. The runtime is slice 02's package, reached through a typed
interface; the day that package exists this ratchet still holds, because the
board must never grow its own way of running things.
"""

import ast

from tests.ratchets.paths import python_files

FORBIDDEN_MODULES = {"subprocess", "multiprocessing", "pty", "webbrowser", "asyncio.subprocess"}
FORBIDDEN_OS_CALLS = {"system", "popen", "fork", "forkpty", "kill", "killpg", "startfile"}


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


def test_board_and_domain_spawn_nothing():
    offenders = {
        str(path.relative_to(path.parents[1])): _violations(path.read_text(encoding="utf-8"))
        for path in python_files("board", "domain")
    }
    offenders = {k: v for k, v in offenders.items() if v}
    assert not offenders, f"the board must never run anything: {offenders}"


def test_the_ratchet_sees_what_it_looks_for():
    assert _violations("import subprocess") == ["import subprocess"]
    assert _violations("import os\nos.system('x')") == ["os.system"]
    assert _violations("from os import execv") == ["from os import execv"]
    assert _violations("import os\nos.path.join('a')") == []
