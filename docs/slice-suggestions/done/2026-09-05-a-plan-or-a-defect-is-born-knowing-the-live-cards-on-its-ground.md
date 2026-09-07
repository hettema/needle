# A plan or a defect is born knowing the live cards on its ground, so the board never holds two plans for one thing

**Carried by:** docs/plans/2026-09-07-typing-an-idea-tells-you-when-it-is-already-a-card-overlaps-one-or-contradicts-one.md — planned on 2026-09-07 at the owner's word in the second door conversation ("can you not write the plan? You have context"), with a cold read of another make folded into the suggestion first

**Kind:** defect
**Fix:** now — the intent is written (Needle's `CLAUDE.md`: one way to do each thing, and a new primitive is born after a search for the existing one; HOW-WE-WORK §3: two ways is failed alignment; `docs/INTENT.md`: the board executes plans, which it cannot when the plans are a mess); the fix stays inside the corpus read and the briefs the board hands out; it removes the class — every document born blind to its neighbours, on every project — not the twelve found tonight.
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation 6b683c8b): "I'm worried we're trying to solve the same thing in similar ways which goes against our working doctrine. I guess it's a side effect of moving very fast. My intent is for the board to be clean and well organised with cards that smell of planning drift either folded or aware of each other … The intent of the board is to execute plans smartly. When the plans themselves become a mess that intent becomes impossible." And again by the owner, from the board's Idea door on 2026-09-07 (conversation 206dd83f), at the same door, not knowing this card existed: "I feel like when I enter a card to any needle board I don't have full understanding of the open cards in that project. What if I suggest a plan it has massive overlap with another plan? Is that a bad thing? I'm for example concerned about me contradicting myself."

## Observation

On the evening of 2026-09-05 Needle's own board held eight cards in Planned
and Up next and twenty-four in Backlog. Read together rather than one at a
time, twelve of them were four things:

| One mechanism | Written as | Named each other? |
| --- | --- | --- |
| The close door's grammar (`needle close`, `board/signals.py`, the brief) | plan 16, plan 14, #67, #40 | 15 named 14; nobody else named anyone |
| What the lane loop remembers about how a lane ended (`api/loops.py`, `board/lane.py`) | #31, #32, #33, #68 | none |
| Whether the doctrine text got worse | #64, plan 60's loop | none |
| A card follows its document (`board/reconcile.py`) | plan 08 item 1, #37, #61 | none |

Two plans that did name each other did so by plan number without a `#`
("after 11 … and after 08"; "after 12 … and 13"), which the board reads as
prose, so no hold held. Two cards on Planned read the opposite of their
plan, because the card kept the suggestion's birth title (#37, itself in the
cluster that would fix it).

Three writers made those documents, and none of them reads the corpus for
neighbours before writing:

1. **A lane's review files a third-ring finding as a suggestion** from
   inside one finding. The ring rule tells it to file, never to look; a lane
   that looked would be the scope creep the effort gate warns about, so it
   does the honest thing and files another card.
2. **The dial's planning session receives one defect and writes one plan.**
   Its brief carries that defect. A class of defects therefore becomes N
   plans, each claiming — truthfully, on its own — to remove a class.
3. **An Idea door conversation searches when the session thinks to.**
   Tonight's did, for the idea's words, and still filed #68 beside three
   live cards on the same loop, because the neighbours share its files and
   its functions, not its words.

The rule that would have caught it — a new primitive is born after a search
for the existing one, proof of search in the plan or the commit body — is
written for code and held by a ratchet for code. For documents it is a wish.
The board already knows how to read shared ground: it does it for lanes
(`board/collision.py`, "shares ground with #60" on three Planned cards
tonight). It reads nothing when a document lands.

### Found twice, 2026-09-07

Two days later the owner brought the same fear to the same door, and neither
he nor the door knew this card existed. The door is one text input that
shows him nothing, and its brief (`api/doors.py::idea_brief`) hands the
session his line and nothing about the live cards — it asks the session to
say when an idea is already in the corpus, and gives it nothing to say it
from. The session found this card by reading twenty-five titles by hand,
and a colleague of another make (Codex 0.153.4, read-only, two rounds,
2026-09-07) confirmed the reading and corrected three overstatements in it.
A door that cannot tell the owner his idea is already a card is this
defect, reproduced on the card that describes it. The second time is the
signal about the method (HOW-WE-WORK §9), and it says three things the
first finding did not:

**Two classes, not one.** *Shared ground* is two documents naming the same
files; the fold settles it and it is never a reason to wait (`docs/INTENT.md`
lesson 4), though it stays a cost both writers pay. *Contradiction* is two
intents that cannot both hold — two "done means" that cannot both be true,
or a new ask that reverses a ruling a live plan already carries — and two
documents can contradict while naming disjoint files, or share every file
and be compatible. A reading by paths (`board/collision.py`) sees the first
class and is blind to the second; shared words are a proxy just as partial,
since two wordings can carry incompatible intents. Only a colleague reading
the intents can judge compatibility; a search can retrieve the candidates,
never judge them. A changed intent is the owner's to change (§1); an
incompatibility nobody noticed is a defect in the board, not in him. So the
remedy is a fork put to him in one question he can answer cold — which
intent stands — never a refusal at the door.

**Retrieving and comparing the open cards is execution; choosing between
two intents is his.** The owner asked whether he should know every open
card before he types. He should not have to: the board is the team's memory
(§11), and finding the neighbours and reading them against his idea is the
colleague's work (§1). What is his is the choice when two intents the record
does not settle collide, and he can make it only with the comparison in
front of him. So the door session is the one that must be handed the
neighbours rather than search for them when it thinks to, and the
comparison comes before any commitment to the corpus.

**Two stages, two reads.** His opening line and the document the
conversation then writes are different things. The birth read of item 1
reads the document once it lands; the opening line is read by the door
session before it writes anything, with the neighbours in its brief. A
document born at the Idea door often names no files, so the birth read
needs the words as well as the paths to find its candidates.

## What would hold it

1. **The board reads a document's ground at birth, by paths and by words.**
   The paths its Terrain names and the code paths its text names, read
   against every live document's, land as one row on the card naming the
   neighbours and the files they share — the "shares ground" reading lanes
   get, applied when a document lands, on every project. A document that
   names no files is read by its words instead — the title's and the
   intent's, against every live document's — and the row names the nearest
   as candidates, never as a verdict. The head counts live documents that
   share ground or words with a live neighbour and name no neighbour, the
   way it counts plans the board cannot read.
2. **Every brief that writes a document carries the neighbours, by intent.**
   The planning brief the dial hands out, the review's filing brief, the
   Idea and Discuss doors' first message: each carries the live documents on
   the same ground or the same words, with each one's intent line and its
   rulings, not only its files. A plan the dial writes for a defect carries
   or sequences each neighbour, or says in its head that it is whole without
   it — and the dial's planning brief hands the session every live defect on
   the same ground, so one plan for a class is the default and one plan per
   instance the exception. The reading that verifies a mark reads the
   neighbours too: a `now` on a document whose ground a live plan already
   covers is a `when` on that card, not a second `now`.
3. **The Idea door's first message names the neighbours and what each is
   to the idea, before anything is written.** With the neighbours in its
   brief, the session judges each one — already this idea under another name
   (with the card), compatible work on shared ground (named, never waited
   on), or a contradiction, two intents that cannot both hold, put to the
   owner as one question with what is true today, both outcomes, what turns
   on each, and a recommendation — and says so in its first message. Nothing
   at the door asks him to read the backlog first, and the comparison is
   shown after he has typed, never as a condition of typing.
4. **A Sequencing line that means a hold is one.** A line that names a plan
   the board cannot place — a plan number with no `#`, a card the board does
   not hold — gets a verdict line in the voice of an unreadable gate, so a
   hold the writer meant is never silently prose.
5. **A test on the fixture:** a suggestion born naming a file a live plan's
   Terrain names shows the row with the plan's card; a suggestion born
   naming no file but a live plan's words shows the row with that card as a
   candidate; a plan that carries it clears the row; a plan whose Sequencing
   names a number the board cannot place shows the verdict line; and the
   door's brief fixture carries a live neighbour's intent line, so a first
   message that names no neighbour when one exists is a brief not read, not
   a brief not given.

Acceptance for the second class, in words a reader can test against a
door's reply or a plan's head:

- Two requested outcomes that cannot both hold, in documents whose files
  differ: the reply names the live card and the conflict before proposing
  any commitment to the corpus.
- Compatible work that shares files: the reply names the shared work, and
  neither invents a conflict of intent nor asks for a wait on that overlap
  alone.
- Two competing intents the existing rulings do not resolve: the reply asks
  one question — today's commitment, both outcomes, what each costs, and its
  recommendation — and writes no plan that picked one.

## Rejected

- **Refusing a birth.** A lane filing mid-review must land; the corpus is the
  only way in, and a refusal there is a suggestion lost. The neighbour is
  shown, and the writer folds or sequences.
- **Inferring a fold from terrain.** Ruling 3 of the many-lanes plan: terrain
  inference is the lock under another name. Shared ground is shown, never
  enforced; which documents are one thing is a judgment the writer makes with
  the neighbours in front of it.
- **A search step the writer is asked to remember.** That is the rule that
  failed tonight, twelve times — and again on 2026-09-07, on this card.
- **The open cards listed beside the Idea door, for the owner to read
  first.** That makes the door a reading task and hands him the retrieval;
  the board should make his not knowing safe, not cure it.
- **A new suggestion for the 2026-09-07 finding.** It would be the
  thirteenth document born blind beside the twelve above, on the very
  class; the second finding sharpens this card instead.
- **A plan written from the 2026-09-07 door conversation.** One home for
  the problem either way, but the dial's planning session derives a plan's
  done means from the suggestion and adds no scope, and a plan written at
  the door skips the independent reading of the mark. So the acceptance is
  fixed here first, and the plan follows the one way: this card is marked
  `now`, no reading has verified it and Needle's dial is off (2026-09-07),
  so it moves when the dial is turned or its Plan door is opened — and
  Needle's own planning waits while lanes are live, by the dial's rule.

## Loop

We think comparing intents before any commitment to the corpus — the
neighbours by intent in every writing brief, the birth read by words as well
as paths — will end unnoticed conflicts between documents, because file
overlap cannot establish compatibility and every one of the twelve was
written by a session that would have read a row had one existed; the
2026-09-07 door conversation caught this card only by a hand search its
brief could have spared it. At acceptance the three cases above are tested
on the fixture. After the first ten documents born after the fold across the
boards, and every Idea door conversation in that window, a reader of
another make checks each source's intent against the reply it got and the
commitment that followed, and counts three things: conflicts missed,
conflicts invented, and choices between intents made silently for the owner.
One occurrence of any fails the thesis: the retrieval or the judgment that
produced it is corrected, the three cases are re-run, and the next ten
births are read. A document that names its neighbour while both keep
incompatible promises counts as a miss, though the loop as first written
would have counted it as success. If the ten births show no real conflict
at all, the live effect is unproven and this stays a belief, reported as
one. If a door birth shows no neighbour and a reader finds one by hand, the
words read are too narrow and widen.
