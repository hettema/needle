# Plans — the folder is the status

A plan lives here while it is pending or in flight and moves to `done/` when
its work has shipped and is folded into `main`. So `ls docs/plans/*.md` is the
live work and `done/` is the archive. There is no separate status index.

Every plan carries, near the top: `**Status:**`, `**Written:**`,
`**Effort gate:** <low|medium|high|xhigh> — <why>`, and `**Sequencing:**` when
it depends on another plan. Every item in a plan ends with what "done" means
for it, as a behaviour someone can observe.
