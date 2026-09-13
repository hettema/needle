# Work that starts without you never goes live without you

**Carries:** docs/slice-suggestions/2026-09-12-work-that-starts-without-you-never-goes-live-without-you.md
**Status:** PENDING
**Written:** 2026-09-13, from the owner's Idea door conversation of 2026-09-12 (943300ef), where he asked whether he could turn Hello Revenue's auto-fix on and go to bed. The measurement in the suggestion moved the answer twice: from "hold every release" to "hold only what carries a schema change", and then, on his own question about what happens to the fixes finishing behind a held one, to holding on the range rather than on the session's own change.
**Effort gate:** xhigh — this is the one path on the board that reaches paying clients, and it is wrong in both directions: too tight and the switch stops shipping anything, which is the outcome he rejected on evidence; too loose and an ordinary fix promotes somebody else's schema change to get past a refusal it did not cause. The reading that gets it right has to hold the fold, the archive it interacts with, the beat that starts the next card, and four projects that are not Hello Revenue, at once.

## Intent

Turning auto-fix on should not also decide what reaches customers. Today it does: work the board starts closes like any other work, and a close promotes the stable branch, and Railway deploys it. The measured risk is narrow — 2.6 per cent of deploys fail and they fail closed behind the health check — with one exception that is not narrow, because the container runs `alembic upgrade head` on every boot and better than one in five schema changes rewrites or deletes live rows against a database the suite has never seen. When this is done, the owner turns the switch on and goes to bed: ordinary fixes ship all the way while he sleeps, and anything that would change the shape of stored data waits on the shared branch with the card saying it is his to release.

The rejected alternative, and why: holding *every* release from a session the board started. It is simpler and it was this plan's first shape. It was rejected on 2026-09-12 against the numbers — it defends one class in five by refusing the other four, and the thing he actually wants from the switch is fixes shipping.

## Proof of search

Named before this plan proposes anything new. `board/collision.py` already answers "what does this card share with what is running", from paths named in backticks that exist — a schema change is a new file, so it cannot see this class, and its comment already says the fold settles what two lanes share; it is cited, not extended. `board/dial.py::held_lanes` already answers "which planned work may not start, and why", and item 4 belongs inside it rather than beside it. `domain/dial.py` already holds the switch, the number and the machine's ceiling, so the declaration in item 2 goes there and not into a new settings concept. Hello Revenue's single-head ratchet (test_alembic_single_head.py, in its own repository) already holds the chain against two sessions numbering in parallel, and its archive gate's `_refuse_unsynced_main` already reads a standing hold file — both are relied on, neither is rebuilt. Neither is backticked as a path here on purpose: a backticked path reads as this lane's own ground and another project's file is not, which is card #77's defect and not this plan's to fix. What does not exist anywhere: a reader for "what would this release carry", and any per-project statement of what cannot be undone. Those two are the new things.

## Terrain

`api/board_cli.py` (the `fold` verb, where the refusal stands, and the turn verb that gains the declaration), `runtime/git.py` (the range read beside `fold`), `runtime/service.py` and `runtime/remote.py` (the fold seam, and the same answer from a machine over the wire), `board/dial.py` (whether a card is one the board started, and the hold on starting the next schema card), `api/dial.py` (the beat), `domain/dial.py` (the declaration's type beside the switch), `infrastructure/store.py` (where the declaration is kept, and the schema change that keeps it), `board/brief.py` (what the brief tells a session the board started), `board/parse.py` (the `Terrain:` line read for item 4), `tests/board/test_dial.py`, `tests/api/test_defects_column.py`, `tests/runtime/test_git.py`, and a new ratchet under `tests/ratchets/`.

This plan changes Needle's own memory (item 2), so its work runs against a private copy of the store and the shared board is only read; the lane folds under a running board, so it runs when no other work has hands on any project.

## Items

1. **What a release would carry, readable.** A runtime answer for the files a promotion of the stable branch would carry — the range between the stable branch and the shared branch, in the project's own checkout, on whichever machine holds it — beside the existing fold in `runtime/git.py` and reachable the same way `fold` already is, locally and over the wire. Nothing decides anything yet.
   *Done means:* from a lane whose shared branch is three commits ahead of the stable one, the verb names those three commits' files and no others; from a lane level with the stable branch it names none; a machine that cannot be reached says so rather than answering empty.
   Hands out: `execution` — running the new verb against a scratch repository in the four states (level, ahead, unreachable, no stable branch) and reporting each answer verbatim; verifies by reading the returned paths against `git diff --name-only` run by hand in the same scratch repository.

2. **Each board says what cannot be undone there, when its switch is turned on.** The declaration rides with the ruling it bounds: turning a board's auto-fix on records, beside the switch, the paths in that project whose change cannot be taken back, and where that project's standing hold on releasing is written. Hello Revenue's are its schema-change folder and the hold file its archive already reads; a board that names none has none, and everything there releases. A board already on keeps working and reads as undeclared until it is turned again.
   *Done means:* turning a board on and naming nothing leaves every release as it is today; turning it on and naming a path makes that path the thing item 3 stops on; the head shows each on board's declaration in the owner's words, and an on board that has never declared reads as undeclared rather than as empty.

3. **The release refuses itself when it would carry what cannot be undone.** In the fold verb, before the push: a session the board started may not promote the stable branch when the range from item 1 contains a path item 2 declared — whoever put it there, not only this session. It refuses having moved nothing, says in one sentence what is waiting and that the release is the owner's, and names the project's standing hold file as the thing to write so the closes behind it do not meet the archive's refusal. The ordinary fold to the shared branch is untouched, and a session the owner started himself is untouched.
   *Done means:* on a test board, a session the board started whose range carries a declared path folds to the shared branch and is refused the promotion, with the stable branch unmoved and the refusal naming the waiting file; the same session with nothing declared in range promotes as today; a session the owner started promotes in both cases; and the refusal's own sentence is what the card shows, not a second wording.

4. **A second one does not pile onto the first.** While a board's release is held, the beat does not start a card whose plan names a declared path in its `**Terrain:**` line — the line every plan already carries and `board/collision.py` already reads. The card waits visibly, as a card held by another already does, and says why. It is not refused and it is not the owner's.
   *Done means:* with a release held on a board, a planned card whose terrain names the declared folder is listed among the held work with the reason in one sentence, and a planned card whose terrain does not name it starts as usual; when the owner releases, the held card starts on the next beat without anyone touching it.
   Hands out: `search` — every place a plan's `**Terrain:**` line is already parsed or read, with path and line, so item 4 reads it through the existing one; verifies by opening each hit and confirming it is the same parse, not a second one.

5. **The card says the work is finished and the release is his.** A card whose work has landed and whose release is held reads as that, not as unfinished and not as shipped: what it did, that it is on the shared branch, what is waiting behind it, and that the next act is his. Its plan is archived normally, because item 3's hold file keeps the archive from refusing.
   *Done means:* the card's face carries one sentence a cold reader can act on — the work, the waiting, whose move — and the board moves it to the column a folded card goes to, never to shipped; a session that dies between the fold and the hold leaves the card saying the release is unheld and unclaimed, never saying it is done.

6. **A check refuses the loose shape.** A ratchet holds the thing that made this a defect rather than a preference: the promotion of the stable branch is decided on the range and never on one session's own change, so the leak cannot be written back in by someone reading item 3 as "did *this* session touch the schema".
   *Done means:* a test that fails when the decision is fed only the session's own changed files, and passes when it is fed the range; the ratchet names the leak in its docstring with the date, so a later session reads why the wider read is the point.

## Acceptance

- With auto-fix on and nobody awake, a night's ordinary fixes reach the stable branch and deploy, exactly as they do when the owner runs the same work himself.
- With auto-fix on and nobody awake, a night in which any session the board started produced a schema change ends with the stable branch where it was, every card closed and archived rather than half-closed, at most one schema change waiting, and the board saying whose move it is.
- The owner can turn a board on without naming anything and lose nothing he has today.

## Loop

Loop: WATCH: no release from a session the board started carried a change to stored data, and ordinary fixes still shipped the same night — command `uv --project /home/dennis/Work/needle run needle fixes hellorevenue` by 2026-10-13 every 7d

The thesis: a check on the range, not on the session, stops exactly the releases that carry a schema change and no others. If we see a night where a schema change reached the stable branch without him, the check is too loose and item 3's read is wrong. If we see a night where nothing shipped at all, the check is too tight — most likely item 2 declared a path too wide — and the declaration narrows rather than the rule loosening. Either reading is the method's, not the night's.
