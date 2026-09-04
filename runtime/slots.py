"""The declared slots, and the registries the runtime reads.

`accounts.json` under the slot root declares each slot and the identity it
should hold; that file is `claude-acct`'s and the runtime only reads it. The
default config directory (`~/.claude`) is a registry too: a session started
with no `CLAUDE_CONFIG_DIR` registers there, so the one list reads it as
well and attributes its rows to the slot whose declared identity it holds.
"""

import json
from pathlib import Path

from domain.slot import Slot
from runtime import machine

DEFAULT_SLOT = "default"
"""The name given to the default config directory's rows when no declared
slot holds the identity signed in there."""


def _accounts() -> dict[str, dict[str, object]]:
    try:
        blob = json.loads((machine.slot_root() / "accounts.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(blob, dict):
        return {}
    return {k: v for k, v in blob.items() if not k.startswith("_") and isinstance(v, dict)}


def identity(config_dir: Path) -> str | None:
    """Who a config directory is signed in as, from its own `.claude.json`."""
    try:
        blob = json.loads((config_dir / ".claude.json").read_text(encoding="utf-8"))
        email = (blob.get("oauthAccount") or {}).get("emailAddress")
    except (OSError, json.JSONDecodeError, ValueError, AttributeError):
        return None
    return str(email) if email else None


def declared() -> list[Slot]:
    root = machine.slot_root()
    return [Slot(name=name, config_dir=str(root / name)) for name in _accounts()]


def slot_named(name: str) -> Slot | None:
    return next((s for s in declared() if s.name == name), None)


def registries() -> list[Slot]:
    """Every directory whose registry the one list reads: each declared slot,
    then the default directory under the name of the slot holding its identity."""
    slots = declared()
    home = machine.claude_home()
    if not home.is_dir() or any(Path(s.config_dir).resolve() == home.resolve() for s in slots):
        return slots
    who = identity(home)
    name = DEFAULT_SLOT
    if who:
        for slot_name, row in _accounts().items():
            expected = row.get("email")
            if isinstance(expected, str) and expected.lower() == who.lower():
                name = slot_name
                break
    return [*slots, Slot(name=name, config_dir=str(home))]
