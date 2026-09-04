"""The layers import downward only: domain ← board ← infrastructure ← runtime ← api.

`domain/` is what things are and imports nothing of ours; `board/` is what
happens, pure over domain values; `infrastructure/` applies it; `runtime/`
is the thing that runs, with the store for its own records; `api/` is the
door that composes the board and the runtime. A reverse import is how a rule
ends up living in a database session, or a process in the board.
"""

import ast

from tests.ratchets.paths import BACKEND_PACKAGES, python_files

ALLOWED: dict[str, set[str]] = {
    "domain": set(),
    "board": {"domain"},
    "infrastructure": {"domain", "board"},
    "runtime": {"domain", "infrastructure"},
    "api": {"domain", "board", "infrastructure", "runtime"},
}

PURE_THIRD_PARTY = {"pydantic"}
"""What domain/ and board/ may import beyond the standard library."""

STDLIB_HINT = {
    "re",
    "html",
    "enum",
    "datetime",
    "typing",
    "collections",
    "dataclasses",
    "pathlib",
    "json",
    "os",
    "sys",
    "inspect",
    "importlib",
    "types",
    "functools",
    "itertools",
    "asyncio",
    "contextlib",
    "argparse",
}


def _imports(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_no_layer_imports_upward():
    for package in BACKEND_PACKAGES:
        for path in python_files(package):
            ours = _imports(path.read_text(encoding="utf-8")) & set(BACKEND_PACKAGES)
            illegal = ours - ALLOWED[package] - {package}
            assert not illegal, (
                f"{path} imports {illegal}; {package} may import only {ALLOWED[package]}"
            )


def test_domain_and_board_stay_pure():
    for package in ("domain", "board"):
        for path in python_files(package):
            third = _imports(path.read_text(encoding="utf-8")) - set(BACKEND_PACKAGES) - STDLIB_HINT
            unexpected = third - PURE_THIRD_PARTY
            assert not unexpected, (
                f"{path} imports {unexpected}; {package} is pure and may use only pydantic "
                "beyond the standard library"
            )
