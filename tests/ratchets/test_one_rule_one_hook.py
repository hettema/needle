"""Two boundaries of slice 03, held.

The model rule is one function (INTENT.md lesson 6) and it lives in
`claude-acct`: inside Needle a `Placement` is constructed only where the
rule's answer is parsed (`runtime/rule.py`) and where the wall detector's
handoff is read (`runtime/launch.py`). A third place would be a second
chooser, which is how 0.1 came to give two answers.

The session hook must never block a session and must survive the board
being down (plan 03, item 3): it imports the standard library only, wraps
everything in one catch-all, writes nothing to stdout, and is registered in
this repository's own Claude settings so Needle's own sessions push too.
"""

import ast
import json
import sys

from tests.ratchets.paths import REPO, python_files

PLACEMENT_MAKERS = {"runtime/rule.py", "runtime/launch.py"}
HOOK = REPO / "hooks" / "needle_hook.py"
HOOK_EVENTS = {"SessionStart", "Stop", "SessionEnd", "StopFailure"}


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


def test_the_hook_is_standard_library_only_and_never_raises():
    source = HOOK.read_text(encoding="utf-8")
    third_party = _imports(source) - set(sys.stdlib_module_names)
    assert not third_party, f"the hook imports {third_party}; it runs under any python3 alone"
    tree = ast.parse(source)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    assert isinstance(main.body[0], ast.Try), "main() must wrap everything in a try"
    handlers = main.body[0].handlers
    assert any(
        h.type is None or (isinstance(h.type, ast.Name) and h.type.id == "Exception")
        for h in handlers
    ), "the catch-all is what keeps a broken bridge from breaking a session"
    assert "print(" not in source, "a hook that writes to stdout writes into the session"


def test_the_hook_is_registered_in_this_repositorys_own_settings():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    for event in HOOK_EVENTS:
        commands = [h["command"] for entry in hooks.get(event, []) for h in entry.get("hooks", [])]
        assert any(c.endswith("hooks/needle_hook.py") for c in commands), (
            f"{event} does not run the Needle hook"
        )
