"""Start is the owner's move, held by a ratchet (plan 07, item 3; plan 11, item 4).

INTENT.md: one move is his — he decides what enters execution. Until plan
11 that meant one thing: the runtime's `start`, the one call that puts hands
on a fresh worktree, is reached only from the modules where a person
presses — `api/doors.py`, the doors on the page, and `api/runtime_cli.py`,
`needle start` in his own terminal — and never from `api/loops.py`, the
module of what the board does by itself on evidence. Plan 11 added the
second way his move is made: a standing ruling, the dial, applied by the
board. The ratchet moved to the altitude of the intent rather than the
method: every start is his — his click through a door, or his ruling
through the dial — and nothing else. Mechanised:

- `runtime.start` / `launch.start` are still reached only from the pressed
  modules; the dial presses the Start *door*, so there is one start and it
  writes one history.
- Plan 59 added a third thing that puts hands on a fresh worktree: a corpus
  lane, which applies a decision the record already made — the owner's own
  answer, or a separation an independent reading proposed. It is his too, and
  it is held the same way rather than left to the letter of the two tests
  above, which it would have passed without being seen: it reaches
  `runtime.start` only from the doors module, only two door functions reach
  that call at all, and only the dial opens a corpus lane.
- The loops still never start anything and never import the doors: a loop
  that starts the top card when the machine is idle is one line, locally
  reasonable, and would fail no test but this one (0.1's rot).
- The door is opened as the machine (`actor=Actor.MACHINE`) from exactly
  one module, `api/dial.py`, whose only start is under the dial — and the
  behaviour half, that with the dial off nothing starts however eligible
  the rail is, is `tests/api/test_dial.py`.
"""

import ast

from tests.ratchets.paths import python_files

THE_DOORS = "api/doors.py"
THE_TERMINAL = "api/runtime_cli.py"
PRESSED = {THE_DOORS, THE_TERMINAL}
"""Where a person presses: the page's doors, and his own terminal's verbs."""
THE_LOOPS = "api/loops.py"
THE_DIAL = "api/dial.py"
"""Where his standing ruling is applied: the one module that opens the Start
door with the machine as the actor."""


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


def machine_starts_in(source: str) -> list[str]:
    """Every call of a `start` that names its actor: the door opened as the
    machine, or as anyone but the default owner."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        chain = _names(node.func)
        if chain and chain[-1] == "start" and any(k.arg == "actor" for k in node.keywords):
            found.append(".".join(chain))
    return found


def start_functions(source: str) -> set[str]:
    """The functions in a module that reach the runtime's start, by name."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
        if any(starts_in(ast.unparse(call)) for call in calls):
            found.add(node.name)
    return found


def calls_of(source: str, name: str) -> list[str]:
    """Every call of a method with this name, by its dotted chain."""
    return [
        ".".join(_names(node.func))
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and _names(node.func)[-1:] == [name]
    ]


def _imports(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }


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
    assert not offenders, f"Start is the owner's move; only {PRESSED} may reach it: {offenders}"
    assert starts_in(_api_sources()[THE_DOORS]), f"{THE_DOORS} is the door and should start lanes"
    assert not starts_in(_api_sources()[THE_LOOPS])
    assert not starts_in(_api_sources()[THE_DIAL]), (
        f"{THE_DIAL} presses the Start door, never the runtime: one start, one history"
    )


def test_the_loops_never_reach_the_doors_or_the_dial():
    """A loop that imported the doors, or the dial, could press Start by
    another name."""
    imports = _imports(_api_sources()[THE_LOOPS])
    assert not any(
        m in ("api.doors", "api.dial") or m.startswith(("api.doors.", "api.dial.")) for m in imports
    ), f"{THE_LOOPS} imports the doors or the dial: {imports}"


def test_only_the_dial_opens_the_door_as_the_machine():
    """The door's default actor is the owner; naming another is the dial's
    alone, and the card's history then says *started by the dial*."""
    offenders = {
        name: calls
        for name, calls in ((n, machine_starts_in(s)) for n, s in _api_sources().items())
        if calls and name != THE_DIAL
    }
    assert not offenders, f"only {THE_DIAL} opens Start as the machine: {offenders}"
    assert machine_starts_in(_api_sources()[THE_DIAL]) == ["self.doors.start"]


def test_only_two_doors_put_hands_on_a_fresh_worktree_and_only_the_dial_opens_the_second():
    """Plan 59's corpus lane is the third way his move is made, and it is
    named rather than tolerated. A fourth would be a new way to put hands on
    a tree that no test would have noticed — which is the whole failure this
    ratchet exists to make loud."""
    sources = _api_sources()
    assert start_functions(sources[THE_DOORS]) == {"start", "corpus_lane"}, (
        "a new door reaches the runtime's start; say here which move it is, and whose"
    )
    for name, source in sources.items():
        if name == THE_DOORS:
            continue
        assert not calls_of(source, "corpus_lane") or name == THE_DIAL, (
            f"{name} opens a corpus lane; only {THE_DIAL} does, under his ruling or his answer"
        )
    assert calls_of(sources[THE_DIAL], "corpus_lane") == ["self.doors.corpus_lane"]


def test_the_ratchet_sees_what_it_looks_for():
    assert starts_in("self.runtime.start(Start(...))") == ["self.runtime.start"]
    assert starts_in("runtime.start(x)") == ["runtime.start"]
    assert starts_in("launch.start(store, request)") == ["launch.start"]
    assert starts_in("from runtime.launch import start\nstart()") == [
        "from runtime.launch import start"
    ]
    assert starts_in("await loops.start()") == []
    assert starts_in("self.runtime.resume(x)") == []
    assert machine_starts_in("self.doors.start(s, n, anyway=False, actor=Actor.MACHINE)") == [
        "self.doors.start"
    ]
    assert machine_starts_in("doors.start(s, n, anyway=False)") == []
    assert start_functions("def a():\n    self.runtime.start(x)\ndef b():\n    pass\n") == {"a"}
    assert calls_of("self.doors.corpus_lane(s, n)", "corpus_lane") == ["self.doors.corpus_lane"]
    assert calls_of("self.doors.start(s, n)", "corpus_lane") == []
