# No card waits forever because the board keeps re-reading the same one

**Carries:** docs/slice-suggestions/2026-09-12-no-card-waits-forever-because-the-board-keeps-re-reading-the-same-one.md
**Status:** PENDING
**Written:** 2026-09-13, from the owner's Idea door conversation on Hello Revenue (e843ad41): he asked whether the 78 defects there were still real, learned that 75 were unread because the second reading had been stuck on three cards, and asked whether that was where the allowance had gone — "Let's stop it and fix it if it is." It was. The seat was stopped by hand at once (below); this plan is the fix.
**Effort gate:** high — the defect is diagnosed to the line by its own suggestion (`api/dial.py::_wants_a_reading` opens on `needs triage` and `stale` alone; `_readings_that_died` counts only readings that landed nothing), the fix is one guard and one fuse in the same file, and the board's own rules already say what must stay true (a `now` over a `his` never routes; a changed text is read once more; a card the owner parks is read once per park). What remains is scaffolded: where the fuse sits so it never blocks the one legitimate re-read, and what the card says while it waits. No test names either function today, so the tests are part of the work, not a reason for `xhigh`.
**Loop:** WATCH: no card is read more than twice on the same text — command uv --project /home/dennis/Work/needle run needle decisions all | awk '/^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]  / && $1 >= "2026-09-14" {print $2, $3}' | sort | uniq -c | awk '$1 > 2' | wc -l | sed "s/^/cards read more than twice since the fix: /" expect "cards read more than twice since the fix: 0" by 2026-10-13 every 1d

## Intent

The board reads one card at a time, cold, so that a defect's mark is verified before anything acts on it. For twenty-four hours that seat read the same three Hello Revenue cards over and over — 850 readings between 2026-09-12 18:52 and 2026-09-13 18:04 UTC, 507 of them on one card — because each reading landed a verdict the board could not act on (a `now` over a document that says `his` or carries no mark), the card stayed "needs triage", and the next beat read it again. Nothing else on any board was read in that time: 75 of Hello Revenue's 78 defects, every one of Needle's own, and every card parked on the owner.

What it cost, measured from the transcripts on 2026-09-13 (the board's own counting rule, `runtime/transcripts.py::tokens`):

| | tokens |
|---|---|
| the 850 readings | 629 million |
| everything ever spent from the Hello Revenue checkout | 795 million |
| one reading, median | 658 thousand |
| card #129 alone | 403 million |

Seventy-nine per cent of every token ever spent from that checkout went to those readings, in one day, across five subscriptions — which is why every account on the machine kept hitting its limit. The owner's question was whether this was where the allowance went. It was.

**What must be true when this is done.** A reading that cannot change where its card routes is not repeated: the card waits, says why in words he can read, and the seat moves on to the next card. And behind that guard sits a fuse the guard's next hole cannot get past: no card is read more than a few times on the same text, whatever the reason, so the worst a future defect in this file can cost is a handful of readings and a card that says the board stopped — never a day of the machine.

**What he gets.** The Defects column on every board gets read down and graded, so auto-fix has something to take and the gravest goes first; his parked cards get their cold reading; and a repeat of this failure is impossible by construction rather than caught by him noticing the bill.

**What this plan does not do.** It does not rewrite the three documents' marks — that is Hello Revenue's plan of 2026-09-13 ("No defect on the board is a duplicate, a ghost, or stuck on its verdict"), which cites each reading. It does not make a reading cheaper: 658 thousand tokens per reading is the seat's own cost at its effort level and is a separate question, worth its own suggestion once the column has been read down and the per-reading cost can be seen without the loop in the way.

## What is true today, and where it lives

**The stop that is in place.** On 2026-09-13 at about 18:10 UTC the conversation set the machine's number to zero (`needle dial --lanes 0`) and stopped the two readings then running (`needle stop 7feb78b0`, `needle stop 26f44fc3`). With the number at zero the beat opens nothing — no reading, no planning session, no fix lane — on any board (`api/dial.py::_take_next`, the `running(...) >= lanes` return). Corpus lanes are not under the number and still run. The number goes back to 4 at this plan's close, item 3, and not before: a reading opened before the fix lands re-enters the loop.

**Why it repeats**, verified in the code on 2026-09-13:

- `board/triage.py::routing_of`: a reading's `now` (or `when`) over a document whose own mark is stricter or absent routes the card as `needs triage` with the words "a commit has to rewrite the mark citing the reading first"; a `split` routes the same way. That is the invariant that a row never loosens the corpus, and it stays.
- `api/dial.py::_wants_a_reading`: opens a reading whenever the card routes as `needs triage` or `stale`, or its reading carries no grade; its only brake is `_readings_that_died`, which counts readings with no result (`r.session_id not in landed and r.ended_at is not None`) against `TRIAGE_ATTEMPTS = 3`. A reading that lands a result is not a death, so the cap never bites on the loop.
- `api/dial.py::_take_next`: one candidate per beat, the unread sorted by `Candidate.age_key` — defects and titles by `(0, born_at, number)`, parked cards behind them — so the oldest unread card is chosen every beat it has no reading open. #129 was the oldest on any board.
- `api/dial.py::_parked_unread` and `_wants_a_title_reading` share the seat and the same cap; a parked card's cap counts per park (`since=parked_at(placement)`).
- No test under `tests/` names `_wants_a_reading` or `_readings_that_died` (grep, 2026-09-13).

**What landed before this plan was committed** (read on 2026-09-14, at the Discuss door of Hello Revenue #524): the owner's own commit `6efa8db` of 2026-09-13 21:25 put item 1's guard into `_wants_a_reading` — a graded reading on today's exact text that still routes `needs triage` holds the card, with the reason in a comment naming this card — and one test, `tests/api/test_the_triage_seat.py::test_a_card_whose_reading_cannot_move_it_is_never_read_again`. Still open from item 1: the card's words in his language, `needle fixes` saying what was read and when, and the test keyed to every branch of `routing_of`. Item 2's fuse and item 3's number are untouched: `needle dial` still says 0.

**The evidence the board keeps.** `store.latest_triages(slug)` carries each card's latest reading with `document_fingerprint` and `source_fingerprint`; `store.windowless_sessions(slug, work=SessionWork.TRIAGE)` every reading opened, with `started_at` and `ended_at`; `store.triages(slug, number)` and `store.title_readings(slug, number)` the ones that landed. Everything the guard and the fuse need is already there; nothing new is stored.

**The words the card shows.** The routing sentence (`Routed.why`) is what `needle fixes`, the card and the rail print; the Defects column's head line counts `needs triage` cards as "read and settled by nobody" (`board/assemble.py::defects_column`). The card's face should say, for a card the guard holds, that it was read, when, what it landed, and that only a commit moves it — in his words, not "needs triage".

**The neighbour that would have hidden this.** `docs/slice-suggestions/2026-09-05-needles-own-defects-get-fixed-without-waiting-for-a-quiet-machine.md` is about when the beat may take a *fix* on Needle's own board; it does not touch which reading opens.

## The work

### 1. A reading the board cannot act on is not repeated

In `_wants_a_reading`: when the card's latest reading is fresh — both fingerprints match today's document and source — and its result routes as `needs triage` for a reason only a commit can change (`now` or `when` over a stricter or absent mark; `split`), the card is not a candidate. The card's routing words already say what is waited for; the face says it in his words.

**Done means:** on a board holding such a card, the beat opens no reading on it, and the seat reads the next unread card; `needle fixes <slug>` says the card was read, when, what it landed, and that a commit rewriting the mark is what moves it; a test drives the guard through every branch of `routing_of` — the branches that end in `needs triage` for a commit's reason hold the card, `stale` and the no-reading branch still open one — keyed to the routing function's own results so a new branch fails the test until it is stanced.

Hands out: `search` — every place that decides a card is unread or opens a reading (`_wants_a_reading`, `_parked_unread`, `_wants_a_title_reading`, `_readings_that_died`, `_landed`) and every test that names the seat's words, as paths and lines; verifies the executing session reads each before changing the guard, because the parked and title readings share the seat and the cap and must keep their own once-per-park and once-per-title rules.

### 2. A fuse no future hole gets past

Behind the guard, a cap that counts every reading opened on a card since its document's text last changed — landed or not — and past which the board opens no more on that text, and the card says so: read N times on this text, the board stopped, and what would start it again (a change to the document or its source). The existing `TRIAGE_ATTEMPTS` and `_readings_that_died` are the place to start; whether the fuse widens that counter or stands beside it is the lane's call, with one rule: the one legitimate re-read of a changed text (a `stale` card) always gets its reading, because the fuse keys on the text and a changed text is a new count.

**Done means:** a card with three readings on one text is not opened again until the text changes, whatever the readings landed; the card's face says the board stopped and why; a test says so for a defect, a title and a parked card alike; and the words never claim "needs triage" for a card the board has given up on.

### 3. The seat is back on, and its first day is watched

At the close, the machine's number goes back to what it was (`needle dial --lanes 4`), the readings resume, and the Loop line above reads the next day: no card read more than twice on the same text since the fix. The first cards read are the three Hello Revenue cards whose marks that repository's plan rewrites — each gets exactly one fresh reading of its new text, which is the proof the guard and the fuse both hold.

**Done means:** `needle dial` says 4; readings open on cards other than #129, #184 and #283 within an hour of the fold; the Loop's command prints zero the next day.

## Acceptance, as behaviours

**The seat never spends two readings where one already answered.** After the fold, `needle decisions all` shows at most one new reading per card per document text, and the column's unread count falls every hour the machine has room.

**A held card tells him what it waits for.** The card's face and `needle fixes` say when it was read, what the reading landed, and that a commit to the document is what moves it — never a bare "needs triage".

**The fuse is loud, not silent.** A card the fuse stops says so on its face and in `needle fixes`; nothing is quietly skipped.

**The three rules the seat already keeps still hold.** A changed text is read once more; a parked card is read once per park; a title is read once per title. The tests of item 1 and 2 say so, and the existing signal, parked and title readings pass unchanged.

**The number is restored by the close, not before.** `needle dial` shows 0 until the fold and 4 after; the close-out names the moment.
