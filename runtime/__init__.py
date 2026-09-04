"""The thing that runs.

The board reads what runs and never is the thing that runs (INTENT.md, lesson
1). This package is the runtime service: one list of sessions across every
subscription slot, the one model rule asked of `claude-acct`, a start in a
scope of its own, a move on the wall detector's handoff, and a window into
any session. Everything here that touches the machine goes through
`runtime.machine`, so the test floor can stand in for the machine whole.
"""
