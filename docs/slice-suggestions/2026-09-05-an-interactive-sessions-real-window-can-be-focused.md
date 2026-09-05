# An interactive session's real window can be focused

**Found by:** Codex session `01a07296`, while Dennis asked it to bring Claude sessions `4e37cd2c` and `e767e02e` forward for a different-make doctrine review on 2026-09-05.
**Kind:** defect
**Fix:** now — plan 04 already promises that an open session window is a door the owner can focus; the fix stays inside Needle's window reader and removes the class for every live interactive session whose terminal was not opened and recorded by Needle.

## Observation

Needle contradicted itself about two live interactive Claude sessions:

```text
needle focus 4e37cd2c
  no window is open into 4e37cd2c; open one first
needle window 4e37cd2c --as board-discuss
  4e37cd2c runs in a terminal of its own; that terminal is its window

needle focus e767e02e
  no window is open into e767e02e; open one first
needle window e767e02e --as lane
  e767e02e runs in a terminal of its own; that terminal is its window
```

The compositor had both windows. `hyprctl clients -j` reported them mapped and visible, and the documented `hyprctl eval` focus by address succeeded:

- `4e37cd2c`: Foot PID 382193, class `org.omarchy.agent`, workspace 1; its descendants are `claude-agent-auto` → `claude-acct auto` → Claude PID 382751.
- `e767e02e`: Foot PID 464656, class `org.omarchy.board-look-card-23-20-every-agent-on-this-machine-r`, workspace 3; Claude PID 464673 is its child.

## Cause found in the live code

`runtime/windows.py::focus_window` can focus only a `Window` already recorded in Needle's store. `reconcile()` removes recorded windows the compositor no longer has but never discovers a compositor window Needle did not open. `open_window`, separately, refuses every live `SessionKind.INTERACTIVE` from the registry fact that it runs in its own terminal. The two verbs therefore answer “has a window” from different sources: Focus asks only Needle's historical ledger; Window infers it from session kind. A terminal launched outside Needle is simultaneously absent and present.

## What would fix the class

One window truth: reconcile the compositor's live clients with the live process tree as well as Needle's ledger. A mapped terminal client whose PID is an ancestor of the session process is that session's existing window, whatever its app-id; record or project it through the same `Window` shape so `focus` uses the existing proved address. `window` then refuses a second window because that same projection found one, rather than because `SessionKind.INTERACTIVE` implies one.

Done means:

1. A fixture compositor window whose terminal PID is the parent, grandparent or deeper ancestor of an interactive session is discovered as that session's window; `focus` brings it forward and proves the active address.
2. The two live shapes above are represented: direct Foot → Claude and Foot → launcher → supervisor → Claude. Neither depends on an `org.omarchy.*` class naming the session.
3. A compositor client unrelated to the session is never adopted merely because it is a terminal; a stale PID or a PID reused after the session's recorded process start is rejected.
4. `window` and `focus` cannot disagree about whether the session has a window, and a second window is never opened.
5. Existing attached lane windows, owner-closed windows and compositor-unavailable behaviour stay unchanged.

## Boundary and overlap

This does not add a way to start a turn in an idle interactive terminal. `needle call` deliberately refuses a terminal so it cannot resume a second copy beside the owner's session; waking an existing terminal is a separate capability and intent decision.

Pending plan 15 (`a-card-that-finishes-or-needs-you-rings-until-you-dismiss-it`) names `runtime/windows.py` for focusing the board window. Its lane and this defect must not edit that file concurrently: plan this card after #15 folds, or have #15 carry the general reconciliation fix if its lane has not yet crossed that seam and the plan records the added promise.

## Evidence still arriving

Claude sessions `4e37cd2c` and `e767e02e` received `from-codex-session-window-bug.md` for an independent challenge of the cause, ownership and boundary. Their conclusions are folded into this document before execution if they materially change the claim above; a delegated result is a claim, so the executing lane re-reads the named code and reproduces the two live commands before acting.
