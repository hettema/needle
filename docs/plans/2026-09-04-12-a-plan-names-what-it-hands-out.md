# 12 — A plan names what it hands out

**Status:** PENDING
**Written:** 2026-09-04, from the machine's card 12 plan window (`omarchy-machine/docs/plans/2026-09-04-12-smart-with-tokens-never-with-quality.md`). Dennis: "lets make it a planned card at the top of up next. I want to nail this before I start pushing work hard again. This is a mission critical piece of work for me." The grammar this plan adds is the machine's rule that Fable orchestrates and judges while cheaper roles do bounded work; the README here is the source every project's plan folder copies, so the line lands here first.
**Effort gate:** high — the line's form is specified by the machine's card; the judgment is in keeping it a sentence a planning session writes naturally rather than a field that turns plans into forms, and in deciding where the board reads a lane's dispatches from.
**Sequencing:** the grammar (item 1) can land at once. Items 2 and 3 read role names from `~/.claude-accounts/roles.json`, which the machine's card 12 gives its role files; nothing here waits on those files, but a role the machine has not named is reported, not invented.

## Intent

Two days of transcripts on this machine showed zero subagent requests in 175 sessions: every search, test run and log read ran on Fable's main thread and stayed in its context for the rest of the session, and the Fable allowance on four subscriptions was gone in two days. The machine's card 12 gives sessions hands to route to — one subagent definition per role, `search` and `execution`, held to `roles.json` — and the doctrine rule that a delegated result is a claim Fable verifies before acting on. What makes that reliable rather than remembered is the plan: an item that hands work out says so, names the role, and says what the executing session verifies before it acts on the result. A plan that says nothing hands nothing out and runs on Fable, which is correct and visible.

After this plan, the plan grammar every project copies carries that line; the board shows a card's named handouts; and a lane's close writes what was actually dispatched against what the plan named, so an unnamed handout, an unfollowed one, or a role nobody has earned is a row on the card, never a guess.

### 1. The grammar
`docs/plans/README.md` (the source) says, beside the effort gate: an item that hands work to a role ends with a `Hands out:` sentence naming the role (`search`, `execution` — roles, never model names), what it hands out, and what the executing session verifies before acting on the result; an item that is judgment says nothing, and that silence means Fable. The why goes with it in two lines: verbose work in a subagent's own context is the cheapest token on the machine, and a subagent's result is a claim. Done means: the README carries the line and its why; the machine's copy of the README paragraph (its card 12) and Hello Revenue's (`hr-plan-write`, its own card) cite this file as the source.

### 2. The board reads it
The plan parsers in `board/parse.py` read the `Hands out:` sentence the way they read the effort gate, and the card shows its handouts per item. A role the sentence names that `roles.json` on this machine does not know is a verdict line on the card, in the same voice as a plan with no gate. Done means: a fixture plan with two handouts shows both on its card; a plan naming a role the machine has not defined shows the verdict; a plan with no handouts shows nothing new.

### 3. The close writes handouts against dispatches
At a lane's close, the board reads the lane's transcript (`~/.claude/projects/<cwd slug>/<session>.jsonl`, the `Agent` tool-use blocks and their `subagent_type`) and writes one row on the card: what the plan named, what the lane dispatched, per role — `handed out: search ×3 (named 2), execution ×0 (named 1)`. That row is the trace the machine's loop reads (`machine burn` counts the same blocks across every project); the board keeps it per card so the owner sees it where the work was. Done means: closing a fixture lane whose transcript holds two `search` dispatches against a plan that named one writes the row with both counts; a named handout never dispatched reads as such; a lane with no dispatches and no handouts writes nothing.

## Terrain
- `board/parse.py` — the plan header parsers (Status, Written, Effort gate, Carries); the handout sentence is parsed beside them. `domain/gate.py` is the shape to mirror for a small closed vocabulary that comes from outside the repo: here the vocabulary is `roles.json`'s keys, read at parse time, never hard-coded.
- `board/lane.py` — the card view and Start; `STARTABLE_COLUMNS`. The handout list is display only; nothing about Start changes, because the role files are global (`~/.claude/agents/`) and the lane finds them by itself.
- The close path (`needle close`, `runtime/handoffs.py`, `infrastructure/store.py` rows) — where the DELIVERED and WATCH rows are written; the handouts row is one more of the same kind.
- `~/.claude-accounts/roles.json` — the roles and today's model per role; `null` is a role not yet earned, which still counts as a valid name (the lane runs it on Fable via `inherit`).
- The machine's `docs/plans/2026-09-04-12-smart-with-tokens-never-with-quality.md`, item 3 — the doctrine rule, the role files, the verification-against-redo distinction the counts feed.

## Acceptance criteria
1. `docs/plans/README.md` carries the `Hands out:` sentence and its why, and names itself as the source.
2. A card whose plan names handouts shows them per item; an unknown role is a verdict line.
3. A lane's close writes the handouts-against-dispatches row from the transcript, on a fixture with a known count.
4. The three README copies (Needle, the machine, Hello Revenue) say the same thing, each citing this file.
