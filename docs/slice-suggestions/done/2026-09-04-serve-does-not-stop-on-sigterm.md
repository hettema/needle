# `needle serve` does not stop on SIGTERM

**Done:** both sections shipped by plan 01b, `docs/plans/done/2026-09-04-01b-the-maps-loose-ends.md`, items 2 and 3 — the stop measured at 0.41 s and exit 0, the watcher on `docs/` whole, `needle add` re-reading a registered path, the project list read live. Archived 2026-09-04.

**Found by:** the coordinating session, 2026-09-04 07:30, restarting the
server to pick up a newly registered project.

## Observation

`systemctl --user restart needle-serve` (a transient scope running
`needle serve`) sat in `deactivating` for longer than the 30 s the caller
waited: the process ignores or outlives SIGTERM, and systemd only ends it at
its stop timeout with SIGKILL. A server that has to be killed is a server
whose restart looks like a hang to the owner, and a supervisor that has to
wait 90 s to replace it.

Likely cause, unverified: the corpus watcher thread (or the SSE stream
generator) is not told to stop when uvicorn receives the signal, so the
process waits on it. Verify before fixing.

## Done means

- `needle serve` exits within two seconds of SIGTERM, closing the watcher and
  every open stream, and exits 0.
- A test starts the server as a subprocess, sends SIGTERM, and asserts exit
  within the deadline.
- The projects list is read from the store on each request, or the store
  notifies the server, so `needle add` does not need a restart to show a new
  project. (Observed the same morning: after `needle add` on the Needle checkout itself
  the running server still listed one project until restarted.)

## Also: a corpus folder created after start is never watched

Verified in `infrastructure/corpus.py::watch`, 2026-09-04 07:35: the watcher
subscribes to `docs/plans` and `docs/slice-suggestions` only if each exists
at startup. This suggestion was the first file in a `docs/slice-suggestions/`
created while the server ran; it did not become a card until the server was
restarted. A project whose corpus grows a folder should not need a restart.
Watch the repository's `docs/` (or the project root) and filter by path, or
re-evaluate the roots on each change, so the "way in" holds from the first
file. And `needle add` on an already-registered project should re-read the
corpus rather than refuse, so a rescan is always one command away.
