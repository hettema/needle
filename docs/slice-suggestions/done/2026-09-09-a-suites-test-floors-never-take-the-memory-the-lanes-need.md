# A suite's test floors never take the memory the lanes need

**Carried by:** docs/plans/2026-09-10-a-test-run-never-takes-the-memory-the-work-needs.md
**Kind:** defect
**Fix:** now — the intent it breaks is written (the plan "a full machine admits nothing new": the floor is a ceiling the machine lowers, and the memory it reads is what the lanes have), the fix stays inside the test floor (`tests/floor.py`, `tests/conftest.py`: lay every floor under a directory on disk, not under `/tmp`), and it removes a class: every suite on this laptop, not one run
**Found by:** the lane on card #83 (docs/plans/2026-09-07-the-work-runs-where-the-horsepower-is-and-the-board-feels-like-it-is-on-your-laptop.md), running its final suite

## The intent it breaks

The board keeps a 5 GB floor of free memory so a lane is never admitted onto a machine that cannot hold it, and it reads that memory as the machine's; while a suite runs, the memory it reads is short by the suite's test floors, which sit in memory without anyone knowing, so lanes are refused or killed for room that a directory is holding.

## Evidence

- `/tmp` on the laptop is a `tmpfs` of 7.7 GB — a filesystem in memory (`df -h /tmp`, 2026-09-09 23:30Z: `tmpfs 7.7G 5.9G 1.9G 76%`).
- pytest lays every test's floor under `/tmp/pytest-of-dennis/pytest-<n>` (`tmp_path_factory`), and keeps the last three runs; with several lanes running suites, `/tmp/pytest-of-dennis` held 2.9 GB, and another session's probe 2.3 GB, at the moment the memory killer took card #83's whole process group (48 processes, 22:03Z) and again when a suite failed with `No space left on device` (23:28Z).
- The same evening the board's floor read the laptop at 2 GB available while 3 GB of that shortfall was test floors in `/tmp`.

## What would hold it

The test floor (`tests/conftest.py::machine_floor`, `tests/floor.py::lay`) takes its root from a directory on disk — `$XDG_CACHE_HOME/needle/floors` or `~/.cache/needle/floors`, pruned like pytest prunes — instead of `tmp_path_factory`'s default under `/tmp`; a ratchet reads the floor's root and refuses one on a memory-backed filesystem. Until then, every suite run passes `--basetemp` on disk by hand, which is what card #83's lane did for its last run.
