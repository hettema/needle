# Plans — the folder is the status

A plan lives here while it is pending or in flight and moves to `done/` when
its work has shipped and is folded into `main`. So `ls docs/plans/*.md` is the
live work and `done/` is the archive. There is no separate status index.

Every plan carries, near the top: `**Status:**`, `**Written:**`,
`**Effort gate:** <low|medium|high|xhigh> — <why>`, and `**Sequencing:**` when
it depends on another plan. Every item in a plan ends with what "done" means
for it, as a behaviour someone can observe.

**And an item that hands work out says so.** An item whose work goes to a
role ends with a `Hands out:` sentence: `Hands out: <role> — <what it hands
out>; verifies <what the executing session checks before acting on the
result>`. The roles are the machine's (`search`, `execution` — the names in
`~/.claude-accounts/roles.json`), never model names. An item that is
judgment says nothing, and that silence means Fable. Why: verbose work in a
subagent's own context is the cheapest token on the machine, and a
subagent's result is a claim, so the plan is where "hand it out, then check
this" is decided rather than remembered. The board reads the sentence onto
the card per item, says on the card when a role named is not one the
machine has, and at the lane's close writes what the plan named against
what the lane dispatched (plan 12). This file is the source of the line:
the machine's `docs/plans/README.md` carries a copy that cites it, and
Hello Revenue's `hr-plan-write` does the same on its own card.

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
