# Review — card #54, a new project follows the way we work from its first session, on any machine, and teaches it back

**Plan:** `docs/plans/done/2026-09-05-18-a-new-project-follows-the-way-we-work-on-any-machine-and-teaches-it-back.md`
**Lane:** `card-54-18-a-new-project-follows-the-way`, 2026-09-05, Claude (Fable 5.1; the lane restarted twice mid-card and resumed from its own transcript both times) with Sol (Codex, `codex exec -s read-only`, thread `01a07211-744c-7cd3-a9aa-d0ac744b54d7`) as the different-make reader in four rounds.
**Composition, for card 58's reader:** one Claude lane doing the judgment and the mechanics; one Codex thread, read-only, called four times — a challenge on the table (found the one dangerously generalised rule and a wrong machine-fact), two rounds of a walk of the whole text (moved the lane off its own remedy), and a review pass on the landed text (found two duplications, an over-applied edit, and nine overclaiming register lines). Every Codex output is kept verbatim in the repository.

## What shipped

- **The one text.** `docs/HOW-WE-WORK.md` is the constitution: the head widened from "a way of building software" to "a way of working", opening with the owner's own sentence — *we cherish intent above all else, and we believe in thorough iteration to improve everything* — then the layering rule, a precedence rule in Sol's words, and the capability-fallback sentence. Fourteen sections in three labelled parts — the doctrine (§1–9), Needle's contract for every project (§10–11), Needle's software execution profile (§12–14) — each method section led by the intent it serves and scoped as today's way for software, plus the owner's steering as a section marked as his. Twenty sentences from the global file added; his one edit ("he holds the intent") applied where he named it and, on his reason, in §1. `docs/INTENT.md` carries "what the colleagues are for" at its head.
- **The board's door says whether a machine delivers the doctrine.** `needle add` and its re-read print `entrance: one-text`, `entrance: two-texts <what it resolves to instead>` or `entrance: none`, resolving `~/.claude/CLAUDE.md` and, where `codex` is installed, `~/.codex/AGENTS.md` against the HOW-WE-WORK the running `needle` ships. Recorded on the project row (migration 0011). A finding, never a refusal.
- **A doctrine edit lands on a card.** `hooks/commit-msg` refuses a commit touching HOW-WE-WORK or INTENT that names no card; `needle hook install` arms it by absolute `core.hooksPath` through the runtime's git door; a ratchet reads the bypass.
- **Every rule says what holds it.** `docs/HOW-WE-HOLD-IT.md`, one stance per section in three words and no fourth, debt as a live card and a date, read two ways by a ratchet whose print is the only map: `held 2, traced 9, convention 3; undefended 1, due 2026-09-19`.
- **The machine's card is written, not done.** `~/Work/omarchy-machine/docs/plans/2026-09-05-20-every-agent-on-this-machine-reads-the-one-text.md`, sequenced after this card.
- **The instruments**, kept as the record of how the words moved: the ruled table (`docs/design/2026-09-05-the-two-texts-of-one-doctrine.md`), the walk by two makes (`docs/design/2026-09-05-the-doctrine-walked-as-its-readers-would-read-it.md`), the marked proposal (`docs/design/2026-09-05-how-we-work-as-the-two-makes-recommend-it.md`), and Codex's challenge verbatim (`docs/reviews/2026-09-05-54-the-different-make-challenge-on-the-two-texts.md`).

## The passes

### Pass 1 — the feature against its "done means" (Claude)

**Plan:** `docs/plans/done/2026-09-05-18-a-new-project-follows-the-way-we-work-on-any-machine-and-teaches-it-back.md`

Item by item, evidence as observed, not as intended:

1. **The table.** `uv run python -m tools.doctrine_table`: `60 paragraphs … 75 paragraph rows over 60 paragraphs, 5 extra rows; drop 41; owner preference 5; machine fact 9; missing portable doctrine 20; ✓ every one of the 60 paragraphs is ruled on by a row`. Every row quotes verbatim; proposals change voice only and say so. The question was asked and the turn ended on it; the board showed the card asking. **Finding, recorded as a deviation on the plan, not fixed:** he answered in the conversation, not through the Answer door, because he was in the interactive session; the card's history has the WAITS row and the folds, not an Answer entry. The ruling is quoted at the table's head and in commit `877a9d4`.
2. **One text.** `git diff bd4ff38..644894d -- docs/HOW-WE-WORK.md docs/INTENT.md` touches only rows the table marks as landing there, the walk's sentences, and his edit; every added sentence is quoted in the table or the walk. He read the proposal page and said "the doc reads well … let's run it". Duplication check is pass 2's.
3. **The entrance line.** On this laptop, the re-read printed `entrance: two-texts /home/dennis/Work/omarchy-machine/home/.claude/CLAUDE.md — ~/.claude/CLAUDE.md and ~/.codex/AGENTS.md resolve there, not to /home/dennis/Work/needle/docs/HOW-WE-WORK.md, so sessions here obey a second doctrine.` On a fixture HOME with no `~/.claude`: `entrance: none`. Both injected files pointing at the fixture's doctrine: `entrance: one-text`. Seven tests in `tests/infrastructure/test_entrance.py`. **Finding, fixed in pass 1:** `Path(__file__)` from a lane's worktree named the lane's copy of HOW-WE-WORK, so every lane would have read `two-texts` forever; `project_of` strips the `.claude/worktrees/<lane>` suffix and a test holds it. `tests/ratchets/test_the_board_never_runs.py` passes — the one process this item needed (arming git) went through `runtime/git.py::arm_hooks_path` after the ratchet refused a `subprocess` in `api/`.
4. **The stance lines.** Ruled beside the text (row D). Ratchet live: `held 2, traced 9, convention 3; undefended 1, due 2026-09-19`. Nine fixture refusals, each named in the parametrised test; debt never counted as held. **Deviation, recorded on the plan:** a debt line names the card's corpus path, not `#<n>`, because the ratchet reads the repository and cannot read the store.
5. **The learning path.** The sentence is in §10 (landed `877a9d4`). The hook: rehearsed on a throwaway repository over six cases before arming — refused a cardless doctrine commit, accepted `#54` and `card 54`, let an unrelated commit through, accepted `--no-verify` and the ratchet then named that one commit and no other. Live: `877a9d4` and `644894d` are the two commits the armed hook judged on the one text; it accepted both because each names #54. `test_no_doctrine_edit_bypassed_the_hook` is silent live.
6. **The machine's card.** Exists on the machine's board, committed `b70f3e7`, gate medium, `Sequencing: after Needle #54`, names `doctrine_twins_drift` and `_twin_sentence` as what retires, cites `docs/codex-on-this-machine.md`. This lane wrote that one file into the machine repo and nothing else.

Suite: `uv run pytest -q` green (every dot, exit 0) on the tree before the pass-2 doc fixes; the two doctrine ratchets re-run green after them. `tsc --noEmit` and `vitest run` (66 passed) green at the `bd4ff38` fold; no frontend file changed since. `machine check` reports no doctrine finding — the twin sentence survived the renumbering because it points at §7, which kept its number.

### Pass 2 — the seams and the truth of the text (Sol, reading as a colleague who was not the author)

**Plan:** `docs/plans/done/2026-09-05-18-a-new-project-follows-the-way-we-work-on-any-machine-and-teaches-it-back.md`

Sol read all 337 lines of HOW-WE-WORK, all of HOW-WE-HOLD-IT, INTENT, and the holder implementations the register names. Read-scope line in its own words: *"all 337 lines of HOW-WE-WORK, all 64 lines of HOW-WE-HOLD-IT, all 157 lines of INTENT, plus the named holder implementations and ratchets needed to test the register's claims."*

Findings, all inside the change, all fixed in `644894d`:

- **§11's lead (lines 226–228) restated its own body (230–237); §14's lead (286–288) restated 290–297.** The duplication §3 refuses, introduced by the walk's own remedy. Both leads now carry only the universal claim and the software scope.
- **§1's edit over-applied the owner's reason.** "The person knows what they want, and only they know it" is an epistemic claim and conflicts with intent being written and backbriefed. Sol's wording — *the person alone can settle what they want* — keeps the ruling as authority. **Still the owner's to strike:** he named the steering line; §1 was changed on his reason, not his instruction.
- **Nine `Held by` lines claimed whole sections their mechanisms hold one clause of** — the Start ratchet holds entry, not the decision boundary; `close` holds that a review file exists, not that a review ran in passes; the register ratchet holds that a stance line exists, not that silent boundaries are mechanised (Sol: "circular"). Sol's rule, adopted into the register's own head: *a stance covers the whole section or it is the weaker stance; a mechanism that holds one clause is named for that clause, never stretched over the rest.* The print fell from `held 9` to `held 2, traced 9, convention 3; undefended 1`. That fall is the register doing its job on its first day.

Sol also confirmed: the marketing colleague no longer stops at §12 or §14 ("that is now specialisation, not abandonment"); the Part headings sit correctly; the one numbered cross-reference (§9 → §7) survived; no mark glyph remains; the §7 debt line "names the exact silent failure still lacking a holder and gives a live plan and date."

Not found by anyone and worth stating: the store. Migration 0011 reached the shared store only through the fold and the service restart, never from the lane's own `needle` commands — the slice-51 incident did not recur, because every live check ran against a private `NEEDLE_DB` copy.

### Pass 3 — the re-read after the fixes (Sol)

**Plan:** `docs/plans/done/2026-09-05-18-a-new-project-follows-the-way-we-work-on-any-machine-and-teaches-it-back.md`

Sol re-read the three changed passages of HOW-WE-WORK and all fifteen register entries. The doctrine: *"§1 fixed — states authority, not private knowledge; §11 fixed — no improper duplication; §14 fixed — necessary intent-to-method mapping, not a second rule."* The register: **not yet clean — six lines still exceeded their evidence**, and one carried a factual error:

- **§14 was false.** "The close is one act, delivered and watch and review, or it is refused" — `api/doors.py::close` lets a docs-only lane close without a review; the refusal is for a code lane. Now a trace, with the two clauses `close` actually holds named as such, "for a code lane" explicit.
- **§12's `Held by` stretched fold over the whole section** — isolation and overlap are the board's read, shown, not held. Now a trace; fold named for the one integration clause.
- **§2's convention was not loud** — the person can approve a plan without detecting a method in an intent's clothes. Now a trace naming the walk and the review's boundaries pass, and saying nothing guarantees the detection.
- **§6, §8, §11 claimed a guaranteed reader** ("read by the person") that no mechanism establishes. Now "presented" — the trace exists; the reader is not promised.

Fixed in this lane; the print is now **`held 0, traced 12, convention 2; undefended 1, due 2026-09-19`**. Read plainly: no section of the constitution is held whole by a mechanism today; twelve are traced, two are loud conventions, one is debt with a card and a date. That is the plan's own thesis — *lands with debt and never calls it defence* — arrived at by a reviewer refusing three rounds of my overclaiming. The register's head carries the rule Sol gave: a stance covers the whole section or it is the weaker stance.

### Pass 4 — the re-read of the six changed lines (Sol)

**Plan:** `docs/plans/done/2026-09-05-18-a-new-project-follows-the-way-we-work-on-any-machine-and-teaches-it-back.md`

Five of six clean. **One finding, §14:** "the close is one act with its three parts" was still grammatically universal while `close` permits a docs-only lane without REVIEW. Sol's wording adopted verbatim: *"every close writes DELIVERED and WATCH in one act, and for a code lane that act also requires a review record that exists."* Ratchet re-run: `held 0, traced 12, convention 2; undefended 1, due 2026-09-19`, unchanged — the fix was to the claim, not the count.

### Pass 5 — the clean pass (Sol)

**Plan:** `docs/plans/done/2026-09-05-18-a-new-project-follows-the-way-we-work-on-any-machine-and-teaches-it-back.md`

*"Clean; §14 now claims exactly what its holder enforces."* Read scope, in Sol's words: only §14's revised stance line — the one line pass 4 found. One clean pass after a pass with findings: the floor, met. Five passes in all, two makes, every Codex line kept verbatim in the lane's scratch and quoted here.

## Outside the change — filed, not fixed

- `docs/slice-suggestions/2026-09-05-a-projects-own-file-holds-only-what-is-that-projects.md` — **Kind:** defect, **Fix:** his. Each project's `CLAUDE.md` read against the one text; Hello Revenue first. Found in the walk; the owner asked that both makes do it as a QA step, cold-pickup walks per project.

## Rulings the owner made on this card, as given

- 2026-09-05, on the table: "as it stands" — every row's stance is his, the contested rows (26b/27c, A, E, 56b) resolved to the stance as written.
- 2026-09-05, on the walk: the recommendation as it stands — one document, three parts, on this card.
- 2026-09-05, one edit: *"he holds the market, the customers, the intent" → "he holds the intent."* His reason, verbatim: "I know the market and the customers but often you have better data than me. I know what I want, that's the only thing I'm confident about that only I know."
- 2026-09-05, on what the doctrine is, in his words, now the head's first sentence: "we cherish intent above all else and … we believe in thorough iteration to improve everything."

## Open, and honest

- **The owner's Answer door was not the channel** — he answered in the session. The plan's item 1 claimed the door; the deviation is on the plan.
- **§1's wording** is Sol's and mine on his reason, not his instruction. One word from him strikes it.
- **The debt:** §7 is undefended until plan 16 lands, by 2026-09-19. The ratchet refuses the register the day that date passes.
- **The machine's card 20 is written, not done.** Until it lands, `needle add` says `two-texts` on this laptop, and that is the true state.

## The loops, as WATCH rows

- `WATCH: every registered project's sessions enter through one text — command uv --project /home/dennis/Work/needle run needle add /home/dennis/Work/needle expect one-text by 2026-09-19 every 1d`
- `WATCH: a doctrine edit after this card arrives on a card, never as a tidy — command git -C /home/dennis/Work/needle log --since=2026-09-06 --format=%b -- docs/HOW-WE-WORK.md docs/INTENT.md expect card by 2026-10-05 every 7d`

The second reads empty until the first edit lands, and empty reads as not delivered; that is honest — no learning has returned yet.
