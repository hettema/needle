"""A subscription's allowances as `claude-acct` last read them, for the end
of a park (plan 68, item 3).

`claude-acct cache` writes `<cache>/<slot>.json` on every read the statusline
makes: the share spent of each allowance under its own label, and since
2026-09-04 when each comes back (`resets`). A lane parked on a wall ends its
park at the reset of the allowance that is gone — the board reads the number
the machine already has rather than parsing the limit message for a time,
which plan 02's ruling 1 forbids.
"""

import json
from datetime import UTC, datetime

from domain.slot import Limits
from runtime import machine


def _when(value: object) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), UTC)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value).astimezone(UTC)
        except ValueError:
            return None
    return None


def snapshot(slot: str) -> Limits | None:
    """The slot's last reading, or None when there is none to read."""
    path = machine.acct_cache_dir() / f"{slot}.json"
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(blob, dict):
        return None
    fetched = _when(blob.get("fetchedAt"))
    if fetched is None:
        return None
    spent: dict[str, float] = {}
    for label, share in (blob.get("limits") or {}).items():
        if isinstance(label, str) and isinstance(share, int | float):
            spent[label] = float(share)
    resets: dict[str, datetime] = {}
    for label, stamp in (blob.get("resets") or {}).items():
        when = _when(stamp)
        if isinstance(label, str) and when is not None:
            resets[label] = when
    return Limits(slot=slot, fetched_at=fetched, spent=spent, resets=resets)


def next_reset(limits: Limits) -> tuple[str, datetime] | None:
    """The soonest return of an allowance that is gone: its label and time.
    None when the reading shows nothing spent, or nothing spent says when
    it comes back — then the park has no clock and waits on the rule."""
    gone = [
        (when, label)
        for label, share in limits.spent.items()
        if share >= 1.0 and (when := limits.resets.get(label)) is not None
    ]
    if not gone:
        return None
    when, label = min(gone)
    return label, when
