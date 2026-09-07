# Every make sees a project's skills, and a called Codex colleague answers in the shape asked

**Status:** NEW — planned, not started.
**Written:** 2026-09-07, from Dennis at card #60's Discuss door, after the research on how Codex takes instructions: "Claude code (you) work with a harness that automatically reads claude.md etc. Codex has its own harness. What I want you to do is research how codex works and then find the way we optimise for codex's way of working as well. How does codex read instructions at startup, how does it do skills, what other tricks does it have that we're not utilising, etc." Then, on the recommendations: "I agree with your recs. And on the execution, why does this need cards? Feels like something we can just execute now or am I wrong? Is it big/risky?" It is neither; the card is the writing, and his agreement is the gate's confirmation.
**Effort gate:** medium — the code is three small seams (an idempotent link, a flag and a field, one pass in a review); the judgment is small and made here (one reader for both makes' answers; a relative link so a project stays portable), and the one failure that would be silent — a link laid into a project's tree that git sees as a change nobody commits — is what item 1 names.
**Sequencing:** none.

## Intent

A Codex session on a project on the board can do what the project's file
prescribes, because it sees the project's skills; and when Needle calls a
Codex colleague, its answer comes back in a shape the board can read, not a
first line guessed from prose. Both are one link and one flag away, and both
were left unused because nobody had read Codex's own harness.

## What the evidence settled (read live on 2026-09-07, Codex 0.153.4)

- **Codex scans `.agents/skills` from the start directory up to the
  repository root, follows symlinks, and reads the same `SKILL.md` shape
  Claude Code does** (the open agent-skills standard; OpenAI's skills page).
  A scratch repository with `.agents/skills -> /home/dennis/Work/hellorevenue/.claude/skills`
  gave a read-only `codex exec` all seven of Hello Revenue's skills by name,
  with `hr-plan-write`'s description quoted verbatim. Without the link the
  same session on Hello Revenue's root listed none of them and, asked what it
  would do with a rule whose method is a skill it cannot see, said it would
  search, refuse to substitute, and tell the owner — the doctrine's head
  paragraph working, and Hello Revenue's plan and UI methods unreachable.
- **Claude Code does not read `.agents/skills`** (its skills page names
  `~/.claude/skills`, `.claude/skills` and plugin skills only), so the link
  points from Codex's location at Claude's, and `.claude/skills` stays the
  one folder. Codex's `/import` copies a Claude setup into Codex's own
  folders; it is never used here, because a copy is a second text.
- **`codex exec --output-schema <file>` with `-o <file>` writes the final
  message as JSON that validates against the schema**, from Hello Revenue's
  root, first try: `{"answer": "# How we work", "how_known": "checked",
  "sources": [...]}`. `codex exec resume` accepts the same flag (its help,
  line 67), so a resumed worker can be held to it too.
- **What Needle reads of an answer today:** `runtime/calls.py::judge` takes
  the first non-blank line of the answer file as the verdict's words
  (`_first_line`), and `runtime/launch.py::_answered` only stats the file. No
  schema of any spelling exists anywhere in the repository (searched
  `output-schema`, `output_schema`, `schema` under runtime/, api/, board/,
  domain/ — the only schemas are the store's).
- **The installer is the place a project's carriers reach every make:**
  `api/board_cli.py::hook_install` (line 361) writes Needle's hook into a
  project's `.claude/settings.json`, idempotently, and arms git's hooks path;
  its test is `tests/api/test_cli.py:140`. `api/doors.py::plan_skill` reads
  `.claude/skills` to name a project's plan-writing skill on the Start door,
  and keeps reading that folder.

## Items

### 1. The installer lays the link, and the link is committed

`needle hook install <repo>` also lays `<repo>/.agents/skills` as a relative
symlink to `../.claude/skills` when that folder is a directory, so a clone at
another path keeps the link; a real directory already there is left alone and
named on stdout (a project already on the standard keeps its own); a link
pointing elsewhere is named, never replaced; and a second run changes nothing.
Then the lane runs the installer on every project the board registers
(`needle projects`) and commits the link into Hello Revenue's trunk by script,
the way card #60 committed its suggestion there — the link is Needle's
artefact in a project's tree, like the settings entries the installer already
writes, and an uncommitted one is the silent failure this item names. Where
to look: `hook_install` and its test; `runtime/git.py` for how the lane runs
git in another repository; the memory of card #60 for the docs-commit script.
Done means: on a fixture repository with `.claude/skills`, the installer
leaves `.agents/skills` resolving to it and says so; on one without, it lays
nothing and says nothing; a second run is a no-op; a read-only `codex exec`
from Hello Revenue's root lists its seven skills by name (the probe of
2026-09-07 is the method); the link is committed in Hello Revenue and the
commit names this card.

Hands out: execution — running the installer on each registered project and the Codex skill-list probe on Hello Revenue, by script, reported verbatim; verifies by reading each link's target and the probe's answer file before the item claims delivery.

**Met:** `tests/api/test_cli.py::test_hook_install_lays_the_codex_skills_link_once_and_leaves_a_projects_own_alone` holds the four cases (laid and said, silent without skills, a second run a no-op, a project's own directory or link left alone and named). Hello Revenue's link is `.agents/skills -> ../.claude/skills`, committed on its trunk as 17967ef6d ("Needle #73") and pushed; the read-only `codex exec` from its root on 2026-09-07 listed all seven skills by name (grill-me, hr-feature-review, hr-frontend, hr-plan-execute, hr-plan-write, hr-prompt-change, sure) and quoted hr-plan-write's description, checked against line 3 of its SKILL.md. The other three registered projects have no `.claude/skills`, so the installer laid nothing there. Deviation from the letter: the installer was not run on Hello Revenue in full, only the link through the same function, because card #60's review recorded that registering Needle's UserPromptSubmit hook there fires two anchors on one word until that project's card retires its own; and running the installer from this lane wrote the lane's own hook path into three projects' settings before the line was read — restored by hand and diffed, and the installer now refuses a lane (6b61f84).

### 2. A called Codex colleague answers in the shape asked, and one reader reads every answer

`runtime/codex.py::resume_argv` passes `--output-schema` with a schema the
runtime owns; the shape is small and is §8's own: `answer` (the words),
`how_known` (`checked`, `recalled` or `inferred`), `sources` (what it stood
on). The schema is generated from a Pydantic model in `domain/` — Pydantic is
the contract (CLAUDE.md, typed edges) — and written where the call's answer
lands, beside it. `runtime/calls.py::judge` reads the `answer` field for the
verdict's words when the file parses as the shape and falls back to the first
line when it does not, saying which; `api/runtime_cli.py::call_brief` asks a
Claude colleague for the same shape in words, so there is one reader for both
makes and a Claude answer in prose still lands. Done means: a `needle call`
to a Codex worker lands a file that parses as the shape and the verdict's
words are its `answer`; a call to a Claude colleague lands and reads as
before; a worker that answers off-shape is reported as landed with its first
line and the reason, never lost; `tests/runtime/` covers the three.

Hands out: execution — a throwaway call to a Codex worker on a private store (`NEEDLE_DB`), by script, reported verbatim; verifies by reading the answer JSON and the verdict row before the item claims delivery.

**Met:** `domain/call.py::Answer` is the shape; `runtime/launch.py::call_codex` writes its schema beside the answer and `runtime/codex.py::resume_argv` passes `--output-schema`; `runtime/calls.py::read_answer` is the one reader and `api/runtime_cli.py::call_brief` asks both makes for the shape. `tests/runtime/test_calls.py::test_the_one_reader_takes_the_answer_field_and_falls_back_to_the_first_line_saying_why` covers the shape, prose and off-shape JSON; the Codex call tests hold the schema beside the answer and the verdict's words as the `answer` field; the Claude call test holds that prose lands read by its first line, said so. Live on 2026-09-07 against a private store: `needle call codex` resumed worker 01a07bae in Hello Revenue's root, the answer landed as `{"answer": "The project carries hr-plan-write at .agents/skills/hr-plan-write/SKILL.md. Its first heading is # Before Complex Implementation; I checked by reading the file.", "how_known": "checked", "sources": ["/home/dennis/Work/hellorevenue/.agents/skills/hr-plan-write/SKILL.md"]}`, `needle wait` reported it landed with exactly the `answer` field as its words, and the heading is line 6 of that file — the worker read the skill through the link item 1 laid.

### 3. A colleague of another make reads this slice's close

Codex has a non-interactive review of its own (`codex review --base <branch>`,
and `codex exec review`, with a bundled `review-agent` skill that reads the
project's instructions first). At this card's close, one pass of the review
is that command against `develop`, run read-only from the lane, its findings
verified by the lane the way every delegated result is (§3), classed like the
others and recorded with the reviewer named. Done means: the review record
carries the pass with its raw output verbatim, the count of its findings that
survived verification, and the count from the Claude passes beside it, so the
loop below can be read.

## Acceptance criteria

1. The installer's test covers the link (laid, left alone, named, idempotent);
   Hello Revenue's tree carries the committed link; a read-only Codex session
   on its root lists its skills.
2. A Codex worker's answer parses as the shape and the verdict reads its
   `answer`; a Claude colleague's prose still lands; an off-shape answer is
   reported, not lost.
3. The review record carries a Codex pass with its surviving count beside the
   Claude passes' count.
4. Backend, ratchet, TypeScript and frontend suites green; every commit names
   this card.

## Deliberately not

- Moving skills to `.agents/skills` and linking `.claude/skills` at it.
  Claude Code's reading of a symlinked skills folder is undocumented; the
  reverse link is verified.
- Copying Hello Revenue's skills anywhere, or Codex's `/import`. One folder.
- A schema per call. One shape, §8's, or the reader has two ways.
- Codex holding a lane, Codex's rules files, project-level Codex config.
  Those need the project trusted in Codex's own config, which is the
  machine's (its plan 28).

## Loop

We think the link will make a Codex session on Hello Revenue write plans and
UI through the project's skills instead of refusing or substituting, because
the only thing between it and the skill was a directory name. Fixed before
the data: over the Codex sessions started in Hello Revenue in the fourteen
days after the fold, at least one rollout under `~/.codex/sessions/` reads a
`SKILL.md` under `.agents/skills/` (grep for `hr-plan-write/SKILL.md`,
`hr-frontend/SKILL.md` or `hr-plan-execute/SKILL.md`). If none does and a
session was asked for plan or UI work there, the skills' descriptions did not
trigger Codex's implicit invocation — Codex budgets the skill list at two per
cent of the context window — and shortening them is the next move; if no
session was asked, the loop waits.

We think a Codex review pass will surface findings the Claude passes did not,
because a reader of another make shares fewer blind spots with the author
(§13's reader "who was not its author", taken one step further). Fixed before
the data: the surviving count from item 3 against the Claude passes' count on
this close. If the Codex pass surfaces nothing new, the pass costs one command
and stays optional; if it surfaces one finding the Claude passes missed and
verified, that is the evidence a later card needs to make the pass part of
the review's form in CLAUDE.md, which is the owner's to align on (§2).
