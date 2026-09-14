# No card waits forever because the board keeps re-reading the same one

**Carried by:** docs/plans/done/2026-09-13-no-card-waits-forever-because-the-board-keeps-re-reading-the-same-one.md

**Kind:** defect
**Fix:** now — `api/dial.py::_wants_a_reading` already writes the bar it misses in its own words ("under a number above one the beat would otherwise open the same reading every minute and read nothing else"), so the intent is written and this is that same guard one case wider; the fix stays inside that guard and the cap beside it (`api/dial.py::_readings_that_died`, which counts only readings that died and so never bites on one that landed), and it removes the class — every reading whose result cannot change where the card routes until a commit rewrites the document — rather than the two cards stuck tonight

**Found by:** #82's reading, 2026-09-12

## The intent it breaks

The board only ever reads one card at a time, and right now it spends every
one of those turns on the same two cards, over and over, so nothing else on
any board is ever reached. Seventeen readings have been done since the seat
started running; sixteen of them are the same two Hello Revenue cards, read
again and again, each one landing the same answer and each one leaving the
card exactly where it was. Behind them sit 140 defects nobody has read — 57
of them Needle's own, waiting five to eight days — and every card parked on
the owner. Card #82 promised him that every card parked on him would be read
once by a second, cold reading, and warned it would take days because that
run starts behind the defects. It is not a matter of days: the queue in front
of it cannot drain on its own, so the parked run never starts.

## Evidence

`uv --project /home/dennis/Work/needle run needle decisions all`, read
2026-09-12: 17 rows, every one dated 2026-09-12, 10 on Hello Revenue #129 and
7 on #184. All 17 land `now`. All 17 end `routes as: needs triage`. No row has
ground `parked` — no card parked on the owner has been read at all, on any
board.

Why it repeats. `board/triage.py::routing_of`'s last branch is the invariant
that a row never routes more freely than the written record: a reading that
lands `now` on a document whose own `Fix:` line is not `now` leaves the card
at `needs triage` until a commit rewrites the mark citing the reading.
`api/dial.py::_wants_a_reading` opens a reading on exactly that state, and its
only brake, `api/dial.py::_readings_that_died`, counts sessions that landed no
result at all (`r.session_id not in landed and r.ended_at is not None`). A
reading that lands a result is not a death, so the cap of three never applies
to it. The next beat sees `needs triage` again and opens reading number
eleven.

The two cards say it themselves. #184's own reading ends: "The document carries
no `Fix:` line, so this reading authorises nothing until a session rewrites the
mark citing it." #129's document is marked `his`. Nothing on the machine
rewrites a mark; auto-fix is off on both boards (`needle dial`, read
2026-09-12). So the state that opens the reading is the state the reading
cannot change.

Why nothing else gets a turn. `api/dial.py::_take_next` sorts the unread queue
by `Candidate.age_key` and acts on one candidate per beat. Defects and titles
key `(0, born_at, number)`; parked cards key `(1, parked_since, number)` and so
rank behind all of them by design (card #82, ruling 9). #129 is the oldest
unread card on any board, so it is chosen every beat it has no reading open;
#184 is next oldest and fills the beats while #129's reading runs. The pair
holds the seat indefinitely, and everything behind them — including all 39
parked cards — waits.

## What would hold it

The brake has to count the readings that landed as well as the ones that died,
or the guard has to stop treating `needs triage` as unread when a reading of
today's text already stands and only a commit can move it. Either shape closes
the class: any card whose reading cannot change its own routing stops taking a
turn, and the queue drains past it.

The two cards then need the act their readings name — a commit rewriting each
document's `Fix:` line citing the reading — but that is those cards' business,
not this one's. This card is that one card can never hold the seat again.

## Live neighbours on this ground

None of the three carries it. #48
(`docs/slice-suggestions/2026-09-05-a-fix-that-files-what-it-found-outside-its-change-still-counts-as-done.md`)
is `api/dial.py::fixes`, the report of what a finished fix left behind, not the
queue. #66
(`docs/slice-suggestions/2026-09-05-one-word-never-names-two-different-things-on-the-board.md`)
renames the word "triage" across `board/triage.py` and the frontend; it changes
the words, not the guard.
`docs/slice-suggestions/2026-09-05-needles-own-defects-get-fixed-without-waiting-for-a-quiet-machine.md`
is an idea on `api/dial.py::_take_next` and `board/dial.py::is_quiet` — when the
beat may take a *fix* on Needle's own board, never which reading it opens.
