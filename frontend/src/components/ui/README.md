# The design system

The only visual language on the board. `tokens.css` holds every colour, radius,
shadow and font as a variable, and the one mapping from a meaning to a colour;
`primitives.css` holds the comp's component rules; `index.tsx` exports one React
component per primitive. A surface outside this folder composes those components
and writes no class name, no style, no colour and no bare form element of its
own — `tests/ratchets/test_one_design_system.py` refuses all four.

## The colour language

Five colours mean five things and nothing else. This table is the rule; it is
signed in `docs/design/2026-09-04-the-colour-language/Colour.dc.html` and held
by `tests/ratchets/test_the_colour_language.py`.

| Meaning | Token | Means | Appears on |
|---|---|---|---|
| `yours` | `--attn` (amber) | only you can act | a lane's question, a verdict to accept, a signal only you can read, Decision moment's cards |
| `broken` | `--wrong` (red) | evidence is gone, or two things disagree | a doubted status, a document nowhere, a lane that died, two running lanes in one file |
| `live` | `--accent` (teal) | happening right now | a lane with hands on, a conversation, a signal being read, a card in flight |
| `proven` | `--landed` (green) | the loop closed | a signal read as delivered, Done, a free card's Start, the trunk level |
| `quiet` | `--ink-2` (grey) | information with no claim on you | counts, ages, gates, kinds, what arrived, what is unplanned, a collision before Start |

**Never**: a count coloured for its size; a category coloured for its kind; a
button coloured; a column coloured.

**How to paint.** A surface says what it means with `data-meaning="…"` and
paints with `var(--meaning)` (or `var(--meaning-2)` for the tint behind it).
Those two variables are set in exactly one place — the `[data-meaning]` block
in `tokens.css` — and nothing else in the frontend may name `--attn`,
`--wrong`, `--accent` or `--landed`. So a page that wants amber has to claim,
in its own markup, that only the owner can act; the page test reads those
claims back against the board's own state table.

**A card's meaning comes from the board, never from the page.** `CardState`
(`domain/board.py`, named by `board.assemble.state_of`) carries the word, its
meaning, the one door the state allows and the loop glyph. The page renders
what it is given and invents no word.

**A door is a shape, never a colour**: the primary door is filled (`.btn`), the
rest are outlined (`.btn.ghost`), and a door that cannot open is one grey line
saying when it will. Nothing you can press is ever confused with something that
is happening.

Tailwind is imported for its reset and for the token theme (`@theme` in
`tokens.css`, with the default palette wiped), so a later primitive may use a
token utility such as `bg-surface-2`; the comp's rules were carried over as
CSS because that is the form the owner signed.
