# A docs-only fold never carries a walked framework or a frozen record

**Kind:** defect
**Fix:** now — the intent it breaks is written in Hello Revenue's CLAUDE.md twice (a changed prompt or framework owes a role-play walk before the suite is green, held by `tests/ratchets/test_prompt_qa_walk_manifest.py`; the first board's record under `docs/board/done/` is frozen, held by `tests/ratchets/test_first_board_record_is_frozen.py`); the fix stays inside the door the sweep used to reach the trunk without a green suite, once that door is traced (the first step below); and it removes the class — any corpus rewrite from a Needle card that reaches a walked or frozen path in a project — not the one sweep that hit it.
**Found by:** the lane on Hello Revenue's card #474 (its suggestion `docs/slice-suggestions/done/2026-09-08-a-rewrite-of-the-boards-titles-never-touches-a-frozen-record-or-a-walked-framework.md`, filed by card #263's lane), whose third clause — narrow the sweep itself — this suggestion carries; Codex's review passes of 2026-09-08 named the clause unmet, asked for a concrete carrier, and asked that the entry path be traced rather than asserted.

## The intent it breaks

Needle #74's corpus commit (Hello Revenue 23de0e2c1, 2026-09-07, "every live title on the board says what it is for, in plain words") renamed suggestion files across 312 files and, in the same commit, rewrote sixty-six lines of a frozen historical record and three citation lines of a walked framework. It reached `origin/develop` without a green suite: the two ratchets that hold those files were red on the trunk from that commit on, so whatever door it used, no fold-time suite gated it. Hello Revenue's suite stayed red on those two checks for every lane that folded over the next two days (cards #461, #459, #462, #456, #263, #452, #472), each proving the reds trunk-side and folding over them. The repair (cards #473 and #474) cost a lane, a full-surface walk and a two-pass review; the class is still open, because the door is unchanged.

What is known and what is not: the commit is a single non-merge commit authored and committed as the owner, with no lane branch or review record beside it, and its message names Needle #74. Which Needle path pushed it — a corpus sweep run from the project's main checkout, the runtime's main-sync, or `runtime/git.py::fold` from a lane that ran no suite — is not established by this evidence, and the fix begins by establishing it (Needle's own ledger and the card's history for #74 are the sources).

## What fixes it

One boundary, not two: a corpus rewrite that a Needle card runs over a project's files treats `prompts/`, `frameworks/` and `docs/board/done/` as out of bounds — it refuses to touch them and says which files it left alone — so that a walked framework is only ever changed by a lane that owes the walk, and a frozen record is never changed at all. "Run the suite before the push" was considered and rejected as the boundary: it would let a sweep change a walked framework whenever a walk record happened to exist, which is not what the title promises. The check that shows it held: a rehearsal of the sweep over a fixture tree with one file under each of the three paths, asserting the three are untouched and the refusal names them.

Whether the same refusal belongs on the door itself (the main-sync or the fold) is decided by the trace above, not assumed here; this suggestion widens nothing beyond the three paths Hello Revenue's own rules already protect.

## What would settle it

The next corpus-wide rewrite from a Needle card: Hello Revenue's `git diff --stat` for the commit shows no path under `prompts/`, `frameworks/` or `docs/board/done/`, and the trunk's next lane fold reports the walk-manifest and frozen-record ratchets green without having to say "trunk-side".
