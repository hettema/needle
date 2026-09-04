"""The corpus on disk: reading every plan and suggestion, and hearing them change.

Four folders, read whole on every change. A full read of Hello Revenue's 690
documents takes well under a second and is the same code path at startup and
on a change, so the index can never be half-updated.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from watchfiles import Change, awatch

from board.parse import parse_document
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind

FOLDERS: list[tuple[DocumentKind, str, bool]] = [
    (DocumentKind.PLAN, "docs/plans", False),
    (DocumentKind.PLAN, "docs/plans/done", True),
    (DocumentKind.SUGGESTION, "docs/slice-suggestions", False),
    (DocumentKind.SUGGESTION, "docs/slice-suggestions/done", True),
]

WATCH_ROOT = "docs"
"""What the watcher subscribes to: the whole of docs/, filtered down to the four
folders. Subscribing to the folders themselves missed any folder created after
the server started — the first suggestion written into a new
docs/slice-suggestions/ was not a card until a restart (2026-09-04)."""


class NotACorpus(Exception):
    """The path does not keep plans where the board reads them."""


def check_corpus(root: Path) -> None:
    if not (root / "docs" / "plans").is_dir():
        raise NotACorpus(
            f"{root} has no docs/plans/ folder, so it is not a corpus the board can read."
        )


def read_document(
    root: Path, kind: DocumentKind, folder: str, archived: bool, file: Path, read_at: datetime
) -> Document:
    text = file.read_text(encoding="utf-8", errors="replace")
    return parse_document(
        text, kind=kind, path=f"{folder}/{file.name}", archived=archived, read_at=read_at
    )


def scan(root: Path, read_at: datetime) -> CorpusIndex:
    documents: list[Document] = []
    for kind, folder, archived in FOLDERS:
        directory = root / folder
        if not directory.is_dir():
            continue
        for file in sorted(directory.glob("*.md")):
            if file.name.upper() == "README.MD":
                continue
            documents.append(read_document(root, kind, folder, archived, file, read_at))
    return CorpusIndex(documents=documents, read_at=read_at)


def in_corpus(root: Path, path: str) -> bool:
    """Whether a changed path is one the board reads: a markdown file directly
    in one of the four folders, or one of the folders themselves appearing or
    going. Anything else under docs/ is noise the watcher does not rescan for."""
    changed = Path(path)
    relative = None
    for base in (root, root.resolve()):
        if changed.is_relative_to(base):
            relative = changed.relative_to(base)
            break
    if relative is None:
        return False
    for _, folder, _ in FOLDERS:
        folder_parts = Path(folder).parts
        if relative.parts == folder_parts:
            return True
        if relative.parent.parts == folder_parts and relative.suffix == ".md":
            return True
    return False


async def watch(root: Path, stop: asyncio.Event) -> AsyncIterator[set[str]]:
    """Yields the set of changed corpus paths each time something in it moves."""

    def wanted(change: Change, path: str) -> bool:
        return in_corpus(root, path)

    async for changes in awatch(
        root / WATCH_ROOT, stop_event=stop, recursive=True, watch_filter=wanted
    ):
        yield {path for _, path in changes}
