# Every session of either make, on every project, knows how to ask a colleague

**Kind:** defect
**Fix:** his — the fix is one sentence in the one text (HOW-WE-WORK §12, where the watercooler is already named), and the one text changes only through a card the owner rules on; no project file may restate it
**Found by:** the owner, 2026-09-07, after a session on the machine asked Codex by a bare `codex exec` one-shot: "I believe we built something for this exact use case, why don't you know about it?" and then "you made the changes so that every session, claude or codex, now knows how to ask a colleague if I say it in a session as well?" — the answer to the second was no.

## Observation

- Plan 17 (card #51, Done) built `needle call` and `needle wait`: a colleague of either make is called warm with a note and the caller is told when the answer lands. Nine exchanges are measured in its review record and the verbs work.
- Nothing a session reads at start names them. `docs/HOW-WE-WORK.md` §12 says "a watercooler carries what one touched that another depends on" and stops; no project's CLAUDE.md names the verbs (Needle's and Hello Revenue's grepped 2026-09-07); the machine's CLAUDE.md said "sessions talk through files" and named the directory only, until commit 1aa3080 of 2026-09-07 added the verbs there.
- That commit reaches Claude sessions started in `~/Work/omarchy-machine` and nobody else: Codex reads `AGENTS.md`, and no project carries one (the global `~/.codex/AGENTS.md` is the one text); a session in Needle or Hello Revenue reads neither the machine's file nor any sentence about calling.
- So "ask Codex" or "ask a colleague" said in any other session today gets what this one did: a one-shot, cold, its exchange unmeasured, its answer in a scratch file the board never sees.

## The intent it breaks

§12: colleagues working together know about each other, and the watercooler is one delivery. §4: only what is written survives — the verbs exist but the instruction to use them was never written where a session reads. §3: one way to do each thing; today there are two, and the bare one is the one a session meets first.

## What would fix it

One sentence in §12 after the watercooler sentence, in the one text, so every make on every project on every machine reads it at the next session start:

> A session that needs a colleague's judgment calls one warm through Needle's `call` and waits on the answer with `wait`; it never launches a colleague of its own, because a call is a row the loop reads and a launch is not.

Then the machine's paragraph of 2026-09-07 shrinks back to what is true of the laptop only (the directory, the naming), and `docs/HOW-WE-HOLD-IT.md` gets the sentence's holder: today a trace (plan 17's table, which the WATCH row reads), tomorrow possibly a ratchet on rollouts and transcripts that names a bare `codex exec`/`claude -p` launched from a session.

Deliberately not: a per-project restatement, or a skill — a restatement in a louder place wins every conflict silently (the one text's head).
