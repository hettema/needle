# A colleague of any make can be called warm and seen at work

**Found by:** Dennis, after #51 proved the first Claude-to-Codex collaboration but exposed that the path is one-way: Codex can call and wait for Claude, while Claude cannot call a warm Codex worker or see one in Needle's session list.
**Status:** PENDING
**Written:** 2026-09-05, by Codex after a grounded challenge from the Claude Opus session that built omarchy #19 and planned Needle #54. Claude verified `codex exec resume [SESSION_ID] [PROMPT]` on this machine and read a live Codex rollout tail; this corrected the earlier belief that a broad provider adapter had to be designed first.
**Effort gate:** medium — the behaviour is narrow and the second file format is known; the risk is falsely claiming symmetry where Codex has no Claude-owned account wall or interactive-session lifecycle.
**Sequencing:** none as a hold. It closes the remaining half of #51's experiment and may run beside #54 because it touches runtime colleague resolution, launch and registry reading, not #54's doctrine files or board entrance.

## Intent

A running AI colleague can ask a warm colleague of another make a bounded question and see that colleague at work through Needle's one collaboration surface. The caller should not need to know which provider owns the transcript. Equal means the same useful behaviour and the same safety refusal, not invented lifecycle parity: a callable Codex worker is a non-interactive `codex exec` rollout, never the interactive chair session, and Needle does not pretend Codex has Claude's subscription-wall states.

## Evidence

- `needle call` and `needle wait` are already provider-independent from the caller's side; this Codex session used both to reach Claude with zero manual polling.
- `runtime.colleague()` and `runtime/launch.py::call` resolve and resume only Claude transcripts today.
- `runtime/registry.py::sessions` reads Claude slot directories only. Codex rollouts under `~/.codex/sessions/**/rollout-*.jsonl` carry cwd, timestamps and a readable tool-call tail.
- `codex exec resume <SESSION_ID> <PROMPT>` exists in Codex 0.152.1. An earlier contrary note was a flag-ordering error.
- **A called Codex worker cannot write its answer by default, and this is a
  config fact, not a one-off.** `codex exec` runs `sandbox: read-only` unless the
  caller passes `-s`; `~/.codex/config.toml` sets no `sandbox_mode`. Proved on
  2026-09-05 ~16:30: the Claude Opus session f4d2a309 resumed rollout
  `01a071ee-cfd3-7fd2-a9dd-cdbff4fec194` with a question and a named answer path;
  Sol composed the whole reply and then said the sandbox rejected the write. The
  exchange survived only because the caller captured stdout by hand — which is
  exactly the manual relay item 2 exists to remove.
- **`workspace-write` is not enough on today's paths.** The shared record lives at
  `~/.cache/omarchy/claude-acct/discussion/`, outside any workspace, so a call that
  merely widens the sandbox one notch still cannot answer. Either the call places
  note and answer inside the worker's own workspace, or the caller reads the
  worker's stdout as the answer. The second is the smaller door and needs no
  sandbox widening at all.

## Items

### 1. The existing colleague concept resolves a Codex worker

Resolve a Codex rollout id, and the unambiguous name `codex`, beside today's Claude resolutions. Preserve the provider on the resolved handle only where behaviour needs it; do not introduce an abstract adapter before the second implementation shows a repeated boundary. Refuse an interactive or currently mid-turn Codex session for the same reason an interactive or mid-turn Claude session is refused. Done means: fixtures resolve one warm Codex worker; ambiguous, absent, interactive and busy workers are refused with the true reason; existing Claude resolution is unchanged.

### 2. The one call resumes Codex and the existing wait judges its answer

Resume the worker with `codex exec resume <id> <brief>` in a transient scope, verify that the new process is alive, and record the existing `Call` fields and watercooler files without a second protocol. Codex calls have only truthful verdicts: `LANDED`, `ENDED`, or `NOTHING`; Claude account movement remains Claude's lifecycle fact. A Codex worker's answer is taken from the channel the sandbox actually permits — its stdout, or a path inside its own workspace — never from a write to the shared record that the default sandbox refuses; a call that would need the caller's hands to save the answer is not an answer path. Done means: a fixture call resumes the named rollout with the brief, the answer lands through the existing record without any manual relay and without widening the sandbox to `danger-full-access`, `needle wait` returns it without polling, a worker whose sandbox refuses its write is reported as refused rather than silently empty, and launch failure leaves no false running call.

### 3. One session list shows Codex doing

Read Codex rollout metadata and its tail into the same session projection used by `needle sessions`, including cwd, last activity and a concise `doing` derived from the most recent tool action. Keep the file-format reader beside the Claude transcript reader; extract a shared boundary only if the finished implementations actually repeat one. Done means: mixed Claude and Codex fixtures render in one list, a malformed or disappearing rollout cannot break the list, and no secret prompt or tool payload is surfaced as `doing`.

## Acceptance criteria

1. A Claude worker calls a warm, non-interactive Codex worker through `needle call`; Codex answers in the shared record; `needle wait` returns within one second of the answer with zero caller polls.
2. `needle sessions` shows that Codex worker while it is active and removes or ends it truthfully afterward.
3. The sixth row of #51's cold/warm comparison is filled by both colleagues, including elapsed time, material corrections and claims corrected.
4. Existing Claude call, wait and session behaviour remains green; the full backend, ratchet, TypeScript and frontend suites pass.

## Loop

We think a callable and visible Codex worker changes collaboration from a chair manually relaying notes into one reciprocal surface without making Codex an execution lane. Fixed now: complete the warm Codex exchange in #51's comparison and compare it with the cold row. If the exchange needs manual relay, targets the interactive chair, leaks transcript content, or needs provider-specific caller commands, the intent did not land. If a third provider later repeats a boundary that these two implementations share, file the extraction from that evidence rather than predicting it here.

## Deliberately not

- A Codex execution lane, worktree fold, close or review authorship.
- Codex hooks, trust configuration, limits or account switching; those are machine/provider adapter facts.
- Claude wall and handoff states projected onto Codex.
- A generic provider framework designed in advance of repeated implementation evidence.

## Terrain

- `runtime/service.py::colleague`, `runtime/launch.py::call`, `runtime/calls.py`
- `runtime/registry.py`, `runtime/transcripts.py`, `domain/call.py`, `domain/slot.py`
- `api/runtime_cli.py`, call/wait/session fixtures, and #51's completed plan and review record

## Close-out

Written by the lane: the exact warm Codex exchange; process and answer timestamps; caller poll count; the completed #51 comparison row; the two refusal demonstrations; files changed; every review pass and correction; full-suite results.

