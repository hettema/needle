"""Start is the owner's click, held by a ratchet (plan 07, item 3).

INTENT.md: one move is his. The runtime's `start` — the one call that puts
hands on a fresh worktree — is reached only from the modules where a person
presses: `api/doors.py`, the doors on the page, and `api/runtime_cli.py`,
`needle start` in his own terminal. Never from `api/loops.py`, the module of
what the board does by itself. 0.1 held the same intent by reading its
server's AST; the rot it named still applies here: a loop that starts the
top card when the machine is idle is one line, locally reasonable, and would
fail no test but this one. The ratchet reads the AST, not the prose: any
call of an attribute named `start` on something called `runtime`, or of
`launch.start`, anywhere under `api/` but the pressed modules, is refused —
and so is a loop reaching the doors at all.
"""

import ast

from tests.ratchets.paths import python_files

THE_DOORS = "api/doors.py"
THE_TERMINAL = "api/runtime_cli.py"
PRESSED = {THE_DOORS, THE_TERMINAL}
"""Where a person presses: the page's doors, and his own terminal's verbs."""
THE_LOOPS = "api/loops.py"


def _names(node: ast.expr) -> list[str]:
    """The dotted chain of a call target, outermost first:
    `self.runtime.start` → [self, runtime, start]."""
    chain: list[str] = []
    while isinstance(node, ast.Attribute):
        chain.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        chain.append(node.id)
    return list(reversed(chain))


def starts_in(source: str) -> list[str]:
    """Every call in the source that reaches the runtime's start."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        chain = _names(node.func)
        if len(chain) >= 2 and chain[-1] == "start" and chain[-2] in {"runtime", "launch"}:
            found.append(".".join(chain))
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "runtime.launch"
            and any(alias.name == "start" for alias in node.names)
        ):
            found.append("from runtime.launch import start")
    return found


def _api_sources() -> dict[str, str]:
    return {
        str(path.relative_to(path.parents[1])): path.read_text(encoding="utf-8")
        for path in python_files("api")
    }


def test_only_the_doors_reach_the_runtimes_start():
    offenders = {
        name: calls
        for name, calls in ((n, starts_in(s)) for n, s in _api_sources().items())
        if calls and name not in PRESSED
    }
    assert not offenders, f"Start is the owner's click; only {PRESSED} may reach it: {offenders}"
    assert starts_in(_api_sources()[THE_DOORS]), f"{THE_DOORS} is the door and should start lanes"
    assert not starts_in(_api_sources()[THE_LOOPS])


def test_the_loops_never_reach_the_doors():
    """A loop that imported the doors could press Start by another name."""
    imports = {
        node.module
        for node in ast.walk(ast.parse(_api_sources()[THE_LOOPS]))
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(ast.parse(_api_sources()[THE_LOOPS]))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(m == "api.doors" or m.startswith("api.doors.") for m in imports), (
        f"{THE_LOOPS} imports the doors: {imports}"
    )


def test_the_ratchet_sees_what_it_looks_for():
    assert starts_in("self.runtime.start(Start(...))") == ["self.runtime.start"]
    assert starts_in("runtime.start(x)") == ["runtime.start"]
    assert starts_in("launch.start(store, request)") == ["launch.start"]
    assert starts_in("from runtime.launch import start\nstart()") == [
        "from runtime.launch import start"
    ]
    assert starts_in("await loops.start()") == []
    assert starts_in("self.runtime.resume(x)") == []
