"""Two boundaries, held: the model rule is one function, and the session
hook never breaks a session.

The model rule lives in `claude-acct` (INTENT.md lesson 6): inside Needle a
`Placement` is constructed only where the rule's answer is parsed
(`runtime/rule.py`) and where the wall detector's handoff is read
(`runtime/launch.py`). A third place would be a second chooser, which is
how 0.1 came to give two answers.

The session hook runs inside every session's every tool call on this
machine (plan 03, item 3; plan 10, item 2). It must never block a session
and must survive the board being down: it imports the standard library
only and wraps everything in one catch-all. And the hook's own failures
never reach the session: the only thing it may write to stdout is the
board's word for the lane, from the one function that answers PostToolUse,
whose every path runs inside its own catch-all — a traceback, a stray
debug line or a partial answer on stdout would land in the model's context
as if the board had said it. Until plan 10 the rule was "no `print(` in the
script", which held the method; this holds the intent. The hook is
registered in this repository's own Claude settings for every event it
serves, so Needle's own sessions push and hear too.
"""

import ast
import json
import sys

from tests.ratchets.paths import REPO, python_files

PLACEMENT_MAKERS = {"runtime/rule.py", "runtime/launch.py"}
HOOK = REPO / "hooks" / "needle_hook.py"
HOOK_EVENTS = {"SessionStart", "Stop", "SessionEnd", "StopFailure", "PostToolUse"}
ANSWERS = "answer"
"""The one function in the hook that may write to stdout."""


def _constructs_placement(source: str) -> bool:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
            if name == "Placement":
                return True
    return False


def test_a_placement_is_made_only_where_the_rule_answers_or_the_handoff_is_read():
    makers = {
        str(path.relative_to(REPO))
        for path in python_files("domain", "board", "infrastructure", "runtime", "api")
        if _constructs_placement(path.read_text(encoding="utf-8"))
    }
    assert makers == PLACEMENT_MAKERS, (
        f"a Placement is constructed in {makers - PLACEMENT_MAKERS}: that is a second model "
        "chooser; ask the rule instead"
    )


def _imports(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _catches_all(function: ast.FunctionDef) -> bool:
    """The function's body, after its docstring, is one try whose handlers
    include a catch-all, followed at most by a `return` of a constant."""
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    if not body or not isinstance(body[0], ast.Try):
        return False
    tail_is_plain = all(
        isinstance(s, ast.Return) and (s.value is None or isinstance(s.value, ast.Constant))
        for s in body[1:]
    )
    return tail_is_plain and any(
        h.type is None or (isinstance(h.type, ast.Name) and h.type.id == "Exception")
        for h in body[0].handlers
    )


def _writes_stdout(node: ast.AST) -> bool:
    """A `print(...)`, anything reached through `sys.stdout`, or `os.write(...)`."""
    if isinstance(node, ast.Call):
        callee = node.func
        if isinstance(callee, ast.Name) and callee.id == "print":
            return True
        if (
            isinstance(callee, ast.Attribute)
            and callee.attr == "write"
            and isinstance(callee.value, ast.Name)
            and callee.value.id == "os"
        ):
            return True
    return isinstance(node, ast.Attribute) and node.attr == "stdout"


def stdout_writes_outside(source: str, allowed: str) -> list[str]:
    """Every write to stdout in `source` that is not inside the function
    named `allowed`, each as `<function or module>:<line>`."""
    tree = ast.parse(source)
    found: list[str] = []
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    for function in functions:
        if function.name == allowed:
            continue
        found.extend(
            f"{function.name}:{inner.lineno}"
            for inner in ast.walk(function)
            if _writes_stdout(inner)
        )
    inside = {id(inner) for f in functions for inner in ast.walk(f)}
    found.extend(
        f"<module>:{node.lineno}"
        for node in ast.walk(tree)
        if id(node) not in inside and _writes_stdout(node)
    )
    return found


def _function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_the_hook_is_standard_library_only_and_never_raises():
    source = HOOK.read_text(encoding="utf-8")
    third_party = _imports(source) - set(sys.stdlib_module_names)
    assert not third_party, f"the hook imports {third_party}; it runs under any python3 alone"
    assert _catches_all(_function(source, "main")), (
        "main() wraps everything in one try with a catch-all"
    )


def test_the_hooks_own_failures_never_reach_the_session():
    source = HOOK.read_text(encoding="utf-8")
    outside = stdout_writes_outside(source, ANSWERS)
    assert not outside, (
        f"the hook writes to stdout outside {ANSWERS}() at {outside}: only the board's word "
        "may reach the session, from the one function that answers PostToolUse"
    )
    answers = _function(source, ANSWERS)
    assert _catches_all(answers), (
        f"{ANSWERS}() holds its every path inside one catch-all: a traceback on stdout would "
        "land in the model's context as if the board had said it"
    )
    assert any(_writes_stdout(n) for n in ast.walk(answers)), (
        f"{ANSWERS}() is where the word is printed; if that moved, move {ANSWERS} with it"
    )


def _line_of(source: str, text: str) -> int:
    for number, line in enumerate(source.splitlines(), 1):
        if text in line:
            return number
    raise AssertionError(f"{text!r} is not in the source")


def test_the_ratchet_sees_a_print_from_main_and_a_write_at_the_top():
    """The check proves it looks where it says: a copy of the script that
    prints from main() is refused, one that writes at module level is
    refused, and the script as it is passes."""
    source = HOOK.read_text(encoding="utf-8")
    leaking = source.replace(
        "def main() -> int:\n    try:\n",
        'def main() -> int:\n    try:\n        print("debug")\n',
        1,
    )
    assert leaking != source
    assert stdout_writes_outside(leaking, ANSWERS) == [
        f"main:{_line_of(leaking, 'print("debug")')}"
    ]
    top = source + '\nsys.stdout.write("x")\n'
    assert stdout_writes_outside(top, ANSWERS) == [
        f"<module>:{_line_of(top, 'sys.stdout.write("x")')}"
    ]
    assert stdout_writes_outside(source, ANSWERS) == []


def test_the_hook_is_registered_in_this_repositorys_own_settings():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    for event in HOOK_EVENTS:
        commands = [h["command"] for entry in hooks.get(event, []) for h in entry.get("hooks", [])]
        assert any(c.endswith("hooks/needle_hook.py") for c in commands), (
            f"{event} does not run the Needle hook"
        )
    word_hooks = [h for entry in hooks["PostToolUse"] for h in entry.get("hooks", [])]
    assert all(isinstance(h.get("timeout"), int) and h["timeout"] <= 10 for h in word_hooks), (
        "the PostToolUse entry names its own ceiling; Claude Code's default is 600 s"
    )
