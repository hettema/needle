# The doctrine, walked as its readers would read it

**For:** Dennis. **From:** two colleagues of different makes — Claude (the lane
on card #54) and Sol (a Codex session), each reading independently first, then
reconciling, with every disagreement kept visible.
**The question you asked:** *"The doctrine isn't about tech, it's about
collaboration, alignment and iteration. If we nail that, it doesn't matter what
we work on as a team — tech, marketing, art. Does the intent of our operating
doctrine hold, and do individual deviations live with it correctly?"* And the
tension you named: *"collaborate on anything"* against *"collaborate on
development projects together."*
**The surface walked:** `docs/HOW-WE-WORK.md` as it stands (193 lines, 13
sections, 2026-09-05), plus the twenty sentences the ruled table would add to it
(`docs/design/2026-09-05-the-two-texts-of-one-doctrine.md`, the *missing
portable doctrine* rows), read as a projection.
**Method:** Hello Revenue's role-play QA walk (`docs/patterns/prompt-template-pattern.md`
§ The Role-Play QA Rule), applied to the constitution instead of a prompt.
**Read scope: full assembled surface** — every section in order, not the
sections the question seemed to touch. **RELAY:** you and a session *produce*
the text, on a card; every session of every make on every project *consumes* it
at session start; the stance ratchet (item 4) and the review record *judge* it.
**Consumers impersonated:** (1) a Claude session opening cold on a new software
project; (2) a colleague of another make, without Claude Code's mechanisms;
(3) a colleague on a marketing or art project put on Needle — the reader this
document has never had. **Motivating scenario:** that third reader's first
session. **Boundary that must not change:** a project's own legitimate
specifics — Hello Revenue's twelve intents, Needle's typed edges — survive; a
doctrine that swallowed them would be a defect too.

---

## 1. Claude's reading — written before Sol's, unedited after

### The head answers the question before the walk starts

Line 6: *"This is a way of building software with one person and many AI
sessions."* The document declares its own scope as software in its first
sentence of substance. Whatever the sections say, a marketing colleague reading
the head is told this is not for them. **The tension you named is not between
sections; it is in the head, and the head is the one place a reader decides
whether to keep reading.**

### Section by section, through the lens

For each section: is it about collaboration, alignment or iteration
(**doctrine**, readable by anyone), or about building software (**method**,
readable by a developer)? And §2's own test — ask *why* of the rule; if the
answer is more durable than the rule, the rule is a method.

| § | title | reads as | the *why* underneath | a marketing colleague could obey it? |
| --- | --- | --- | --- | --- |
| 1 | Two kinds of decisions | **doctrine** | the person sees what the session cannot, and vice versa | yes — one phrase ("sees the code, the machine") is an example, not a rule |
| 2 | Intent over orders | **doctrine** | rules written as outcomes survive a change of method | yes |
| 3 | A session's economics are inverted | **doctrine** | a session's shortcut is read as a pattern by the next | yes — "TODO", "a later slice" are developer examples of a general truth |
| 4 | Only what is written survives | **doctrine, one method inside** | a session's memory vanishes | yes — except "every commit has a body", which is git; the intent is *every change says what prompted it* |
| 5 | Convention is the weakest defence | **doctrine, developer examples** | a boundary held by memory erodes | yes — "a test, a refusal at a door" are code; a checklist a tool refuses to skip is the same rule in marketing |
| 6 | Completeness is a claim only the session can check | **doctrine** | the person cannot read the work to find out | yes |
| 7 | We live in iterations, and a loop is a thesis | **doctrine** | closing the effects gap is what makes work compound | yes — this is the heart of "get better faster together" and reads as such |
| 8 | The corpus is the way in | **the instrument's contract** | work is written before it is done | yes *on Needle*: plans, suggestions, `now`/`when`/`his` are Needle's grammar, which the head says to adopt with the document ("adopt both or neither") |
| 9 | The board is the team's memory | **the instrument's contract** | a board moved by hand lies while the person is away | yes on Needle |
| 10 | Execution takes a lane | **method, entire** | hands on the same work do not trample each other; nothing lands unreviewed or broken | **no** — worktree, branch, fold, fast-forward push, suite green, stable branch: every noun is git |
| 11 | Nothing is done without a review | **mixed** | a second reading finds what the first could not; the ring decides who fixes | partly — the passes and the three rings are collaboration; "code-shipping slice", "file and line", "concurrency" are software |
| 12 | The close ritual | **mixed** | a shipped plan leaves no loose ends and no lie | partly — "every promise gets a stance, met or deviated" is doctrine; "folded", "stable branch is level", "the lane is removed" are git |
| 13 | Raise the standard | **doctrine** | the second failure is about the method | yes |

**Count:** eight sections are doctrine anyone can obey (§1–7, §13); two are the
instrument's contract and travel with Needle (§8–9); three are software method
carrying a doctrine sentence each (§10–12). The document is **about
collaboration, alignment and iteration for eight sections of thirteen, and it
says it is about software in its head.**

### The twenty additions, through the same lens

Seventeen of the twenty proposed sentences are about collaboration and pass for
any reader: the two kinds of decision, the guard on substituting one's own goal,
the brake on philosophising, handing work out and checking a claim, the loop
rules, the self-judgment hazard, don't settle for probably, investigate within
scope and ask before the irreversible, assertion without a check.

Three carry a developer's example or are developer-only:

- **27e** — "re-run the failing test it reports" is an example inside a rule
  (*verify what the action rests on*) that holds anywhere. Keep; the example
  can stand.
- **56a** — "rehearse destructive work on a fixture before running it on real
  data" is true of a mail-merge as of a migration. Keep.
- **56b** — "a tool that matches on process or command text can match the
  session's own command" is only ever true of someone writing shell tooling.
  Under the "anything" lens this is a method example, not doctrine; Codex
  moved it *into* the doctrine in the challenge round, and under this lens I
  would move it back out — or into §5 as an example, not a rule. **Flagged for
  Sol.**

### The tension, and the three ways to resolve it

You said *"collaborate on anything"* may be in tension with *"collaborate on
development projects together"*, and that "anything" might be a future card.
The walk says the tension is real and has a location: the head (line 6) and
§10–12. Three honest ways to resolve it, none of them mine to pick:

**A. Keep the scope as software.** The head stays; §10–12 stay; the table's
edits land. "Anything" is a future card. Cheapest. The cost: a marketing
project on Needle reads a document that says, in its first sentence, that it is
not for them — and the eight sections that *are* for them go unread.

**B. Widen the scope now, on this card.** Rewrite the head; rewrite §10–12 as
intents with the git method named as *today's way for code*. The document
becomes what you described. The cost: this lane grows by a rewrite of three
sections you would have to rule word by word, and the table's sixty rows were
already a full reading.

**C. Widen by one sentence, and let the stance lines carry the rest.** This is
the one I would recommend, and it borrows the table's own row 1b. Row 1b
resolves the *make* problem in one sentence: *where this document names a
mechanism, it names one colleague's; a colleague without it holds itself to the
same rule and says which mechanism it lacked.* The *domain* problem has the same
shape and takes the same sentence:

> Where this document names a method — a worktree, a suite, a fold, a review of
> code — it names today's way for software; a project of another kind holds
> itself to the same intent and says which method it lacks.

With that sentence at the head, and the head's "a way of building software"
changed to "a way of working" (your words, your call), §10–12 can stay as
written *for now* and are honest: they are the current method for code, and the
sentence says so. Item 4's stance lines then do the bookkeeping this plan already
builds: §10, §11 and §12 each get a line saying what holds them, and the
rewrite-as-intent becomes a debt line — `*Undefended until:* #<card> by <date>`
— which is a card on your board that you rank, not a rewrite I do in a lane
you did not gate for it.

Why C over B: it lands the intent you stated *today*, in one sentence you can
read, without a rewrite that would need sixty more rows. Why C over A: A leaves
the head saying the opposite of what you just told me the doctrine is for.

### What a marketing colleague would actually hit — the motivating scenario walked

Session one on a marketing project. The colleague reads the head: "a way of
building software." Stops, or reads on with the assumption that half of it does
not apply. Reaches §8: is told to write a plan with an effort gate and a "done
means" — fine, Needle's grammar, and Needle is the board they are on. Reaches
§10: "runs in an isolated worktree on a short-lived branch … folds by a
fast-forward push to the trunk when its suite is green." Has no worktree, no
trunk, no suite. Under option A, they invent something or skip it; under C,
they read the head's sentence and say: *"no suite exists for a campaign brief;
the equivalent intent — nothing lands unreviewed — is held by the review
record."* That is the deviation "living with it correctly," and it is exactly
the sentence you asked for.

### The boundary that must not change — walked

Hello Revenue's twelve quality intents and its `scripts/method_register.py`;
Needle's typed edges and "the board never runs." Under A, B and C alike these
stay in the project files; row 3b's sentence ("this document holds what is true
in every session, on every project; a project's own file holds the rest") is
the line that protects them. Where I would watch: a project file that *restates*
a doctrine section in its own words is drift, and Hello Revenue's CLAUDE.md does
some of that. That is a card of its own (each project's file read against
HOW-WE-WORK), not this one, and I am filing it as a suggestion.

---

## 2. Sol's reading — written independently, before reading section 1, unedited

*Run as `codex exec -s read-only` from the main checkout, where section 1 was not
yet on disk; the prompt named the walk document and forbade reading it. Sol's
own read-scope line is the last line below. Codex thread
`01a07211-744c-7cd3-a9aa-d0ac744b54d7`.*

My recommendation: widen the doctrine now, but do not pretend every current section is universal. Split the one source into a universal operating doctrine and an explicitly labelled Needle execution profile. “One true doctrine” should mean one authority, not one undifferentiated set of rules.

### 1. All thirteen sections

1. **Two kinds of decisions** — Doctrine, but software nouns at lines 15–18 and “technical” at 25 unnecessarily narrow a universal alignment rule.
2. **Intent over orders** — Doctrine. Fully portable.
3. **A session’s economics** — Doctrine about AI labour, expressed through developer examples. “One way” is a method whose durable intent is preventing pattern drift.
4. **Only what is written survives** — Mixed. Durable doctrine through line 60; commits, plans, and closes at 61–63 are Needle/software methods.
5. **Convention is the weakest defence** — Doctrine. Tests and doors are examples, not its scope.
6. **Completeness** — Doctrine, except “cannot read the code” at line 79 falsely specializes the person’s information asymmetry.
7. **Iterations and loops** — Doctrine. Lines 105–108 are a current measurement method and should be labelled as such.
8. **The corpus is the way in** — Mostly Needle operating method. The durable doctrine is: work is externalized before execution; status has one authoritative representation; ownership and acceptance are explicit.
9. **The board is the team’s memory** — Mixed. Authority over prioritization and evidence-backed state are doctrine; columns, cards, and automatic moves are Needle’s method.
10. **Execution takes a lane** — Software/Needle method. Its portable intent is isolated concurrent execution, visible overlap, and integration only after applicable verification.
11. **Review is a loop** — Mixed. Iterative review, three rings, and a clean re-read are doctrine; “code-shipping,” file-and-line findings, concurrency/restart, and fixes landing are software forms.
12. **The close ritual** — Needle/software method. Its durable doctrine is that every promise receives an evidenced stance and interrupted closure cannot manufacture a false “done.”
13. **Raise the standard** — Doctrine. Fully portable.

### 2. The twenty additions

| Row | Judgment under “anything” | Action |
|---|---|---|
| 1b | Portable mechanism-fallback rule | Add, but say “capability” rather than enumerating Claude mechanisms. |
| 3b | Essential layering doctrine | Add. This protects project-specific intent. |
| 12 | Portable alignment doctrine | Add. |
| 19 | Portable brake on intent theatre | Add. |
| 26c | Delegation method, not universal doctrine | Move to the Needle execution profile; it is false when delegation is unavailable or unauthorized. |
| 27a | Developer-heavy delegation method | Move and generalize examples; code search, suites, logs, and ratchets are not the doctrine. |
| 27d | Portable judgment boundary | Add, replacing “what to build” with “what outcome to pursue.” |
| 27e | Portable verification doctrine | Add. |
| 27f | Planning method | Move to the Needle profile. Durable rule: delegation is chosen deliberately before execution. |
| 31b | Portable iteration ownership | Add. |
| 31c | Portable cadence doctrine | Add. |
| 35b | Portable experimental reasoning | Add. |
| 38b | Portable loop prioritization | Add. |
| 40 | Portable protection against self-confirmation | Add. |
| 49b | Portable scope clarification with technical wording | Add, rewritten as “systems, settings, and working arrangements,” not “machine/config.” |
| 52 | Portable verification doctrine | Add. |
| 54 | Portable epistemic rule | Add. |
| 55 | Portable authority and reversibility rule | Add as revised. |
| 56a | Mixed | Add assertion/correction faithfully; generalize “fixture” to rehearsal in a safe representative setting. |
| 56b | Developer/Unix-specific safety rule | Move to a technical execution profile; do not elevate one process-matching trap into universal doctrine. |

The additions do not solve §§8–12. They improve the universal core while leaving the document’s execution half software-shaped.

### 3. The tension

Yes, directly.

The document declares itself a way of “building software” at lines 6–11 and repeatedly makes software the assumed world:

- Code, machine, and technical decisions: 15–18, 23–26
- Engineer/TODO framing: 45–54
- Code, commits, and plans: 59–63
- “Cannot read the code”: 78–83
- Repository grammar and board machinery: 112–131
- Worktrees, branches, suites, trunk: 144–153
- “Code-shipping,” file-and-line review, concurrency/restart: 155–166
- Stable branches and unmerged work: 168–177

Widen now. Dennis has already supplied the intent, and marketing/art are already motivating consumers; postponing the wording would knowingly publish a constitution that excludes work it is meant to govern.

The cost is substantive: §§8–12 need separation into durable intent plus an explicit Needle execution profile. Several software nouns elsewhere need generalization. This is more than changing “software” to “work”; that cosmetic edit would leave non-developers inventing half the operating system.

### 4. Marketing colleague’s first session

They encounter the exclusion before the first rule: lines 6–8 say this is for software. A conscientious reader stops treating it as binding; an accommodating one begins translating without authority.

- Lines 15–30: they invent a boundary between Dennis’s intent and their own craft judgment because the text offers only “technical.”
- Lines 45–54: they either map TODOs and duplicate implementations onto drafts/channels/assets, or dismiss §3 as engineering culture.
- Lines 58–63: “the what is in the code,” commit bodies, plans, and closes force them to invent where campaign rationale, rejected concepts, and final artifacts live.
- Lines 67–74: they can execute the principle, but must invent non-code mechanisms for claims, approvals, brand constraints, and provenance.
- Lines 78–83: “cannot read the code” does not describe their information asymmetry; they must infer the real rule is truthful completion reporting.
- Lines 85–108: this largely works. They can define conversion, recall, preference, or production signals, though taste judgments remain deliberately Dennis’s.
- Lines 112–131: they must either create suggestion/plan folders and adopt the exact `now`/`when`/`his` grammar, or silently skip it. Nothing says which details are mandatory Needle protocol and which are examples.
- Lines 135–142: the board behavior is executable if Needle supports their artifacts and signals.
- Lines 146–153: they stop. An art concept has no worktree, branch, green suite, trunk, or stable branch. They skip the section and invent no equivalent isolation/integration discipline.
- Lines 157–166: “code-shipping” tells them review does not apply. They risk losing the valuable review loop, boundary critique, and clean-pass requirement along with its developer form.
- Lines 170–177: they cannot perform the close ritual because folding, stable branches, and unmerged deletion have no stated equivalents. They either falsely close the card or invent an undocumented close.
- Lines 181–187: they rejoin the doctrine successfully.

The concrete failure is not confusion about values. It is that the first non-software colleague must author the missing marketing/art execution profile during their first task.

### 5. The boundary

Protect project-specific intent with an explicit three-layer rule:

1. Universal doctrine governs collaboration, authority, alignment, evidence, review, and iteration.
2. Needle’s execution profile says how Needle currently realizes it.
3. Each project owns its domain intents, quality boundaries, vocabulary, artifacts, and specialized methods.

A project may replace or specialize a method when it preserves the doctrine’s intent and records why. Universal doctrine must not define product quality. Review must explicitly test both layers: the work against universal operating doctrine and against the project’s own named boundaries.

That preserves Hello Revenue’s twelve quality intents and Needle’s typed edges: neither is competing doctrine; both are legitimate project truth. Row 3b is therefore necessary but insufficient unless it also states precedence and specialization explicitly.

**Read scope: full 193-line HOW-WE-WORK surface, the full Role-Play QA Rule supplied, and all twenty proposed missing-portable-doctrine rows in the design table; I did not read the prohibited doctrine-walk document.**

## 2b. Round two — Sol reads section 1 and attacks the reconciliation, unedited

*I had proposed a reconciled shape ("C′": one document, two labelled parts, each
method section led by its intent) and asked Sol to attack it on three points
before you saw it. Same thread, resumed warm.*

### 1. Agreement

We agree on the thirteen-section shape: §1–7 and §13 are doctrine; §8–9 are Needle’s instrument contract; §10–12 are software methods carrying portable intent. None of your rows is wrong. My qualifications remain: §1’s software nouns narrow rather than merely illustrate; §3’s “one way” is a method serving anti-drift; §9 contains portable authority principles inside the instrument; and §10’s exact portable intent is integration after applicable verification—“nothing lands unreviewed” belongs primarily to §11.

### 2. Challenge to C′

### (a) One file or two

C′ meets my non-cosmetic bar in one file. Separation must be semantic, not physical. Two clearly labelled parts preserve one injected authority and avoid the delivery failure of a second unread file.

One correction: Part II should not be titled simply “how we do it on Needle today.” Lines 146–177 describe how **software** runs on Needle, not how marketing or art does. Call §§8–9 the cross-domain Needle contract and §§10–12 “Needle’s software execution profile.” Otherwise the new label still overclaims universality.

### (b) Marketing walk under C′

At lines 146–153, the colleague now reads the portable intent first: isolate concurrent hands, expose overlap, integrate only after verification. They no longer skip the obligation. They still must invent the project’s concrete method, but under the precedence rule that invention is legitimate specialization rather than guesswork. The text must say where that specialization and its reason are recorded.

At lines 157–166, the lead sentence must explicitly say the review intent applies to **every completed slice**. If it only precedes the unchanged sentence “A code-shipping slice closes…,” marketing can still conclude the loop applies only to code. The remaining prose must be introduced as the software realization.

At lines 170–177, the evidenced-promise and no-false-close sentence prevents skipping. Again, “the following ritual is the software realization” must precede the git language.

So: the five intent sentences are enough to prevent stopping only if each establishes universal applicability and explicitly scopes the existing paragraph as the software method. The head must also require a non-software project to record its specialization. C′ need not supply a generic marketing workflow; that belongs to the project once real work reveals it.

### (c) What C′ could lose

Three risks:

- Part II could become a miscellaneous-method drawer. Row 56b is technical safety guidance, not Needle execution workflow; it belongs in the relevant technical profile, not automatically beside §§8–12.
- Combining §§8–9 with §§10–12 under one undifferentiated heading obscures that the former already govern every Needle project while the latter govern software.
- “May specialise” without naming where the specialization survives recreates the `/clear` failure. Require it in the project’s own durable instructions.

My earlier split and C′ otherwise converge in substance.

### 3. This card or the next

This card. The head, precedence rule, five intent sentences, and two-part organization repair a contradiction this card’s own full walk discovered. Deferring would knowingly publish “anything” doctrine whose software sections still contain no fallback intent; an `Undefended until` marker reports that defect but does not stop the next marketing colleague from hitting it.

Dennis’s added reading cost now is bounded: the head, two precedence sentences, five intent sentences, and the part labels. Deferring costs another card, another assembled-text reading, an interim false doctrine, and re-establishing the same context. A full domain-neutral rewrite of the software methods is not required here; clear intent-plus-labelled-method structure is.

### 4. Exact precedence rule

> This document holds the operating doctrine shared by every project; Needle’s execution profile records how Needle realizes it today, and each project’s own instructions hold its domain intents, quality boundaries, artifacts, and specialized methods. Where the layers differ, doctrine governs: a project may replace or specialize a method when it preserves the intent that method serves and records why, but neither the doctrine nor Needle’s profile may flatten the project’s own legitimate truth.

**Read this round: section 1 of the named walk document in full, plus C′ and the four questions in your message.**

---

## 3. Where we agree, where we do not, and what we recommend

### What the two rounds did

Two colleagues of different makes read the same 193 lines independently and
reached the same thirteen verdicts: **eight sections are doctrine anyone can
obey, two are Needle's contract, three are software method with a portable
intent inside them.** Neither of us changed a verdict on reading the other's.

Then each moved the other on something material. **Sol moved me off my own
recommendation.** I had proposed one sentence at the head (a domain fallback:
*a project of another kind holds itself to the same intent*) and stance lines to
carry the rest. Sol's walk of the marketing colleague at §10 and §12 showed the
hole: the fallback says "hold the same intent" and §10 states no intent — it is
method from its first word to its last. A fallback with nothing to fall back
to. **I moved Sol off a separate file.** Its first reading split the text into a
universal doctrine and a "Needle execution profile"; a second file is either a
second injected text (which this card's own door refuses) or a file nothing
injects, which reaches no session. Sol agreed: *"separation must be semantic,
not physical."*

You said this would be a test of the doctrine. Here is what it showed: two
independent reads converged on the facts in one round and on the remedy in two,
with each round's disagreement written down before it was resolved. The
different-make round on the table earlier today found the one rule I had
generalised dangerously (row 55); this round found the hole in my remedy. In
neither case would a second Claude session have been as likely to find it — the
disagreements were about what is true *of the reader's own make and domain*.

### The recommendation — one document, three labelled parts

Widen the scope **on this card**, not by rewriting §10–12 but by leading each
with its intent and labelling what follows as today's method for software. Sol
and I both recommend this card rather than the next: a debt line would *report*
the contradiction to the next marketing colleague without stopping them hitting
it, and the reading it costs you is bounded — the sentences below.

**The head.** Line 6 today: *"This is a way of building software with one person
and many AI sessions, and no other human in the loop."* Proposed:

> This is a way of working with one person and many AI colleagues, and no other
> human in the loop.

followed by the layering sentence the table already proposes (row 3b) and a
precedence rule, in Sol's words, which I adopt as written:

> This document holds the operating doctrine shared by every project; Needle's
> execution profile records how Needle realises it today, and each project's own
> instructions hold its domain intents, quality boundaries, artefacts and
> specialised methods. Where the layers differ, doctrine governs: a project may
> replace or specialise a method when it preserves the intent that method
> serves and records why, in its own instructions — but neither the doctrine
> nor Needle's profile may flatten the project's own legitimate truth.

**Three parts, labelled** (Sol's correction to my two: §8–9 already govern every
project on the board, §10–12 govern software, and one label over both would
overclaim):

| part | sections | reader |
| --- | --- | --- |
| **I — The doctrine** | §1–7, §13, and the portable additions | anyone who works with you |
| **II — Needle's contract** | §8–9 | every project on the board, whatever it makes |
| **III — Needle's software execution profile** | §10–12, and the four additions that are about delegating and shell tooling (26c, 27a, 27f, 56b) | a software project |

**Five intent sentences**, one leading each section of Parts II and III. Each
does two things Sol's second walk showed are both required: it states the intent
as applying to *every* completed piece of work, and it scopes the paragraph that
follows as the current method for software. Drawn from the sections' own words;
yours to keep or edit.

> **§8.** Work is written before it is done, and that writing is the one
> authoritative status. On Needle, the writing is the corpus below.

> **§9.** The person ranks and gates; every other move is a machine fact with
> named evidence, or the board lies while they are away. On Needle, the board
> below is how that is held.

> **§10.** Hands on the same work run apart, their overlap is visible, and
> nothing is integrated before the verification that applies to it. For
> software on Needle, that is the lane below. A project of another kind names
> its own method for this in its own instructions, and why.

> **§11.** Every completed slice is read again by a reader who was not its
> author, in passes until one finds nothing new, and the ring a finding falls in
> decides who fixes it. For software, the review below is the current form.

> **§12.** A shipped promise gets an evidenced stance — met, or deviated with a
> pointer — and an interrupted close can never read as done. For software on
> Needle, the ritual below is the current form.

**Six generalisation edits** Sol proposed and I accept — each changes your words,
so each is a row for you:

| where | today | proposed |
| --- | --- | --- |
| §1, lines 15–18, 25 | "sees the code, the machine"; "technical" | the colleague's craft judgment, whatever the craft |
| §6, line 79 | "cannot read the code to find out" | "cannot inspect the work directly" |
| table row 1b | an enumeration of Claude Code's mechanisms | "a capability" |
| table row 27d | "what to build" | "what outcome to pursue" |
| table row 49b | "the machine, the config" | "systems, settings and working arrangements" |
| table row 56a | "on a fixture" | "in a safe, representative setting" |

**What this does to the table.** Nothing to any stance. Four *missing portable
doctrine* rows (26c, 27a, 27f, 56b) land in Part III rather than Part I; the
table's "where it lands" column gains a part for them if you rule this way. I
have not edited the table — one ruling at a time, and both are yours.

**Cost to you.** One head sentence, one precedence rule, five intent sentences,
three part labels, six wording edits: seventeen decisions, beside the table's
seventy-five rows. Sol's estimate of the alternative: "another card, another
assembled-text reading, an interim false doctrine, and re-establishing the same
context."

### Where we still differ — both readings, neither marked correct

After two rounds, one point:

- **Where row 56b lives** ("a tool that matches on process text can match its
  own command"). Sol: it is technical safety guidance, not Needle execution
  workflow, and should not sit "automatically beside §8–12"; it belongs in "the
  relevant technical profile." Me: in a one-file world Part III *is* the
  technical profile, and a sentence with nowhere else to go goes there — or into
  §5 as an example of a boundary that needs a mechanism, which is where I first
  had it. One sentence; yours.

Everything else converged, and the record above shows where each of us gave
ground and why.

### What this does not do

It does not write a marketing or art execution profile. Sol said it best:
*"that belongs to the project once real work reveals it."* The precedence rule
tells such a project where to record its method and its reason, which is what
"individual deviations live with it correctly" means mechanically.

It does not read the project files. Hello Revenue's and Needle's own `CLAUDE.md`
against the one text is its own card, filed today as
`docs/slice-suggestions/2026-09-05-a-projects-own-file-holds-only-what-is-that-projects.md`,
marked `Fix: his`.

---

*Both Codex rounds ran as `codex exec -s read-only` — the reviewer form
`docs/codex-on-this-machine.md` prescribes — from the main checkout, thread
`01a07211-744c-7cd3-a9aa-d0ac744b54d7`. Sol wrote nothing; its words above are
its output, unedited. The session id you offered (`01a071ee-35f7…`) held a live
writer lock, so it was left alone rather than resumed beside itself.*
