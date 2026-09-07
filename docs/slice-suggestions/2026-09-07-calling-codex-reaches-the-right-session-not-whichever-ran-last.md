# Calling Codex reaches the right session, not whichever ran last

**Kind:** defect
**Fix:** now — a call that answers nothing costs the caller ten minutes of wait and the doctrine says a call is the one way to ask a colleague; the class is "the colleague a call reaches is chosen by recency, not fitness"
**Found by:** the allowance-glance session on slot eduard, 2026-09-07 (calls 5 and 6, `~/.cache/omarchy/claude-acct/discussion/from-allowance-glance-eduard.md`)
**Formerly:** A warm call resumes whatever Codex session was last, including its effort and its half-spawned threads (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)

`needle call codex <note>` resumed the most recent Codex session, 01a07bb6,
a card-73 lane whose header says `reasoning effort: none`. It read the note,
then its turn ended on `collab spawn failed: no thread with id 01a07bcf…`
(the log's last line) with no final message, so `wait 5` reported "finished
its turn without its note". The second call landed on 01a07bb3, a probe
session in a scratchpad directory, which answered well — with a read-only
sandbox that stopped it initialising SQLite under `~/.codex`, so it could not
finish the very probe the question asked for.

What is true when fixed: a call to a slot's "most recent" lands on a
colleague fit to answer — a judgment question runs at the effort the
doctrine puts judgment on, in a sandbox that can run a read-only probe — or
the call says up front which session it picked and what that session's
effort and sandbox are, so the caller can choose another. A turn that ends
on a tool error without a final message is reported as that error, not as
"finished without its note".
