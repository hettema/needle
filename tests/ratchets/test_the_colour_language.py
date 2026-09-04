"""Five colours mean five things and nothing else (plan 27).

The rule is not "use the tokens" — the tokens were always there, and the board
still ended up with a count coloured for its size, a category coloured for its
kind, buttons in accent and a whole column in amber. The rule is that a
surface must *say which of the five things it is saying* before it can be
painted at all.

So there is exactly one place where a meaning meets a colour: the
`[data-meaning=...]` block in `tokens.css`, which sets `--meaning`. Every
other rule in the frontend paints with `var(--meaning)` and cannot reach a
meaning token directly. A page that wants amber has to claim, in its markup,
that only the owner can act — and the page test reads those claims back.

This ratchet holds the intent, not the method: any better way of painting is
free to arrive, as long as it still has to name its meaning first.
"""

import re

from tests.ratchets.paths import FRONTEND_SRC, UI, frontend_files

TOKENS = UI / "tokens.css"

MEANING_TOKENS = re.compile(r"--(?:attn|wrong|accent|landed)\b")
"""The four tokens that carry a meaning. Grey needs no guard: it is what a
surface looks like when it says nothing."""

MEANING_RULE = re.compile(r'^\[data-meaning="(?P<meaning>[a-z]+)"\]\s*\{(?P<body>[^}]*)\}', re.M)

MEANINGS = {
    "yours": "attn",
    "broken": "wrong",
    "live": "accent",
    "proven": "landed",
    "quiet": "ink-2",
}
"""The language, as `docs/design/2026-09-04-the-colour-language/Colour.dc.html`
signs it and `components/ui/README.md` writes it down."""


def _mapping() -> dict[str, str]:
    text = TOKENS.read_text(encoding="utf-8")
    return {m["meaning"]: m["body"] for m in MEANING_RULE.finditer(text)}


def test_every_meaning_has_one_colour_and_one_only():
    mapping = _mapping()
    assert set(mapping) == set(MEANINGS), (
        f"the colour language names {sorted(MEANINGS)}; tokens.css maps {sorted(mapping)}"
    )
    for meaning, token in MEANINGS.items():
        body = mapping[meaning]
        assert f"--meaning: var(--{token})" in body, (
            f'"{meaning}" must be var(--{token}); tokens.css says: {body.strip()}'
        )


def test_nothing_but_that_mapping_may_name_a_meaning_token():
    """A count is not amber for being large, a category is not a hue, a button
    is not a colour and a column is not a state — because none of them can
    reach one without saying which of the five things it means."""
    offenders: list[str] = []
    for path in frontend_files():
        text = path.read_text(encoding="utf-8")
        if path == TOKENS:
            # In the tokens file the four are defined, themed for Tailwind and
            # mapped; only the mapping may hand them to a surface.
            for number, line in enumerate(text.splitlines(), 1):
                handed_over = (
                    MEANING_TOKENS.search(line)
                    and "--meaning" in line
                    and "data-meaning" not in line
                    and not line.lstrip().startswith("--meaning")
                )
                if handed_over:
                    offenders.append(f"tokens.css:{number}: {line.strip()}")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if MEANING_TOKENS.search(line):
                offenders.append(f"{path.relative_to(FRONTEND_SRC)}:{number}: {line.strip()}")
    assert not offenders, (
        "a meaning's colour was reached without naming the meaning; paint with "
        "var(--meaning) and say what it means with data-meaning:\n" + "\n".join(offenders)
    )


def test_the_readme_carries_the_table():
    """The rule is written down where the next session will look for it."""
    readme = (UI / "README.md").read_text(encoding="utf-8")
    for meaning, token in MEANINGS.items():
        assert re.search(rf"\|\s*`{meaning}`\s*\|", readme), f"the README's table omits {meaning}"
        assert f"--{token}" in readme, f"the README's table omits {meaning}'s token"
