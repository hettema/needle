# A colleague another account started answers a call, or the call says why it cannot

**Kind:** defect
**Fix:** now — HOW-WE-WORK §12 says a session that needs a colleague's judgment calls one warm through Needle's `call` and waits on the answer, and §6 says a report is either the state or bad information; the fix stays inside the runtime's call door (`api/runtime_cli.py`, `runtime/service.py::call`) and removes the class the way #137's cross-machine refusal did — refuse at the door, by name, a colleague whose transcript the calling account cannot resume — rather than one more retry
**Found by:** the lane on card #149 (docs/plans/2026-09-15-auto-fix-stops-at-the-line-you-drew-and-leaves-the-rest-filed.md), in the independent review

## The intent it breaks

A colleague you call answers, or the call tells you at once why it cannot, so the wait is never spent on a colleague who was gone before it began. Today a call to an ended reading session that another account started records the call, moves the session to the caller's account, resumes it there where its transcript does not exist, and reports it minutes later as "ended without its note: it was stopped through its account" — a sentence that names no cause and reads as an accident; the caller retries with the next ended session of the same kind and loses the same minutes again, and the independent review a lane owes waits behind two calls that could never have landed.

## Evidence

- Calls 141 and 142 on 2026-09-15 (rented, account hrme): `needle call dcfc002d …` and `needle call ca0a82dc …`, both ended Needle reading sessions listed under the `armana` account. `needle wait` answered "ended: <id> ended without its note: it was stopped through its account" for each; `needle rescues ca0a82dc` shows the one row `armana/opus → hrme/default  resumed with the owner's answer` at 10:40:15Z, and `needle sessions` afterwards lists the session under `hrme`, ended. No answer file was written.
- Call 144 the same morning, `needle call 2a1a6790 …` on an ended reading session listed under `hrme`, resumed at once as a new session (`481177f2 (resumed from 2a1a6790)`) and read — so the discriminator is which account's transcript store holds the session, which `needle sessions` already prints in its first column and the call door does not read.
- The controlled comparison, the same morning: call 149 was `needle call ca0a82dc …` — the very session call 142 had failed on — made from a session running on the `armana` account instead of `hrme`. It resumed and read at once ("ca0a82dc is working on …, opus on eduard"). Same session, same note, same machine; only the calling account differed. So the cause is the calling account against the session's own, and nothing about the session's state.
- `needle cause <id>` and `needle ended <id>` for the two repeat the one sentence and add nothing.

## What would hold it

The call door reads the session's account before it moves anything: a session whose transcript the calling account cannot open is refused by name with the account that can (`this colleague is armana's; call it from that account, or call one of hrme's: …`), exactly as a Codex colleague that cannot be resumed is refused today (#137). A ratchet in the runtime's tests hands the door a session of another account and expects the refusal, never a rescue row. Neighbours on this ground: #71 (a called colleague has the doctrine, or the call says it did not — the same door, a different silence) and the plan on #83 (a call that travels between machines, item 4), which this does not change.
