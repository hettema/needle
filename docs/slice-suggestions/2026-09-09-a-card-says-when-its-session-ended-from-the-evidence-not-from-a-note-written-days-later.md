# A card says when its session ended from the evidence, not from a note written days later

**Kind:** defect
**Fix:** now — the intent is written (the archived plan for card #68, `docs/plans/done/2026-09-05-work-the-laptop-interrupted-comes-back-by-itself-and-the-board-says-truly-how-it-ended.md`, whose intent says every word the card says about how a session ended is true, and whose item 1 says a death is named from what held the process and never from the registry's word); the fix stays inside the one sentence that says when a session ended (`board/lane.py:415–427`, which reads the registry's `updated_at` for the clock while the death record beside it already holds the last time the process was known alive); and it removes the class — every session the background service marked lost after a restart or a reboot carries a stamp days after its real end — not this one card.
**Found by:** #68's reading, 2026-09-09

## The intent it breaks

A card that says its session ended gives one time for that ending, and it is the time the evidence supports: when the machine last saw the process alive, or the kill that took it. Today the card gives two: the sentence at the top says "ended 27 h ago", read from the note the background service wrote when it noticed the session was gone after its own restart, while the evidence in the next sentence says the process was last active three and a half days earlier and the laptop had since gone down. While this holds, the owner reads a lane that died on the evening of 2026-09-05 as one that died yesterday morning, and the card's own words about its ending contradict each other on the same face.

## Evidence

Read on 2026-09-09 at 11:18Z from the served board (`GET /api/projects/hellorevenue/cards/435`) and a copy of the board's memory.

- Hello Revenue #435's face: *Something is wrong: the session on it ended 27 h ago with nothing landed. The process disappeared after its last activity at 2026-09-05 20:28Z, in a boot that ended 44.4 h later; the cause is not established.* Twenty-seven hours before the read is 2026-09-08 08:04Z.
- The session's registry row: `created_at` 2026-09-05 18:21Z, `updated_at` 2026-09-08 08:04:50Z, detail *ended while the background service was off* — the daemon's stamp for a session it lost across its restart, not the ending (card #68's memory: only a bare `stopped` is a stop).
- The death record for the same session (`store.deaths("hellorevenue")`): cause not established, `last_alive_at` 2026-09-05 20:28:56Z, named 2026-09-09 11:11Z. The boot that held the process ended 2026-09-07 16:51Z (`journalctl --list-boots`), so the process was gone at least 39 hours before the stamp the face reads.
- `board/lane.py:415–416` sets `last_seen` to the registry's `updated_at`, falling back to the lane record's `last_seen`; line 427 writes *the session on it ended {ago(last_seen)} ago* from it. The `Death` the same function reads for the cause carries `last_alive_at` and is not consulted for the clock.
- #341 and #417 read *ended 4 d ago* on the same pass, which happens to agree with their evidence because their registry rows were stamped near their real end; the disagreement appears only for a session the daemon marked lost later, which is every session that dies while the service is down or the laptop is off.

## What would fix it

The sentence takes its clock from the death record when one stands — its last-alive time, which the reader already bounds from the sighting or the transcript's last record — and only otherwise from the registry, so one time is said and it is the evidenced one; a fixture case where the registry's stamp is days after the transcript's last record asserts the face names the earlier time.
