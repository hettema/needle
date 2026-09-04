# The colour language

**Status:** PENDING
**Written:** 2026-09-04, from the owner's reading of the served board after cards #9, #16 and #17 landed: "I have literally no idea what all those pills mean and do. Colours should mean something." The proposal was drawn as a design canvas over today's feature set, revised three times on his notes, and signed the same evening. The comp is `docs/design/2026-09-04-the-colour-language/` (six artboards and their layout; the same canvas is at https://claude.ai/code/artifact/d1bb4c0b-72c0-4dd7-8d45-7e8dcd8da62a).
**Effort gate:** high — the comp settles every visual decision; the judgment is in holding one rule across every surface without exception, and in a page test that proves it. No new feature; every element in the comp exists on the board today.
**Sequencing:** independent of #20 (identity and the record) and of plan 10; touches only `frontend/` and the assemble step that names states. Shares the page with nothing running.

## Intent

The board can be read without being explained. Five colours mean five things and nothing else: amber is your move, red is broken, teal is live, green is proven, grey is quiet. A button is a shape, never a colour. Every collapsed card has one anatomy, every state sits in the same place in the same word, and a shipped card shows its loop as a glyph. The head is one line whose three words filter the board.

## The rule, stated once

| Colour | Means | Appears on |
|---|---|---|
| amber (`--attn`) | only you can act | a lane's question, a verdict to accept, a signal only you can read, Decision moment's cards |
| red (`--wrong`) | evidence is gone or two things disagree | a doubted status, a document nowhere, a lane that died, two running lanes in one file |
| teal (`--accent`) | happening right now | a lane with hands on, a conversation, a fold landing |
| green (`--landed`) | the loop closed | a signal read as delivered, Done, the trunk level |
| grey (`--ink-2/3`) | information with no claim on you | counts, ages, gates, kinds, what arrived, what is unplanned, a collision before Start |

Never: a count coloured for its size; a category coloured; a button coloured; a column coloured. The comp's `Colour.dc.html` is the sheet.

### 1. The head is one line, and its three words are filters
As `Head.dc.html`. Done means: the head is one line — wordmark, project pill with the corpus counts behind it, then `Your move N`, `Broken N`, `Live N` in their colours, the lens switch, the Idea box and door; clicking a word filters the board to those cards and shows the breakdown (verdicts, questions, signals, …) as sub-filters; clicking again clears; the quiet facts (arrived today, unplanned defects and ideas, trunk level) live behind the project pill, not on the head; nothing on the head ever renders as a bare number in a ring.

### 2. One card anatomy, every state
As `Card.dc.html` and `Main.dc.html`. Done means: number and gate on the first line with the kind right-aligned; title; one line of essence; a state line with one word in its colour bottom-left and the one door that state allows bottom-right; the border takes the state's colour only for live, asking you and broken; a collision before Start is a quiet state word ("collides with #N · waits"); doors are filled (primary) or outlined (secondary), never coloured; a gateless suggestion's door reads "Create plan"; the rank digit is gone (position is rank).

### 3. The loop is a glyph
Done means: a shipped card's state line leads with its loop — an open ring in ink with who reads it and when ("loop open · a session reads it 11 Sep"), or a filled green dot with the time and the verdict ("loop closed · read 14:54, delivered"); an owner-only signal's ring is amber; the glyph is at least 14 px and reads at column width.

### 4. The open card keeps its depth, and takes only the top of the comp
`OpenCard.dc.html` shows the top of the card — what it is, the state sentence in its colour under the title, the doors row with one filled primary and closed doors as one grey line saying when they open. Done means: that top lands exactly; everything below it (the brief, the record, carries, the plan, the doubt, the readings, the history) keeps every layer it has today, restyled only where the language demands (state words, door shapes, loop glyph). The owner ruled the rest of the open card is its own design run.

### 5. The triage lens says current → target
As `Triage.dc.html`. Done means: each line shows the card's current column and its destination with the destination in the meaning's colour; accept-all is a filled button per class where the evidence is uniform; the doubted class never has one.

### 6. A page test holds the language
Done means: a test renders one card per state and asserts, for each, the state word, its colour token, its border token and its door label against a table that is the rule above; a ratchet greps the page's components for any hard-coded colour outside the tokens; the design-system README carries the table.

## Terrain
- `frontend/src/components/ui/tokens.css` (the five semantic tokens already exist: attn, wrong, accent, landed, ink), `primitives.css`, `frontend/src/board/` (Board, the card faces, OpenCard's top, the attention rail, the triage lens), `board/assemble.py` (the state words and rail counts the page renders — one function names each state; the page never invents a word).
- The comp's artboards are static HTML with inline styles on the same tokens' values; lift spacing, sizes and weights from them exactly.

## Acceptance criteria
1. Open the served board: the head is one line; click Your move and only those cards remain, with sub-filters; click again and the board is back.
2. Every card in every column matches the anatomy; a scan of a column finds live, asking and broken by border alone; nothing else is coloured.
3. A shipped card shows its loop glyph legibly at column width; an owner-only signal's ring is amber.
4. The triage lens shows current → target on every line.
5. The page test and the ratchet are green, and the README carries the table.
6. The owner uses it for a day and says whether the board can be read without being explained. That verdict is this card's WATCH signal.

## Rulings
Recorded as the build makes them, each with the alternative rejected. The design rulings made on the canvas are in the comp's notes and in this plan's rule table.

## Estimate
Execution clock: one lane-day. Gate clock: the owner's day of use.
