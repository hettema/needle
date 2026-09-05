"""Reading the machine's doctrine delivery: two links, and no machine code.

`needle add` says whether a session started in a project will read this
repository's `docs/HOW-WE-WORK.md` as its constitution. It answers by resolving
the files a provider injects and comparing them to the HOW-WE-WORK that ships
with the running `needle` — `Path(__file__)`, never a configured path, because a
configured one could be made to agree with anything and the question is whether
*this* installation's text is what a session sees.

Why the board owns this and not the machine: it is the one reader that exists
wherever Needle is installed, it reads two links and runs nothing, and it is
what makes "wherever it runs" a sentence the board can check on a laptop it has
never seen. The board never runs a process, so Codex's presence is read from
`PATH` (`shutil.which`) rather than from `codex --version`; a version is the
machine's question, an installation is the board's.
"""

import shutil
from datetime import datetime
from pathlib import Path

from domain.entrance import Entrance, EntranceWord, InjectedFile

LANES = Path(".claude") / "worktrees"
"""Where a lane's worktree lives inside the project it is a copy of."""


def _installed_root() -> Path:
    """The project the running `needle` belongs to, from its own file.

    A lane runs `needle` from its worktree, so `__file__` lands under
    `.claude/worktrees/<lane>/` — a copy of the project at another revision,
    not another project. Read literally, the door would then tell every lane
    `two-texts` for as long as lanes exist, because the injected file resolves
    to the main checkout's copy and never to the lane's. The suffix is stripped
    so the question stays the one worth asking: does the machine deliver *this
    project's* text?
    """
    return project_of(Path(__file__).resolve().parents[1])


def project_of(root: Path) -> Path:
    """`root` with a lane's `.claude/worktrees/<lane>` suffix stripped."""
    parts = root.parts
    marker = LANES.parts
    for i in range(len(parts) - len(marker)):
        if parts[i : i + len(marker)] == marker:
            return Path(*parts[:i])
    return root


HOW_WE_WORK = _installed_root() / "docs" / "HOW-WE-WORK.md"
"""The one text, as the running `needle` was installed with it."""

CLAUDE_ENTRANCE = Path(".claude/CLAUDE.md")
CODEX_ENTRANCE = Path(".codex/AGENTS.md")
CODEX_COMMAND = "codex"


def _resolved(path: Path) -> Path | None:
    """The file every link leads to, or None when the chain ends nowhere.

    `Path.resolve()` on a missing path still returns a path, so existence is
    asked separately; a dangling symlink and an absent file are the same answer
    here, because a session reads neither."""
    try:
        target = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return target if target.is_file() else None


def read_entrance(
    home: Path, at: datetime, doctrine: Path = HOW_WE_WORK, has_codex: bool | None = None
) -> Entrance:
    """What a session started under `home` reads as its constitution."""
    one_text = _resolved(doctrine)
    codex = shutil.which(CODEX_COMMAND) is not None if has_codex is None else has_codex
    injected = [home / CLAUDE_ENTRANCE] + ([home / CODEX_ENTRANCE] if codex else [])

    files: list[InjectedFile] = []
    for path in injected:
        target = _resolved(path)
        files.append(
            InjectedFile(
                path=_spoken(home, path),
                resolves_to=str(target) if target is not None else None,
                is_the_one_text=target is not None and one_text is not None and target == one_text,
            )
        )

    missing = [f for f in files if f.resolves_to is None]
    elsewhere = [f for f in files if f.resolves_to is not None and not f.is_the_one_text]
    if missing:
        word = EntranceWord.NONE
        is_are = "is" if len(missing) == 1 else "are"
        line = (
            f"entrance: none — {_named(missing)} {is_are} not there, so a session here "
            "enters with no doctrine."
        )
    elif elsewhere:
        word = EntranceWord.TWO_TEXTS
        targets = sorted({f.resolves_to for f in elsewhere if f.resolves_to is not None})
        line = (
            f"entrance: two-texts {' '.join(targets)} — {_named(elsewhere)} "
            f"{_resolve(elsewhere)} there, not to {doctrine}, so sessions here obey a "
            "second doctrine."
        )
    else:
        word = EntranceWord.ONE_TEXT
        line = f"entrance: one-text — {_named(files)} {_resolve(files)} to {doctrine}."

    return Entrance(word=word, line=line, files=files, read_at=at)


def _spoken(home: Path, path: Path) -> str:
    """The injected path as the person knows it, with their home written `~`."""
    try:
        return f"~/{path.relative_to(home)}"
    except ValueError:
        return str(path)


def _named(files: list[InjectedFile]) -> str:
    return " and ".join(f.path for f in files)


def _resolve(files: list[InjectedFile]) -> str:
    return "resolves" if len(files) == 1 else "resolve"
