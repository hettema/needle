"""Typed edges, lossless: the frontend mirrors the domain and never says `any`.

The TypeScript types are generated from the Pydantic models, so a backend shape
change that is not regenerated fails here before it fails in the browser; and
no file in the frontend may open a hole in the types.
"""

import json
import re

from api.typegen import MODULES, TYPES_DIR, generate
from tests.ratchets.paths import REPO, frontend_files, python_files

HOLES = re.compile(
    r":\s*any\b|<any>|\bas\s+any\b|\bany\[\]|Record<string,\s*(?:unknown|any|object)>|@ts-ignore|@ts-expect-error|eslint-disable|\bunknown\[\]"
)


def test_the_generated_types_are_what_is_on_disk():
    expected = generate()
    stale: list[str] = []
    for module, content in expected.items():
        path = TYPES_DIR / f"{module}.ts"
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(module)
    extra = sorted(p.stem for p in TYPES_DIR.glob("*.ts") if p.stem not in expected)
    assert not stale and not extra, (
        f"frontend/src/types is behind the domain (stale: {stale}, unexpected: {extra}); "
        "run `uv run needle types`"
    )


def test_every_domain_module_is_mirrored():
    modules = sorted(p.stem for p in python_files("domain") if p.stem != "__init__")
    assert sorted(MODULES) == modules, "add the new domain module to api.typegen.MODULES"


def test_no_hole_in_the_frontend_types():
    offenders: list[str] = []
    for path in frontend_files() + sorted((REPO / "frontend" / "tests").rglob("*.ts*")):
        if path.suffix == ".css":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if HOLES.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert not offenders, "type holes:\n" + "\n".join(offenders)


def test_the_compiler_is_strict():
    config = json.loads((REPO / "frontend" / "tsconfig.json").read_text(encoding="utf-8"))
    options = config["compilerOptions"]
    assert options["strict"] is True and options["noImplicitAny"] is True
    assert options["noUncheckedIndexedAccess"] is True
