# Plans — the folder is the status

A plan lives here while it is pending or in flight and moves to `done/` when
its work has shipped and is folded into `main`. So `ls docs/plans/*.md` is the
live work and `done/` is the archive. There is no separate status index.

Every plan carries, near the top: `**Status:**`, `**Written:**`,
`**Effort gate:** <low|medium|high|xhigh> — <why>`, and `**Sequencing:**` when
it depends on another plan. Every item in a plan ends with what "done" means
for it, as a behaviour someone can observe.

A plan's title is its card's title, and the owner ranks cards from their
titles alone. So the title says what will be true when the plan is done, in
his words — the outcome, never the mechanism, the area or a term from the
code. "Defects fix themselves", not "A standing ruling lets a defect enter
execution". The test: could he place it against every other card without
opening it? A suggestion's title is held to the same bar, because it becomes
a card the moment it lands (owner ruling 2026-09-04: "I need to be able to
derive from the card title what the intent of the card is").

A plan that carries suggestions names their paths in its head — a
`**Carries:**` line, or the `**Written:**` line as the early plans did. The
board follows the plan from that line (plan 06, item 5): the first cited
suggestion's card becomes the plan's card with its number and history, the
others fold under it, and none of them needs a second card. The session that
writes the plan moves each carried suggestion to `docs/slice-suggestions/done/`
with a `**Carried by:** <plan path>` line under its title, in the same commit;
the board reads the repository and never writes into it.
