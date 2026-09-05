# The strongest model with headroom drives the card, whatever its make

**Carries:** docs/slice-suggestions/2026-09-05-every-rung-is-a-claude-one-so-sol-can-be-asked-but-never-given-the-wheel.md
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation a4386ba3)
**Status:** PENDING
**Written:** 2026-09-05, from Dennis: "most of our claude accounts are out of fable credits, only one left. But we have a lot of headroom with codex sol. When fable runs out, can Sol be selected as the driver of a card instead of opus? And can we make it so that if other fable/sol level models pop up, we can let them drive cards?" — and, told that #63 waited on two rulings: "it's not just about metering, it's also about having the strongest model steer. Opus is not as strong as fable or sol I'd say."
**Effort gate:** high — the launch, the scope and the fold are transcriptions of what a Claude lane already does and what a called Codex worker already gets; the judgment is in what the board honestly shows for a make that has no wall, no rung-walk and no fork, and in keeping the tier a dated ruling the evidence can move rather than a fact the code asserts.
**Sequencing:** none as a hold. #58 (the composition router) can only assign a hand the runtime can execute, so this card is its prerequisite, not its dependant. The machine's half — one rule ranking tiers across makes and reading Codex's headroom — is a card on the Omarchy board written after item 1 here ships, because a rule that names a rung nothing can execute is a rule that lies (#63).

## Intent

A card is driven by the strongest model that has headroom, whatever make it belongs to. When every Fable allowance is spent, the board hands the wheel to Sol before it hands it to Opus, and the board sees, steers and closes that lane as it does a Claude one. A new top-tier model, of either make or of a third, becomes a rung by a row of data and a launcher for its make, never by a code change to the runtime's idea of a model.

## The two rulings

#63 was marked `his` on two questions. Both were answered in the door on 2026-09-05, and this plan is what they authorise.

1. **A make the board cannot instrument the way it instruments Claude may hold a card's wheel.** Ruled yes. The alternative — Sol asked but never driving — was rejected because it makes every card an Opus card the moment Fable is spent, and four accounts of five are spent as this is written (`claude-acct status`, 2026-09-05: gmail, hrme, hrclaude and armana at 100 % Fable used; eduard at 1 %).
2. **A rung that spends no Claude allowance may outrank Opus.** Ruled yes, and for a reason that is not the meter: the ladder is a quality tier. In the owner's words, Opus is not as strong as Fable or Sol. So the ladder reads: every top-tier rung with headroom, of any make, before any Opus rung. The alternative — a ladder ranked by allowance, which is what #63 had argued Sol would buy — was rejected because it hands a card to the weaker model while a stronger one sits idle on another subscription.

What the rulings do not do: they do not settle where Sol sits *within* the top tier against Fable, and they do not overrule #58 or the machine's plan 12, both of which hold that a routing preference is earned by evidence. The reconciliation is item 4: the tier is written as the owner's ruling with its date, the evidence readers may move it by a dated edit, and nothing here is a permanent make-to-role assignment.

## What is already true

- A Codex worker can be resumed by the runtime, put in a card's scope, verified alive and judged (`runtime/launch.py::call_codex`, plan 57). It has never held a worktree, a branch or a card.
- Codex 0.152.1 fires `SessionStart`, `SessionEnd`, `Stop`, `UserPromptSubmit`, `PreToolUse` and `PostToolUse` (the machine's plan 22, checked against the binary). The board reads `SessionStart`, `Stop`, `SessionEnd`, `StopFailure` and `PostToolUse` (`hooks/needle_hook.py`). Every event the board needs to see a lane born, working and ended exists on the Codex side; only `StopFailure` — the wall — does not, and a Codex lane has no wall to report.
- `codex exec` takes `-C <dir>`, `-s <sandbox>`, `-m <model>`, `--json`, `-o <file>` and `resume <id>`. Its default sandbox is read-only; `workspace-write` confines writes to the working directory and, unless `[sandbox_workspace_write]` says otherwise, cuts the network.
- A Claude lane is one argv (`runtime/launch.py::argv_for`), one scope per card (`scope_session`, which adopts by pid and cares nothing for the make), one walk down the ladder (`_walk`). `domain/slot.py::Model` is `fable | opus`, and the board guesses `fable` for a row with no model (`board/lane.py:128`, `:174`).
- Codex trusts a hook by its hash and runs project-level hooks only in a trusted repository root; a lane's worktree is a new path every time, so a Codex lane's hook can only be the global one (`~/.codex/hooks.json`; the machine's `docs/codex-on-this-machine.md` has the six traces).

## Items

### 1. A Codex lane: started from the card, working in its worktree, seen by the board

Start launches `codex exec` in the card's worktree at the plan's effort, in `needle-<card>.scope`, with the brief a Claude lane gets, and records the row the way a called worker is recorded. The board's hook fires from Codex's global hook file for every event the board reads, gated on the session's cwd being a lane the board knows, so the machine's `SessionStart` line and the board's stand side by side in one file. Two facts are proved on a throwaway worktree before the argv is fixed, and their answer goes in the machine's Codex doc: whether `workspace-write` lets a lane commit when the worktree's `.git` is a file pointing into the main checkout's `.git/worktrees/` (`writable_roots` is the door if not), and what a Codex hook payload carries — `session_id`, `cwd`, a transcript path — against what `hooks/needle_hook.py` keeps. Done means: `needle start` on a throwaway card with the rule answering `codex` puts a Codex row in the one list with the card's name, worktree and scope; the row's Stop lands on the board through the hook; the lane's first commit exists in its worktree and nowhere else; a launch that fails is `DEAD` with the log's last line and leaves no row.

Hands out: execution — the throwaway sandbox probe (a commit inside a worktree under `workspace-write`, with and without `writable_roots`) and the hook payload capture, run by script and reported verbatim; verifies by reading the worktree's `git log` and the captured payload before the argv is written.

### 2. A Codex lane folds through the same door, and red never lands

The fold is the runtime's, not the lane's: `needle fold` from the lane's worktree runs the suite and pushes fast-forward to `origin/develop`, so the lane needs no network inside its sandbox and no push of its own. Claude Code's worktree guard has no counterpart in Codex; what holds the boundary for a Codex lane is the sandbox's workspace root — the worktree — and the fold's own refusal of anything that is not a fast-forward. Done means: a Codex lane on a throwaway card folds green through `needle fold`; a `git` command aimed at the main checkout from inside the lane's sandbox is refused by the sandbox, proved in item 1's probe and recorded in the machine's doc; a red suite leaves the branch unpushed with the failure named on the card.

### 3. The board shows a Codex lane as what it is

A Codex row's rung reads as its make and the model the rollout names, and nothing else: no wall, no fork, no rung-walk, because the make has none (plan 57's ruling stands). The board stops guessing `fable` for a row with no model; a row with no model says so. Stop and Move on a Codex lane say the true thing: Stop ends the process through its scope; Move is closed with the reason that a Codex lane has no other slot until the machine's rule names one. The Start door's preview says which make and model will drive and why, in the rule's words. Done means: a fixture Codex lane renders its make and model on the card and in the one list; the two `fable` guesses are gone and a test refuses a row with no model reading as any model; the Start preview names the make when the rule answers `codex`.

### 4. The ladder is data with a tier per rung, and the runtime launches any rung it names

A rung is a make, a model and a tier, and the tier is the owner's dated ruling — today: Claude's Fable and Codex's top model in the top tier, Claude's Opus below — held in the machine's slot data beside the accounts, never in a Needle enum. The runtime accepts whatever rung the rule names, chooses the argv by the make, and refuses a make it cannot launch by that make's name. Adding a new top-tier model of either make, or a third make, is a row in that data and a launcher for its make, never a change to `Model`. #58's reader and the machine's plan 12 baseline may move a rung's tier; a move is a dated edit of the ruling, visible on the Start preview, and never an automatic one (a routing change with no baseline cannot be evaluated — the machine's plan 12, item 7). Done means: `domain/slot.py::Model` no longer enumerates Claude's model names; a fixture rule answer naming `codex` with a model launches through item 1's argv and one naming an unknown make is refused with that name in the reason; the tier and its ruling date read on the Start preview; the machine-side card that makes `claude-acct best`, or its successor, answer across makes is filed on the Omarchy board with this plan as its evidence.

## Loop

We think a top-tier Codex lane will hold the quality a Fable lane holds while Opus-hours under a spent Fable allowance fall toward zero, because the owner's ruling says the tier is quality and #51, #54 and #57 showed Sol's corrections landing on real work. The read is #58's, on the first six Codex-driven cards against the six Fable-driven cards nearest them in work shape: corrections before build, review-ring findings, defects filed against the card within fourteen days. If the Codex arm escapes more defects, the tier ruling comes back to Dennis with those tallies and the rung drops a tier by a dated edit. If the arm holds and Opus-hours fall, the ruling stands as a fact and the machine-side card has its evidence. If Starts begin dying for want of any rung, that is a different failure — the board stopping — and the machine-side card goes first.

Loop: the first six Codex-driven cards against their nearest Fable-driven neighbours — session read the review records and the suggestions filed against those twelve cards, in docs/reviews/ and docs/slice-suggestions/, and #58's reading of them where it exists, by 2026-09-26

## Deliberately not

- Inventing wall, fork or slot-move parity for a make that has none.
- A provider adapter before a third make shows the repeated boundary (plan 57's ruling).
- Writing the cross-make rule here; it is the machine's, and it follows item 1.
- Deciding where Sol sits against Fable inside the top tier; #58 earns that.
- Automatic composition; #58 assigns hands, this card makes a Codex hand executable.

## Terrain

- `runtime/launch.py` — `argv_for`, `_walk`, `scope_session`, `call_codex`, `CODEX_RUNG`
- `runtime/codex.py` — the rollout reader, `resume_argv`, `SLOT`, `WORKER_SOURCES`
- `runtime/rule.py`, `domain/slot.py` — `Model`, `Rung`, `Placement`, `Where`
- `hooks/needle_hook.py`, `needle hook install`, `api/app.py` (`/api/hooks`)
- `board/lane.py:128`, `:174` — the `fable` guess
- `~/.codex/hooks.json`, `~/.codex/config.toml` (`[sandbox_workspace_write]`, `[hooks.state]`), `~/.claude-accounts/accounts.json`
- the machine: `docs/codex-on-this-machine.md`, `docs/plans/2026-09-05-22-codex-switches-accounts-like-claude.md`, `docs/plans/done/2026-09-04-12-smart-with-tokens-never-with-quality.md` (item 7)
- `docs/plans/2026-09-05-the-team-learns-which-composition-earns-its-place.md` (item 1)

## Close-out

Written by the lane: a stance per item; the two probe facts and where they were recorded; the first Codex lane's card number and its fold; the machine-side card's path; the loop's row as the close wrote it and its first reading date.
