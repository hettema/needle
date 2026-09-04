# The design system

The only visual language on the board. `tokens.css` holds every colour, radius,
shadow and font as a variable, copied once from the signed comp; `primitives.css`
holds the comp's component rules; `index.tsx` exports one React component per
primitive. A surface outside this folder composes those components and writes
no class name, no style, no colour and no bare form element of its own —
`tests/ratchets/test_one_design_system.py` refuses all four.

Tailwind is imported for its reset and for the token theme (`@theme` in
`tokens.css`, with the default palette wiped), so a later primitive may use a
token utility such as `bg-surface-2`; the comp's rules were carried over as
CSS because that is the form the owner signed.
