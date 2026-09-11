# A colleague's answer that arrived is never reported as missing

**Kind:** defect
**Fix:** now — the waiting command's whole promise is to hand back the answer a colleague landed, and calling a landed answer missing sends the caller to ask again for work already done; checking for the answer once more after the colleague's thread ends, before saying it is missing, removes that for every call and not for one.
**Found by:** the lane on card #124 (docs/plans/2026-09-10-a-sessions-message-is-answered-at-once-and-never-sent-twice.md), in the review's seams pass

## The intent it breaks

When a session asks a colleague of another kind to read its work, the board
is meant to bring that colleague's answer back the moment it lands. On card
#124 the board said the colleague had ended without answering while the
answer was already written in the place it names, so a session that trusts
the board would ask again and pay for the same read twice, or stop the
review believing the reader failed.

## Evidence

- Call 97 on card #124, 2026-09-11: `needle wait 97` printed
  `ended: 01a0905f ended without its note` and exited 1.
- The answer it names was on disk: `~/.cache/needle/card-124/from-codex-fresh-120901218148-re-cold-read-4.md`,
  1,981 bytes, modified 14:10 local, the same minute as the thread's log
  (`…re-cold-read-4.log`, 79,128 bytes, 14:10), holding a complete answer that
  ends `VERDICT: broke 2.3, 2.4 — …`.
- Inferred, not traced in the code: the wait saw the thread end before the
  answer file was written (the fresh thread writes its final message after
  the process it watches exits, or the wait reads the file once, before the
  write lands). The four other fresh calls on the same lane (91, 92, 94, 95)
  were reported landed.
