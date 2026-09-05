# My own second reading, made before Codex answered

Recorded before the challenge lands so the reconciliation can tell my own
corrections apart from Codex's. The three rows I named to Codex as the ones
where my split rule was closest to arbitrary, re-read against HOW-WE-WORK's
actual text:

## 39 — keep `drop`

Global: "A step that leaves no evidence cannot be measured later, and the steps
most likely to be skipped are exactly the ones that leave nothing behind."
§7 carries the rule ("If a step leaves no trace, the loop begins by creating
one"). The second sentence says *why* the rule matters and tells a session
nothing new to do. Gloss. Unchanged.

## 45 — keep `drop`

Global: "It surfaces by hitting a wall, long after the cheap moment to fix it.
That is what makes it worse than waste."
Same shape as 39: the cost of the thing §6 already forbids. Gloss. Unchanged.

## 49 — CHANGED, split into 49a / 49b

Global: "A boundary that depends on someone remembering it will erode. When an
invariant matters, mechanize it — a hook, a permission, a database grant, a
test, a default that makes the wrong thing impossible. **This is not a software
rule; it applies to the machine, the config, and the way we work.**"

I marked the whole paragraph `drop` on the reasoning that §5's placement in a
document about the way of working makes the scope. That was weaker than it
looked. The sentence is not a gloss on the rule — it *extends the rule's
domain*, and it does so to exactly the domains where the failure is silent: a
permission, a config default, a working convention. §5 as published lists "a
test, a refusal at a door, a default" and never says the rule reaches past code,
so a session reading only HOW-WE-WORK can consistently mechanise its tests and
leave a config boundary to convention.

It also passes Codex's own portability test from the prerequisite note §4 —
would the sentence be true on a second laptop with the same owner? Yes; "the
machine" and "the config" are categories, not this laptop.

- **49a · drop** — "A boundary that depends on someone remembering it will
  erode. When an invariant matters, mechanize it…" (§5, near-verbatim)
- **49b · missing portable doctrine** — "This is not a software rule; it applies
  to the machine, the config, and the way we work."

Effect on the counts if applied: drop 41 → 41 (49 becomes 49a), missing 18 → 19,
rows 72 → 73.
