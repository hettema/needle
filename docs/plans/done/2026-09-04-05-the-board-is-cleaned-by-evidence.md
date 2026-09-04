# 05 — The board is cleaned by evidence

**Status:** DONE — built 2026-09-04 by the build session (Claude Fable 5.1 at high), reviewed in `docs/reviews/2026-09-04-the-board-is-cleaned-by-evidence.md`, folded to `origin/develop` the same evening; the verdicts written on Hello Revenue's board after the served board was restarted on the new code, main synced
**Written:** 2026-09-04, from the owner's intent stated the same afternoon on seeing Hello Revenue's whole board for the first time: "get the board squeaky clean, not by just discarding stuff but by being smart about it. Find things we can guarantee are done or no longer relevant first, then iterate smartly so we can make informed decisions as quickly and efficiently as possible." Prioritising what remains is the round after, and not this slice.
**Effort gate:** high — the mechanics (evidence classes, a triage view, batched acceptance) are specified below; the judgment is in the verdict each open card gets, which the lane writes with its evidence and the owner accepts or overturns. Nothing is discarded by the machine.
**Sequencing:** after 04. Uses the doubt marks, the signal grammar and the batched owner questions.

## Intent

Every open card on the board carries a verdict with its evidence, and the owner clears the board in a few sittings by accepting verdicts in batches, overturning the few he disagrees with, and reading only the evidence, never the whole card. What is provably done or no longer relevant leaves first; what remains open is open on purpose, with a written reason, and ready for the prioritisation round.

### 1. Evidence classes, one per open card

Every card outside Done and Not now gets exactly one evidence class, computed where the corpus and the machine can say and judged by the lane where they cannot, with the evidence beside it:

| Class | Evidence | Recommended verdict |
|---|---|---|
| **shipped, signal read** | plan archived, DELIVERED written, signal read delivered | Done |
| **shipped, signal owner-only** | plan archived, DELIVERED written, signal is an owner question | stays Executed; the question joins the batch |
| **built under another name** | a suggestion whose subject an archived plan delivered (cited, or the lane finds the delivery in the plan's close-out) | Done, citing the plan |
| **superseded** | the intent was overtaken by a later ruling or plan (cited) | Not now, citing what overtook it |
| **doubted** | a machine placement whose evidence is gone (from slice 04) | the doubt's own fact decides: Decision moment or back where it came from |
| **stale plan** | a plan in Planned or Up next older than a stated age with no lane ever | Decision moment with "still true?" |
| **live and open** | none of the above | stays, with a one-line reason |

Done means: every open card carries a class, an evidence sentence and a recommended verdict, written through `needle row` as a RULING-kind row the owner has not yet accepted (the row names the class); the lane's table of every verdict with its evidence is in the close-out; no card is moved by this slice until the owner accepts.

### 2. A triage view

Done means: the page has a triage lens over one project: every open card as one line — number, title, class, evidence, recommended verdict — grouped by class, with **Accept all in this class**, **Accept** and **Overturn** per line; accepting moves the card by the machine with the verdict's reason on its history row and the owner named as the acceptor; overturning keeps the card and records his word; the lens is reachable from the attention rail ("N cards carry a verdict you have not read").

### 3. Hello Revenue's board is triaged

Done means: the lane runs the classification over every open card on Hello Revenue's board (roughly 250 today: 152 Backlog suggestions, 9 Planned, 1 Up next, 13 Decision moment, 66 Executed), reads the corpus for the "built under another name" and "superseded" classes rather than guessing, writes the verdicts, and ends its turn with the counts per class and the ten verdicts it is least sure of, for the owner's first sitting. The lane never moves a Hello Revenue card.

### 4. What stays open is ready for the next round

Done means: every card left open after acceptance carries its "live and open" reason in one line, so the prioritisation round starts from a board where every card has already answered "why are you still here".

## Terrain

- The board's own facts: doubts (`board/lane.py` predicates, slice 04), signals (`board/signals.py`), the audit rows, `document_state` and `document_path` on each card.
- Hello Revenue's corpus for the judgment classes: `docs/plans/done/*.md` close-outs (`## Close-out` stances name what each plan delivered), `docs/slice-suggestions/done/` (suggestions already archived name the plan that carried them), `docs/wiki/` for what superseded what. Read-only.
- `needle row` for writing the verdict rows; a new row kind if RULING does not fit (a verdict is a proposal until accepted — say which in the Rulings).
- The frontend's lens switch (`rank`, `age`, `gate` on the board) is where the triage lens joins.

## Acceptance criteria (behaviours)

1. Every open Hello Revenue card shows a class, evidence and recommended verdict; the attention rail counts the unread ones.
2. Accepting a class moves every card in it by the machine with the reason and the owner's name on each history row; overturning one keeps it and records his word.
3. The lane's close-out lists counts per class and its ten least certain verdicts.
4. No Hello Revenue card is moved by the lane itself.

## Rulings

Recorded as the build made them (Claude Fable 5.1 at high, 2026-09-04), each with the alternative rejected.

1. **A verdict is a VERDICT row, one per card, in a grammar the board parses like WATCH's: `<class> — <evidence> → Done|Not now|Decision moment|Backlog|Planned|Up next|stays`.** RULING did not fit: a RULING row is the owner's word, and a proposal wearing that label would read as his. When he rules, the VERDICT row becomes a RULED row carrying his ruling and the verdict's whole text, so the card says one thing about its fate and the history keeps both. Rejected: a table of verdicts (a second store for what a row already holds, and unreachable through `needle row`); a RULING-kind row (the plan's own suggestion).

2. **The board writes the four classes its own facts settle — shipped with the signal read, shipped with a signal only the owner reads, doubted, stale plan — through `needle verdicts SLUG --write`; a session writes the three the corpus decides.** The next cleaning round starts from the machine's read, not from a session re-deriving it. Rejected: the board guessing "built under another name" from titles and stems (a guess in a confident voice, the thing the doubt mechanism exists to refuse).

3. **A plan is stale after 21 days in Planned or Up next with no lane ever.** The 11 Aug oversight read found every plan older than that needing a terrain re-check before execution. Rejected: 30 days (two of the three stale plans on the board would have missed it by a day).

4. **Accepting a verdict that stays on a doubted card re-places the card by the owner's own hand, so the placement becomes his word and is trusted from there; accepting "stays" on a held or trusted card writes no move row.** Seven of Hello Revenue's doubted cards are doubted for a stale link or a lost document, not for missing work; the owner's acceptance is the fact that answers the doubt. Rejected: every accept becoming an owner placement (a held shipped card would stop being re-tested, and the doubt mechanism would go blind exactly where it earns its keep); a doubted card's "stays" leaving it doubted (the owner would accept the same verdict every sitting).

5. **The owner's rulings park; a session's deferrals stay in Backlog.** A suggestion the owner parked, demoted or held back by ruling is superseded by that ruling and goes to Not now with the ruling as its wake; a suggestion a session deferred with a trigger is live and open, in Backlog, with the trigger as its one-line reason. Rejected: every "deferred" head line reading as Not now (Backlog is where a deferred signal lives by the corpus's own convention; the owner's move is the discriminator).

6. **A duplicate or a moot card goes to Not now citing what carries the intent, never to Done.** Done is a closed loop; nothing was delivered under the duplicate's name. Rejected: Done for duplicates (a lie about delivery), Backlog (the board keeps two cards for one intent).

7. **An archived document that names its card links to it, archived.** The corpus read linked live documents only, so a plan written at the close and archived in the same fold left its card doubted "for want of a plan" while naming it from done/. Adjacent to the slice and in its service: a false doubt is a false verdict. The four shipped cards whose plan names no card stay doubted; the close-out names the one-line edit. Rejected: the lane editing Hello Revenue's plans (a lane's git never targets another repository).

8. **Accept all in a class is one request that rules card by card; a refusal stays with its card and the answer names it.** A refused card (a verdict sending a card to Executed with no readable signal) never blocks the class. Rejected: one transaction for the class (one bad verdict would refuse a hundred good ones); the page calling accept per card (a hundred round trips under a lock the loops share).

## Close-out

Built 2026-09-04 by the build session (Claude Fable 5.1 at high). Review: `docs/reviews/2026-09-04-the-board-is-cleaned-by-evidence.md`. Each acceptance behaviour, stanced before the second fold, with the evidence.

1. **Every open Hello Revenue card shows a class, evidence and recommended verdict; the attention rail counts the unread ones** — met on the served board. The 197 judgment verdicts (194, then the three cards born during the write) were written through `needle row` from this lane after the fold and the restart (the served code has to know the row kind before the first row lands: the old server read every row's kind as an enum), then `needle verdicts hellorevenue --write` wrote the classes the board's own facts settle: 47 written (shipped, signal owner-only: 47); 3 for the corpus to decide. The table below is read back from the served board over HTTP. Four false doubts cleared before any verdict was written: the relink from archived documents (ruling 7) linked #241, #210, #238 and #239 to the plans in done/ that name them, and the doubted count on the rail went from 22 to 18.
2. **Accepting a class moves every card in it by the machine with the reason and the owner's name on each history row; overturning one keeps it and records his word** — met on the floor (`tests/api/test_triage.py`, `tests/infrastructure/test_store_doors.py`, `frontend/tests/board.test.tsx`). No Hello Revenue verdict was accepted by this lane: the lens waits for the owner's first sitting.
3. **The lane's close-out lists counts per class and its ten least certain verdicts** — below.
4. **No Hello Revenue card is moved by the lane itself** — met: the lane's only writes on that board are VERDICT rows; the served board's column counts after the write are what they were before it (9 Planned, 1 Up next, 13 Decision moment, 66 Executed) except Backlog, 152 to 155 by the three cards the corpus read birthed, not by any move.

Item 4 of the intent (what stays open is ready for the next round) is met by construction: every live-and-open verdict carries its one-line reason, and accepting it records that reason on the card as a RULED row.

### The classification, as the served board reads it

Read from the served board after the write: 244 verdicts on 244 open cards; the attention line says 244 unread, 18 doubted.

| Class | Cards | Landing |
|---|---|---|
| shipped, signal read | 1 | 1 → Done |
| shipped, signal owner-only | 47 | 47 → stays |
| built under another name | 17 | 17 → Done |
| superseded | 16 | 16 → Not now |
| doubted | 18 | 11 → Decision moment, 5 → stays, 1 → Done, 1 → Not now |
| stale plan | 3 | 2 → Decision moment, 1 → Not now |
| live and open | 142 | 142 → stays |

### The ten verdicts the lane is least sure of

- **#215** — built under another name: #228 taught Ava the author's reasons; this asks Ava to check before defending, a neighbouring behaviour
- **#266** — built under another name: the tracking-chain plan fixed the first-beacon cookie without citing this suggestion
- **#294** — built under another name: a rendered-text guard exists, on the repaint path; the suggestion asked for it on every regen
- **#310** — built under another name: the SERP mockup draws a favicon; whether it is the captured one from product analysis is read from the component's comment
- **#371** — built under another name, with #372: the repair turn and the annotation drop answer the instances on record; the portfolio-check floor was declined, so a fourth instance could still kill a build
- **#272** — superseded: an April checklist; if any owner task in it was never done, the new site would not show it
- **#281** — superseded: read from the tracking chain's rebuild, not from a sweep of the pages
- **#333** — superseded: folded into #144's third ruling; if the ruling is answered without the Google-reach question, this reopens
- **#187** — doubted, to Not now: the board it describes is retired, but its DELIVERED stands; Done would also be defensible
- **#219** — shipped, signal read: your 4 Sep ruling is on the plan's status line, not on the card

### Every verdict, by class

| Card | Column | Class | Evidence | Landing |
|---|---|---|---|---|
| #219 | Decision moment | shipped, signal read | your ruling of 4 Sep on its plan's status line: 'this is live, card can be moved to done'; forks 1 and 5 settled by #222, forks 2 to 4 live as Backlog cards | Done |
| #101 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #102 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #103 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #117 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #119 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #124 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #125 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #131 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #132 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #133 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #135 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #136 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #137 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #170 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #171 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #173 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #175 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #177 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #178 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #180 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #181 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #182 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #185 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #186 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #192 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #193 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #194 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #195 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #198 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #201 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #208 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #209 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #210 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #213 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #217 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #222 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #225 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #229 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #230 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-03 | stays |
| #231 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #235 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #237 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #238 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #239 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #241 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #246 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #259 | Executed | shipped, signal owner-only | the plan is archived and DELIVERED is written; the signal is a question only you can read, due 2026-09-11 | stays |
| #179 | Backlog | built under another name | its suggestion is archived SUPERSEDED, delivered by Needle: WATCH signals the machine reads and moves on, owner questions batched (Needle's slices 03 and 04); its RULED row is honoured, a proven watch moves the card to Done itself | Done |
| #215 | Backlog | built under another name | the plan archived 3 Sep whose card is #228 (card #228) cites its evidence as the cost it closes: Ava now answers why with the reason the author wrote or admits none was stored | Done |
| #266 | Backlog | built under another name | docs/plans/done/2026-06-08-trustworthy-tracking-chain.md fixed hr_vid persistence in the browser tag: the cookie is set before the first beacon fires and relayed across the hop | Done |
| #286 | Backlog | built under another name | docs/plans/done/2026-06-11-01-platform-foundation-generalization.md closes it by name; its own head says CLOSED for both surfaces it named | Done |
| #288 | Backlog | built under another name | promoted to docs/plans/done/2026-05-05-meta-account-history-aggregation.md, which names it as its origin and shipped | Done |
| #294 | Backlog | built under another name | a rendered-text guard checks the words on repainted pictures (docs/plans/done/2026-08-30-carousel-edits-one-card-at-a-time.md and #237's plan (archived 3 Sep)) | Done |
| #297 | Backlog | built under another name | docs/plans/done/2026-06-07-lp-top-1pct-overhaul.md names it as origin and says it is its full realization, all phases | Done |
| #302 | Backlog | built under another name | docs/plans/done/2026-08-18-model-slot-eval-program.md (card #135): every AI job has its own model slot in Settings with an evidence registry, 19 seats | Done |
| #310 | Backlog | built under another name | the Google ad preview draws the favicon and business name (frontend/src/components/campaign/GoogleSerpMockup.tsx, identity row) | Done |
| #339 | Backlog | built under another name | docs/plans/done/2026-08-14-surface-texture-differentiation.md names it as its evidence base and shipped the differentiation defense | Done |
| #347 | Backlog | built under another name | docs/plans/done/2026-08-19-value-stack-authored-chrome.md (card #124) wrote the two money-summary labels in the page's own language | Done |
| #349 | Backlog | built under another name | docs/plans/done/2026-08-25-offer-scoped-numbers-hold.md shipped the shape you ruled on 25 Aug and records this suggestion as the rejected alternative | Done |
| #371 | Backlog | built under another name | #222's plan built the repair turn (a target below the limit, a declared last resort instead of raising) and #246's plan dropped annotation keys instead of re-rolling; the portfolio floor it also names was declined as a build-killer | Done |
| #372 | Backlog | built under another name | the same three instances as #371: the repair turn (#222) and the annotation-key drop (#246, #246's plan (archived 3 Sep)) | Done |
| #388 | Backlog | built under another name | born 4 Sep when #210 was relinked to docs/plans/done/2026-09-01-contradiction-repair-holds-the-deal.md, which names #210 and this suggestion as its origin and shipped; the suggestion belongs in done/ | Done |
| #389 | Backlog | built under another name | born 4 Sep when #238 was relinked to #238's plan (archived 3 Sep), which names #238 and this suggestion and shipped; the suggestion belongs in done/ | Done |
| #390 | Backlog | built under another name | born 4 Sep when #239 was relinked to #239's plan (archived 3 Sep), which names #239 and this suggestion and shipped; its gated half stays a written trigger there | Done |
| #120 | Backlog | superseded | a duplicate: its two cited suggestions are cards #326 (query-key factories) and #346 (test files outside the type gates), and the citation itself is malformed so the board reads it as gone | Not now |
| #153 | Decision moment | superseded | its own Q row rules it future-dated: decides at the option grant, not now; that grant is the wake | Not now |
| #223 | Decision moment | superseded | its plan is written and is card #263 (#263's plan (3 Sep), Planned); one card carries the intent forward, this one is its older twin | Not now |
| #227 | Backlog | superseded | your ruling of 2 Sep held it back until a real client hits a failed line; that line is the wake | Not now |
| #232 | Backlog | superseded | your ruling of 2 Sep: wanted, not now, once the new build is proven on real campaigns; #263's plan sequences it after #222 proves | Not now |
| #252 | Backlog | superseded | its suggestion is archived SUPERSEDED: the widget it fixed was removed with the first board on 2026-09-04 (docs/slice-suggestions/done/2026-09-03-the-bar-widget-still-asks-the-board-every-eight-seconds.md); a bar widget for Needle would wake it | Not now |
| #272 | Backlog | superseded | an April deployment checklist for the logged-out site; the site was rebuilt by docs/plans/done/2026-07-25-marketing-site-repositioning.md and again by #231's plan (archived 2 Sep) | Not now |
| #281 | Backlog | superseded | a one-time sweep of April's in-flight pages to pick up the hosted tag; the tracking chain was rebuilt on 8 Jun (docs/plans/done/2026-06-08-trustworthy-tracking-chain.md) and every page since carries the new tag | Not now |
| #285 | Backlog | superseded | the LP overhaul retired the mechanism (a user-set visual-style knob) as off-grain and absorbed the need into the feedback-to-ICAV edit path (docs/plans/done/2026-06-07-lp-top-1pct-overhaul.md) | Not now |
| #307 | Backlog | superseded | demoted from the plan queue by your ruling of 17 Aug (defer for now, its head); its promotion back is a move, not a rewrite | Not now |
| #313 | Backlog | superseded | deferred by you on 19 Jun; #238's plan (archived 3 Sep) took the other path and says so (not the 2026-06-19 idea) | Not now |
| #319 | Backlog | superseded | parked by your decision of 8 Jul (not the right use of our time right now, its head); the trusted-number path carries a non-code step | Not now |
| #328 | Backlog | superseded | parked 25 Jul as a decision, not a vanished conversation (its head): recommended defer, your question answered | Not now |
| #330 | Backlog | superseded | the same hole as #374 (the raw-button ratchet's line-local regex, still /<button[\s>]/ on 2026-09-04); #374 carries the fresher evidence | Not now |
| #333 | Backlog | superseded | its question is #144's third ruling (must the client's phrasing appear in the ad text); one place to rule | Not now |
| #343 | Backlog | superseded | rides with #121 (#121's program), parked until a signed online-shop client | Not now |
| #143 | Executed | doubted | no WATCH row, and none is owed: its RULED row records the ruling executed (the rehearsal half shipped as #103, the aperture half is #196's plan); its plan is archived and DELIVERED written | Done |
| #154 | Executed | doubted | a 0.1 watch note (Monday's four firsts) with no plan, no DELIVERED and no readable signal; nothing shipped-shaped stands behind it | Decision moment |
| #155 | Executed | doubted | a 0.1 watch note with no plan, no DELIVERED and no readable signal; the carousel-edit plan of 30 Aug is archived and this watch belongs on its card | Decision moment |
| #156 | Executed | doubted | a 0.1 watch note (the next placed photo) with no plan, no DELIVERED and no readable signal | Decision moment |
| #157 | Executed | doubted | a 0.1 watch note with no plan, no DELIVERED and no readable signal | Decision moment |
| #158 | Executed | doubted | a 0.1 watch note with no plan, no DELIVERED and no readable signal | Decision moment |
| #159 | Executed | doubted | a 0.1 watch note with no plan, no DELIVERED and no readable signal | Decision moment |
| #160 | Executed | doubted | a 0.1 watch note (Sonepar's Try again) with no plan, no DELIVERED and no readable signal | Decision moment |
| #161 | Executed | doubted | a 0.1 watch note with no plan, no DELIVERED and no readable signal; #253's signal watches the same ledger | Decision moment |
| #162 | Executed | doubted | a 0.1 watch note (the next production release) with no plan, no DELIVERED and no readable signal | Decision moment |
| #163 | Executed | doubted | a 0.1 watch note with no plan, no DELIVERED and no readable signal | Decision moment |
| #164 | Executed | doubted | a 0.1 watch note (two chat-edit fixes) with no plan, no DELIVERED and no readable signal | Decision moment |
| #187 | Executed | doubted | a 0.1 card with DELIVERED written (the board picks up its own new code) and no plan or suggestion in docs/; the board it describes was retired on 2026-09-04 (docs/plans/done/2026-09-04-retire-the-first-board.md) | Not now |
| #188 | Executed | doubted | a 0.1 card with DELIVERED written and your RULED row (build it before the first Google campaign), but no plan or suggestion anywhere in docs/ carries it; the question due 2026-09-11 is the only loop left | stays |
| #189 | Executed | doubted | its plan is archived at docs/plans/done/2026-09-01-the-board-clears-its-own-disagreements.md (DELIVERED written, your question due 2026-09-11); the file names no card, so the board cannot link it | stays |
| #228 | Executed | doubted | its plan is archived at the plan archived 3 Sep whose card is #228 (DELIVERED written, your question due 2026-09-11); the file names no card, so the board cannot link it and reads no plan behind the card | stays |
| #244 | Executed | doubted | its plan is archived at docs/plans/done/2026-09-03-needle-board-on-omarchy.md (DELIVERED written, your question due 2026-09-11); the file names no card, so the board cannot link it | stays |
| #249 | Executed | doubted | its plan is archived at docs/plans/done/2026-09-03-the-board-stops-asking-and-starts-listening.md (DELIVERED written, your question due 2026-09-11); the file names no card, so the board cannot link it | stays |
| #110 | Planned | stale plan | a plan of 6 Aug, 29 days old with no lane ever; the 11 Aug oversight read found its acceptance organic (the owner's felt read, no mechanical floor): still true? | Decision moment |
| #121 | Planned | stale plan | a plan of 20 Jun, 76 days old with no lane ever, parked by you as a program; its WAITS row names the wake, a signed online-shop client | Not now |
| #262 | Planned | stale plan | the umbrella plan of 7 Aug, 28 days old with no lane; slices 0, 1, 1b, 1c, 2, 2b, 2c and 4 are archived under docs/plans/done/, slice 5 was never written: close the program or write slice 5? | Decision moment |
| #105 | Backlog | live and open | the proposal card's state model, a chain of if-statements over two files; no plan | stays |
| #106 | Backlog | live and open | waits on a live client paying this way and a design for your sign-off (the WAITS row) | stays |
| #107 | Backlog | live and open | deferred by you until the first generated playbook meets real leads (its head: do not execute without owner go); waits on notes from real sales calls (the WAITS row) | stays |
| #108 | Backlog | live and open | a note with no document: the fixes from the mobile review, written down, none applied | stays |
| #109 | Planned | live and open | a plan of 15 Aug, 20 days old with no lane, a day under the three-week line; the direction-record plan it builds on shipped | stays |
| #111 | Backlog | live and open | waits on chat editing becoming a client's daily habit (the WAITS row) | stays |
| #112 | Backlog | live and open | a note with no document: the admin screens still to design | stays |
| #113 | Backlog | live and open | a Calendly booking creates a new visitor instead of linking the ad click; no plan | stays |
| #114 | Backlog | live and open | parked by the instant-forms plan until the falsifying test produces results; the optimization-goal override is still unbuilt | stays |
| #115 | Backlog | live and open | a weekly spend cross-check against Meta's own totals; no plan | stays |
| #116 | Backlog | live and open | waits on a live campaign past Meta's learning phase (the WAITS row); the ladder machinery exists, nothing is wired into it | stays |
| #122 | Backlog | live and open | a program (managed ad spend, clients never touch Meta); planning it is the next act, no plan yet | stays |
| #126 | Backlog | live and open | a live claims-check miss (a results-in-24-hours promise shipped); no plan; the residue the direction-record plan filed | stays |
| #127 | Backlog | live and open | a dozen background jobs read the Meta login the non-renewing way; no plan | stays |
| #128 | Backlog | live and open | refuse any ad account or page not on the offered list at first deploy; no plan | stays |
| #129 | Backlog | live and open | an intent question for you (its head says so): tell our checker broke apart from the work is bad | stays |
| #130 | Backlog | live and open | verifier scope mappings for Google flywheel actions, a known gap since the Google flywheel plan of 17 Jun; no plan | stays |
| #134 | Executed | live and open | shipped (plan archived, DELIVERED); its command signal reads 2 of the 3 review reports it expects, read daily until 2026-09-11 | stays |
| #139 | Decision moment | live and open | four rulings on booking-first pages are yours (the Q row); the plan waits on them | stays |
| #144 | Decision moment | live and open | four Search-authority rulings are yours (the Q row); #196 and #331 wait behind them | stays |
| #147 | Decision moment | live and open | the deploy note is done (DELIVERED); its ASK waits on you: correct the mhall stamp to EUR 499.01 or let it stand | stays |
| #148 | Decision moment | live and open | the guarantee in the win-back campaign waits on your ratify-or-drop (the Q row) | stays |
| #149 | Decision moment | live and open | your read of the investor deck built 28 Aug (the ASK row) | stays |
| #150 | Decision moment | live and open | the app surface walk's open calls wait on you (the ASK row) | stays |
| #151 | Decision moment | live and open | license the Satoshi font or swap it: your call (the Q row) | stays |
| #152 | Decision moment | live and open | everything buildable in the doubling-clock program shipped by 29 Aug; closing the program is your ruling (the Q row) | stays |
| #172 | Planned | live and open | planned 30 Aug from the self-paced review; no lane yet; carries one call that is yours at execution | stays |
| #174 | Up next | live and open | planned 31 Aug from the self-paced review and ranked first in Up next; no lane yet | stays |
| #176 | Planned | live and open | planned 31 Aug from the self-paced review; security hardening on the deploy path, no lane yet | stays |
| #183 | Backlog | live and open | the scoped-asset dedup has never fired (found at #117's close); needs its own before-and-after run; no plan | stays |
| #184 | Backlog | live and open | a typed boundary marker can cut a client's message in half; pre-existing, nothing corrupted; no plan | stays |
| #190 | Backlog | live and open | your call whether Ava may speak a viability verdict to a client (the Q row): it reverses a standing stance | stays |
| #191 | Backlog | live and open | a design-system consolidation filed at #132's close (four copies of one quiet link); no plan | stays |
| #196 | Planned | live and open | planned 1 Sep, split out of #143's plan; waits on #144's four rulings (the WAITS row) | stays |
| #197 | Backlog | live and open | a ritual, a morning session sorting the QA report against written rulings; no plan yet, and the QA email has yet to carry a real event | stays |
| #214 | Decision moment | live and open | shipped 1 Sep (plan archived, DELIVERED, REVIEW); its WATCH row is 0.1 prose the board cannot read, so it cannot enter Executed until the signal is rewritten in the grammar; two rulings in it are yours | stays |
| #220 | Backlog | live and open | still live under Needle (its head says so, 2026-09-04): the fold does not run the suite on the rebased tree; no plan | stays |
| #242 | Backlog | live and open | ruled 3 Sep (the UK cross-industry campaign supplies the three formats); next in line to plan, no plan yet | stays |
| #253 | Decision moment | live and open | shipped 3 Sep (plan archived, DELIVERED, REVIEW); its signal starts with your step, re-sending the failed invoice.paid events in Stripe, due 2026-09-11 | stays |
| #261 | Planned | live and open | planned 3 Sep from the CLAUDE.md restructure; no lane yet | stays |
| #263 | Planned | live and open | planned 3 Sep; sequenced after #235 folds, which it has; #223 is its older twin | stays |
| #264 | Backlog | live and open | a suggestion of 4 Apr (UTM attribution on LP buttons) that nothing later cites; on the plate until you say otherwise | stays |
| #265 | Backlog | live and open | a suggestion of 15 Apr (a mechanical validator for the analyst's measurement scaffold) that nothing later cites | stays |
| #267 | Backlog | live and open | the separate five-component app-promotion slice the ODAX plan named (docs/plans/done/2026-04-17-meta-odax-hardening.md); nothing built, no client asked | stays |
| #268 | Backlog | live and open | the ON_AD, MESSENGER and PHONE_CALL destinations the ODAX and conversion-matrix plans left for their own slices; nothing built | stays |
| #269 | Backlog | live and open | filed by the AM-chat parity plan of 20 Apr as a follow-on (a typed memo in AMContext); nothing later carries it | stays |
| #270 | Backlog | live and open | filed by the AM-chat parity plan of 20 Apr as a follow-on (memo injection into the four surgical-update specialists); nothing later carries it | stays |
| #271 | Backlog | live and open | half shipped: its head records supersession-by-declaration delivered 2 Sep; the recency half stays open | stays |
| #273 | Backlog | live and open | a standing register, not a slice: the claims log the marketing-site plans write to (last extended 2 Sep by the new site's review) | stays |
| #274 | Backlog | live and open | a suggestion of 26 Apr (a Playwright runtime pass over the hybrid LP) that nothing later cites | stays |
| #275 | Backlog | live and open | its head says future slice, owner action required (the Conversions API token); nothing later cites it | stays |
| #276 | Backlog | live and open | still true in the code: hosted_form.py falls back to the legacy single-nonce shape (lines 1553 and 1733 on 2026-09-04) | stays |
| #277 | Backlog | live and open | still true in the code: the trust-signal slot is emitted hidden and empty (_base.py:264, hosted_form.py:1898) | stays |
| #278 | Backlog | live and open | the session-intent-read plan of 28 Aug judged it adjacent and scoring by nothing; no plan | stays |
| #279 | Backlog | live and open | deferred UX polish at the cascade plan's close (the team working in real time); the build-progress reveal of 1 Sep covers builds, not cascades | stays |
| #280 | Backlog | live and open | a suggestion of 28 Apr (the app's consent banner) that nothing later cites | stays |
| #282 | Backlog | live and open | five browser add-ons as separate ad-pattern integrations, filed by the conversion-matrix plan; nothing built | stays |
| #283 | Backlog | live and open | a suggestion of 29 Apr (a sweep for chat-state-versus-UI erosion) that nothing later cites | stays |
| #284 | Backlog | live and open | H2 and H8 recorded as continued deferral by the LP overhaul (docs/plans/done/2026-06-07-lp-top-1pct-overhaul.md, step 4: heavy infra) | stays |
| #287 | Backlog | live and open | gated on the falsifying test's signal (its head); no plan | stays |
| #289 | Backlog | live and open | not yet planned (its head); extend deviation surfacing to two more fields; nothing later cites it | stays |
| #290 | Backlog | live and open | defer-and-reassess (its head): fires only if the race fix did not hide the noise; no plan | stays |
| #291 | Backlog | live and open | not yet planned (its head); the pen now lays type over pictures instead of painting it (#237), which changes the question | stays |
| #292 | Backlog | live and open | not yet planned (its head); no plan | stays |
| #293 | Backlog | live and open | an intent-bearing call deferred to you (its head); no plan | stays |
| #295 | Backlog | live and open | not yet planned (its head); no plan | stays |
| #296 | Backlog | live and open | kept as an image-dedup backstop by the LP overhaul, to re-evaluate after the Critic ships; the Critic has shipped | stays |
| #298 | Backlog | live and open | deferred (its head): blocked on a prerequisite that does not exist, a client connecting real customer data | stays |
| #299 | Backlog | live and open | still true in the code: submit_hosted_form sits in api/routes/tracking.py, 1058 lines on 2026-09-04 | stays |
| #300 | Backlog | live and open | two money-figure pairings enforced two ways, from the grounded-conversion-value plan's close; no plan | stays |
| #301 | Backlog | live and open | an owner-agreed split-out of the avatar-first niche slice (its head); no plan | stays |
| #303 | Backlog | live and open | revisit only if the traffic mix shifts (its head); no plan | stays |
| #304 | Backlog | live and open | a suggestion of 10 Jun (a dynamic one-shot form challenge) that nothing later cites | stays |
| #305 | Backlog | live and open | a regenerate affordance for failed follow-up sheets; only the drip-recovery suggestion cites it; no plan | stays |
| #306 | Backlog | live and open | gated on evidence, do not build speculatively (its head) | stays |
| #308 | Backlog | live and open | deferred future work, scoped out of situational reasoning as speculative (its head) | stays |
| #309 | Backlog | live and open | deferred to the decision-gate slice that builds the action-surface registry; no such slice is archived | stays |
| #311 | Backlog | live and open | gated on evidence, build when production shows a fabricated situational claim (its head) | stays |
| #312 | Backlog | live and open | the hero-image plan took its hero item; per-concept exception isolation in the LP stage is not on record as built | stays |
| #314 | Backlog | live and open | its seat is in the model-slot program with the trigger recorded: build the keyword_viability battery when Google spend justifies | stays |
| #315 | Backlog | live and open | probe-gated (its head): spun out of the citation-rescue slice; your decision on the attribution risk | stays |
| #316 | Backlog | live and open | future-sliced by you at the flywheel-reasoning plan's close (docs/plans/done/2026-06-17-flywheel-outcome-grounded-reasoning.md) | stays |
| #317 | Backlog | live and open | captured during the email-sequence activation slice; a resume capability nobody has asked for yet | stays |
| #318 | Backlog | live and open | phase 2e of the flywheel steering slice, deferred as a fast-follow; no plan | stays |
| #320 | Backlog | live and open | an HR brand leak on partner consent screens; no plan | stays |
| #321 | Backlog | live and open | the COGS plan made metered AI cost contractual (7 Aug); billed-versus-computed reconciliation itself is unbuilt | stays |
| #322 | Backlog | live and open | a program question (partner staff running campaigns for their customers); the term-sheet research cites it; no plan | stays |
| #323 | Backlog | live and open | English-substring guards on localized fields since the localize-by-default flip; no plan | stays |
| #324 | Backlog | live and open | the verify-financials form authored by the analysis; no plan | stays |
| #325 | Backlog | live and open | null tolerance beyond the AM emission tree; no plan | stays |
| #326 | Backlog | live and open | still true in the code: no query-key factory exists in frontend/src on 2026-09-04 | stays |
| #327 | Backlog | live and open | a ratchet for nested-shape skeletons in prompt OUTPUT blocks; no plan | stays |
| #329 | Backlog | live and open | a machine-readable recovery hint on connect-flow errors; no plan | stays |
| #331 | Backlog | live and open | carried by the Search authority program (#144), which waits on your four rulings; its posture stands (docs/plans/done/2026-08-07-direction-authority-slice-b.md) | stays |
| #332 | Backlog | live and open | open (its head): partner pages hostnames are CORS-blocked from the public LP endpoints; no plan | stays |
| #334 | Backlog | live and open | the page-meta coverage ratchet holds that every page calls usePageMeta; the Home-row mirror it asks for is unbuilt | stays |
| #335 | Backlog | live and open | open (its head): the promise floor is word math on a meaning question; no plan | stays |
| #336 | Backlog | live and open | the grandfathered-leak baseline still holds in tests/ratchets/test_no_session_history_in_intelligence_docstrings.py; the sweep is unbuilt | stays |
| #337 | Backlog | live and open | a mid-step transient re-runs the LP specialist against its own output; no plan | stays |
| #338 | Backlog | live and open | parked with a trigger (its head): a behavioral discriminator for the visible-reporting scanner class | stays |
| #340 | Backlog | live and open | filed by the acceptance-read plan (docs/plans/done/2026-08-14-the-acceptance-read.md) for the universal seam; no plan | stays |
| #341 | Backlog | live and open | filed with its trigger by docs/plans/done/2026-08-15-the-gate-serves-the-copy.md; no plan | stays |
| #342 | Backlog | live and open | account-level conversion history for the fireable-event guard; no plan | stays |
| #344 | Backlog | live and open | persist the full candidate pool at the four selector seams; no plan | stays |
| #345 | Backlog | live and open | two follow-ups from the client-photo review (the stamp seam bypass, a thumbnail primitive); no plan | stays |
| #346 | Backlog | live and open | still true in the code: frontend/tsconfig.app.json excludes the test files on 2026-09-04 | stays |
| #348 | Backlog | live and open | new scope (its head): widen the ty commit gate to unresolved-reference, with prerequisite cleanup; no plan | stays |
| #350 | Backlog | live and open | outcome rows carrying their booking's event reference; filed from the measured-show-rate plan's deviation; no plan | stays |
| #351 | Backlog | live and open | the mechanism half of partner invisibility (a post-build shell-transform ratchet); the policy half shipped | stays |
| #352 | Backlog | live and open | the iterated campaign's build seeing the source winner's pixels; the strangerhood census cites it; no plan | stays |
| #353 | Backlog | live and open | filed at the walk-in-door close: folding deposit actions into the cockpit owes a comp pass | stays |
| #354 | Backlog | live and open | declined with a promotion trigger by the owner-weekly-list plan (two drill-in figures the payback read carries no field for) | stays |
| #355 | Backlog | live and open | filed by the envelope-total plan: a budget-raise door in chat and the iterate room's blindness to the account | stays |
| #356 | Backlog | live and open | the margin's standing confirm on the Payback tab; no plan | stays |
| #357 | Backlog | live and open | the payment-strike surface the error lane's void waits for (docs/plans/done/2026-08-29-t2g-ws-b11-hr-own-t2g.md); an operator reaches the void by script until it lands | stays |
| #358 | Backlog | live and open | the specification shipped with the-machine-runs-its-own-gates (30 Aug); the deletion machine itself is deliberately unbuilt | stays |
| #359 | Backlog | live and open | declined for cost with the trigger that reopens it (its head) | stays |
| #360 | Backlog | live and open | its Critical 3 shipped as #173 (Google moves survive becoming proposals); Critical 2, rate limits collapsing to one bucket behind the proxy, still waits | stays |
| #361 | Backlog | live and open | unmocked lib/api modules fail soft in component tests; no plan | stays |
| #362 | Backlog | live and open | a standing rule now: the new marketing site's plan says it governs any testimonial that lands on the pages | stays |
| #363 | Backlog | live and open | a backbrief where nothing landed wears a Done chip; filed by the chat-apply plan; no plan | stays |
| #364 | Backlog | live and open | the audit's row 8 was closed by #228; the false lock claim and the reach-class forks stay open | stays |
| #365 | Backlog | live and open | your fork filed by #213 (its WATCH names it): a notice at the activation click when a direction runs past the month | stays |
| #366 | Backlog | live and open | the declared exception of the money floor plan: the two flywheel orchestrators still speak minor units | stays |
| #367 | Backlog | live and open | upsell sequencing and pricing psychology, the Hormozi gaps the coverage audit left; no plan | stays |
| #368 | Backlog | live and open | residuals of the instant-forms slice audit; no plan | stays |
| #369 | Backlog | live and open | filed by the spine-of-the-brief plan as the mechanical close of the edit seam; no plan | stays |
| #370 | Backlog | live and open | partly: the downstream partial now names the world (the spine plan's stance 8); the media buyer and the visual room are not taught to reason with it | stays |
| #373 | Backlog | live and open | an owner gate item, a model-slot change (its head); no plan | stays |
| #374 | Backlog | live and open | still true in the code: the raw-button ratchet matches /<button[\s>]/ line by line on 2026-09-04 | stays |
| #375 | Backlog | live and open | filed during #217's review: a text-only reply to a paste escapes the ledger; no plan | stays |
| #376 | Backlog | live and open | dormant with the corpus-maturity gate (its head); wakes at its first signed pattern | stays |
| #377 | Backlog | live and open | filed by #246's review: the forbid-model remainder of the annotation-key drop; no plan | stays |
| #378 | Backlog | live and open | seventeen DNS pastes per partner; no plan | stays |
| #379 | Backlog | live and open | filed by #239's review: the ledger cannot tell two templates apart on one slot; no plan | stays |
| #380 | Backlog | live and open | filed at #237's close as out of scope (size, position and scrim controls for the type); no plan | stays |
| #381 | Backlog | live and open | still true in the code: ALLOWED_SILENT_FALLBACKS is keyed by (path, line) on 2026-09-04 | stays |
| #382 | Backlog | live and open | no Microsoft integration exists; the meeting-medium plan records it as a future provider | stays |
| #383 | Backlog | live and open | arrived 4 Sep from the pen's role-play walk; no plan | stays |
| #384 | Backlog | live and open | arrived 4 Sep from #237's fifth review round; five production rows fail validation; no plan | stays |
| #385 | Backlog | live and open | arrived 4 Sep from #237's review; still true in the code (api/routes/chat.py spells the lookup at lines 287 and 312) | stays |
| #386 | Backlog | live and open | arrived 4 Sep from #237's review; no plan | stays |

### The edit for Hello Revenue (coordinating session, on that repository's `develop`)

Four shipped cards stay doubted because their archived plan names no card; a `**Card:** #N` line on the plan's second line relinks each on the board's next read of the corpus, and the doubt clears by itself (the relink from done/ is ruling 7). Add:

- `the plan archived 3 Sep whose card is #228` — `**Card:** #228.`
- `docs/plans/done/2026-09-03-the-board-stops-asking-and-starts-listening.md` — `**Card:** #249.`
- `docs/plans/done/2026-09-03-needle-board-on-omarchy.md` — `**Card:** #244.`
- `docs/plans/done/2026-09-01-the-board-clears-its-own-disagreements.md` — `**Card:** #189.`

Until then, accepting their "stays" verdicts re-places them by the owner's hand (ruling 4), which also clears the doubt.

Three suggestions were never archived when the plans that carried them shipped, so the moment the relink moved #210, #238 and #239 onto their plans, the corpus read birthed the orphaned suggestions as cards #388, #389 and #390 (14:21 UTC, the first read after the restart). Their verdicts say so and send them to Done; the corpus edit that ends it is the archive ritual on each: `uv run python scripts/archive_docs.py <the suggestion>` on each of the three, whose paths are the citations on cards #388, #389 and #390.

## Estimate

Execution clock: one lane-day, most of it reading the corpus. Actual: one session, 2026-09-04, about three hours, of which the corpus read and the 194 verdicts were a little over one. Gate clock: the owner's sittings over the lens, which is the point.
