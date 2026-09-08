# The strongest model with room to run drives the card, Claude or Codex

**Carries:** docs/slice-suggestions/2026-09-05-every-rung-is-a-claude-one-so-sol-can-be-asked-but-never-given-the-wheel.md
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation a4386ba3)
**Status:** SHIPPED
**Written:** 2026-09-05, from Dennis: "most of our claude accounts are out of fable credits, only one left. But we have a lot of headroom with codex sol. When fable runs out, can Sol be selected as the driver of a card instead of opus? And can we make it so that if other fable/sol level models pop up, we can let them drive cards?" — and, told that #63 waited on two rulings: "it's not just about metering, it's also about having the strongest model steer. Opus is not as strong as fable or sol I'd say."
**Effort gate:** high — the launch, the scope and the fold are transcriptions of what a Claude lane already does and what a called Codex worker already gets; the judgment is in what the board honestly shows for a make that has no wall, no rung-walk and no fork, and in keeping the tier a dated ruling the evidence can move rather than a fact the code asserts.
**Sequencing:** none as a hold. #58 (the composition router) can only assign a hand the runtime can execute, so this card is its prerequisite, not its dependant. The machine's half — one rule ranking tiers across makes and reading Codex's headroom — is a card on the Omarchy board written after item 1 here ships, because a rule that names a rung nothing can execute is a rule that lies (#63).
**Formerly:** The strongest model with headroom drives the card, whatever its make (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)

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

**Met:** `needle start` on a card whose rule answers `codex` lays the lane's worktree, launches `codex exec` in it at the plan's effort, verifies the process past an observation window, puts it in `needle-<card>.scope` and records the row (`runtime/launch.py::codex_lane`, `runtime/codex.py::lane_argv`, `runtime/git.py::add_worktree`; `tests/runtime/test_codex_lane.py`, five cases). A launch that dies is `DEAD` with the log's last line and takes its worktree back, so the card is left as it was found. The row's events land on the board through the hook: a real `codex exec` in this lane's worktree on 2026-09-08 at 11:53Z put `SessionStart`, `Stop` (carrying the session's last message) and `SessionEnd` in the live board's `hook_events`, each attributed to project `needle` and card 63 — the machine's `etc/codex/requirements.toml` now declares the board's four events beside the health line and the re-anchor. Both probe facts are answered and are in the machine's `docs/codex-on-this-machine.md` ("What the sandbox allows a lane" and "What a hook payload carries").

### 2. A Codex lane folds through the same door, and red never lands

The fold is the runtime's, not the lane's: `needle fold` from the lane's worktree runs the suite and pushes fast-forward to `origin/develop`, so the lane needs no network inside its sandbox and no push of its own. Claude Code's worktree guard has no counterpart in Codex; what holds the boundary for a Codex lane is the sandbox's workspace root — the worktree — and the fold's own refusal of anything that is not a fast-forward. Done means: a Codex lane on a throwaway card folds green through `needle fold`; a `git` command aimed at the main checkout from inside the lane's sandbox is refused by the sandbox, proved in item 1's probe and recorded in the machine's doc; a red suite leaves the branch unpushed with the failure named on the card.

**Deviated:** the intent holds and the method changed, with the evidence. The plan said the lane would have no network and the runtime would fold for it. Probing the real sandbox on 2026-09-08 showed the boundary is not where the plan expected: Codex's workspace sandbox denies every write under `.git` **by rule**, in a plain repository as much as in a worktree, so `-s workspace-write` alone cannot commit at all — and with the four writable roots that let it commit (`.git/worktrees/<lane>`, `.git/objects`, `.git/refs`, `.git/logs`) the main checkout's index and working tree stay refused by the kernel. Given a lane that can commit, the shortest way to "folds through the same door" is the same door: with `network_access` on it runs its own suite and its own `uv run needle fold`, exactly as a Claude lane does, and `needle fold` needs no second shape for a second make (one way to do each thing, §3). All four capabilities were verified inside the real sandbox on 2026-09-08: `git push` to a remote, `uv --project … run needle` exit 0, the board on 127.0.0.1:8480 answering 200, and both escapes refused. What the plan asked for and did not get: a fold that runs the suite. `needle fold` does not run one and did not before; a lane runs its suite and then folds, which is what a Codex lane now does too. Making the fold run the suite for every lane is a change to every lane's fold, not to this card's make question — filed as `docs/slice-suggestions/2026-09-08-work-cannot-land-on-the-shared-branch-without-its-tests-having-passed.md`.

### 3. The board shows a Codex lane as what it is

A Codex row's rung reads as its make and the model the rollout names, and nothing else: no wall, no fork, no rung-walk, because the make has none (plan 57's ruling stands). The board stops guessing `fable` for a row with no model; a row with no model says so. Stop and Move on a Codex lane say the true thing: Stop ends the process through its scope; Move is closed with the reason that a Codex lane has no other slot until the machine's rule names one. The Start door's preview says which make and model will drive and why, in the rule's words. Done means: a fixture Codex lane renders its make and model on the card and in the one list; the two `fable` guesses are gone and a test refuses a row with no model reading as any model; the Start preview names the make when the rule answers `codex`.

**Met:** a Codex row reads as its make and the model its rollout names — `runtime/codex.py::_model_of` reads the model from the rollout's head (`base_instructions.provenance.model`, read from a 0.153.4 rollout on 2026-09-08) and answers None when a version writes it elsewhere. The three `fable` guesses are gone (`board/lane.py` twice, `api/loops.py`, and the page's `model ?? "fable"`), replaced by one builder on each side — `domain.slot.rung_words` and `frontend/src/board/rung.ts` — and `tests/ratchets/test_the_board_never_names_a_model_it_was_not_told.py` refuses a Claude model name written anywhere in the runtime, the board or the page; it was run against the old code and fails on it. The Start preview names the make when the rule answers one (`board/lane.py::driver`; `tests/board/test_who_drives.py`). Stop and Move already said the true thing for a Codex row (plan 57) and still do.

### 4. The ladder is data with a tier per rung, and the runtime launches any rung it names

A rung is a make, a model and a tier, and the tier is the owner's dated ruling — today: Claude's Fable and Codex's top model in the top tier, Claude's Opus below — held in the machine's slot data beside the accounts, never in a Needle enum. The runtime accepts whatever rung the rule names, chooses the argv by the make, and refuses a make it cannot launch by that make's name. Adding a new top-tier model of either make, or a third make, is a row in that data and a launcher for its make, never a change to `Model`. #58's reader and the machine's plan 12 baseline may move a rung's tier; a move is a dated edit of the ruling, visible on the Start preview, and never an automatic one (a routing change with no baseline cannot be evaluated — the machine's plan 12, item 7). Done means: `domain/slot.py::Model` no longer enumerates Claude's model names; a fixture rule answer naming `codex` with a model launches through item 1's argv and one naming an unknown make is refused with that name in the reason; the tier and its ruling date read on the Start preview; the machine-side card that makes `claude-acct best`, or its successor, answer across makes is filed on the Omarchy board with this plan as its evidence.

**Met, with the machine's half named:** `domain/slot.py::Model` is gone — a rung's model is the word the rule answered, kept as given. `Make` is what remains code, and deliberately: a make needs a launcher, so the makes this runtime *can* run are code and a make it may be *told about* is not; a rule naming `mistral` is refused with that word and the makes it can launch (`runtime/rule.py`; `tests/runtime/test_rule.py`). The tier is read from the rule's answer as the owner's dated ruling and shown on the Start door with its date (`board/lane.py::why_this_driver`); a half-named tier is no tier. What is not live: `claude-acct best` does not yet answer `make`, `tier` or `tier_ruled_on`, so today every Start preview reads a Claude rung with no tier, exactly as it did — the fixture rule answers drive both paths in the tests. That half is the machine's card, filed as this plan's Sequencing said it would be, with this plan as its evidence: `/home/dennis/Work/omarchy-machine/docs/slice-suggestions/2026-09-08-the-strongest-colleague-with-room-to-work-takes-the-next-card-whichever-kind-it-is.md`. One visible consequence today: the rule answers `model: null` for a slot's top rung and the runtime used to turn that into the word `fable`; it now passes no `--model` and the board says the slot alone, with the rule's own reason ("Fable headroom on eduard …") beside it. The word comes back to the label when the machine's card makes the answer name the model.

## Measurement correction agreed on 2026-09-08

Dennis accepted the allowance audit and asked: "do you need to update 63 so it knows to fix the measurement thing?" The correction belongs to the machine's existing reader, so its execution is machine **#47**, written in `/home/dennis/Work/omarchy-machine/docs/plans/2026-09-08-token-use-is-counted-once-and-savings-need-proof.md`. Read and coordinate that work alongside this card; the cross-make chooser in item 4 is a different machine responsibility and does not carry the measurement correction implicitly.

The source search found machine #12 and `machine burn`, not a need for a new meter. The audit verified that copied histories inflate consumption and that #12's `expect walls` signal accepts both zero and 999 walls. The linked machine plan owns request deduplication, explicit uncertainty for conflicting copies or historical account attribution, and correction of #12's false success condition. This card's runtime work can start before that correction ships; any efficiency conclusion below must wait for its verified result. Preserve the first Codex-driven cards' existing traces so waiting on the reader cannot erase their observations.

The close must identify the linked machine card and its actual state. If the correction or a comparable quality baseline remains missing, the comparison says insufficient evidence and stays open; shipping a working Codex driver is not proof of savings or unchanged quality. #58 still follows #63 and owns automatic collaboration, including who challenges the accountable driver.

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

Written by the lane: a stance per item; the two probe facts and where they were recorded; the first Codex lane's card number and its fold; the machine-side card's path; the loop's row as the close wrote it and its first reading date; the linked measurement card and whether its correction was verified or the efficiency comparison remains open.

### What the close wrote

- **A stance per item:** above, on each of the four.
- **The two probe facts, and where:** the sandbox and the hook payload, both
  probed on 0.153.4 on 2026-09-08 and written up in
  `/home/dennis/Work/omarchy-machine/docs/codex-on-this-machine.md` under
  "What a session of this make may do with a card". The first contradicted
  this plan's own premise: the sandbox denies `.git` writes by rule, not
  because a linked worktree's `.git` points elsewhere.
- **The first Codex lane, and its fold:** none on a real card yet, and the
  reason is item 4's — `claude-acct best` cannot answer `codex`, so no Start
  will choose it until the machine's card lands. What did run, end to end on
  2026-09-08, is a lane on a throwaway card with the rule stubbed to answer
  `codex`: alive in 8.3 s, in its own worktree, in its own space on the
  machine, and it committed its own work (`a3bbff1`) while its reach into the
  main copy came back `Read-only file system`. Pass 5 of
  `docs/reviews/2026-09-08-the-strongest-model-with-room-to-run-drives-the-card.md`
  has it.
- **The machine-side card:**
  `/home/dennis/Work/omarchy-machine/docs/slice-suggestions/2026-09-08-the-strongest-colleague-with-room-to-work-takes-the-next-card-whichever-kind-it-is.md`,
  filed with this plan as its evidence and naming the three fields the rule's
  answer needs.
- **The loop's row and its first reading:** the WATCH this close wrote is the
  owner's reading of the first six Codex-driven cards against their nearest
  Fable-driven neighbours, by 2026-09-26. It cannot read earlier than the
  machine's card, because until then there are no Codex-driven cards to read.
- **The linked measurement card, and whether its correction was verified:**
  machine **#47**, `docs/plans/done/2026-09-08-token-use-is-counted-once-and-savings-need-proof.md`,
  is **Done and its correction verified** — both items carry a `Met:` with
  evidence: `count_once()` reconciled against the audit's independently
  deduplicated counts exactly on every complete day, and `machine burn --days
  7 --savings` now rejects the 999-wall counterexample the old vocabulary-only
  condition passed. So the meter is trustworthy.
  **The efficiency comparison itself remains open, on no evidence at all.**
  Not one card has been driven by a Codex session, so there is nothing to
  compare: no allowance figure, no quality baseline, no corrections-before-
  build or defects-within-fourteen-days tally for either arm. This close
  claims a working driver and nothing whatever about savings or about quality
  holding, which is what this plan's own added section asks of it. The first
  six Codex-driven cards' traces are what the reading will need, so nothing
  in this card prunes a lane's log, its rollout or its card history.
