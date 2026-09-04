"""The roles this machine names (plan 12, item 2).

`~/.claude-accounts/roles.json` is the machine's one place where a role is
named and the model it runs on today is set (`~/Work/omarchy-machine`, its
card 12): every key that is not a note (`_comment`, `_history`) is a role.
The board reads the names and nothing else — which model a role runs on is
the machine's business, and a plan names roles, never models.
"""

import json

from runtime import machine


def roles() -> list[str] | None:
    """The role names in file order; None when the machine has no roles
    file, so a plan's roles cannot be checked and the board says so rather
    than inventing a vocabulary."""
    path = machine.roles_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        blob = json.loads(text)
    except ValueError:
        return None
    if not isinstance(blob, dict):
        return None
    return [key for key in blob if isinstance(key, str) and not key.startswith("_")]
