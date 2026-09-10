# A test run on a layered filesystem that keeps its writes in memory is refused too

**Kind:** defect
**Fix:** his — the check on card #109 refuses a scratch root by the kernel's own name for its filesystem (tmpfs, ramfs), and a layered filesystem (overlay) answers with its own name while its writes may go to a memory layer beneath; whether the board's bar is "the kernel calls it memory" or "the writes end up in memory" is the owner's to set, because holding the second means reading each layered kind's mount options for where its writable layer lives, and no machine on the board mounts one for a test root today.
**Found by:** the lane on card #109 (docs/plans/done/2026-09-10-a-test-run-never-takes-the-memory-the-work-needs.md), in the review's fourth cold read by Codex

## The intent it breaks

A test run never takes the memory the work needs: the board refuses a run whose scratch files would sit in memory. Today that refusal reads the kernel's name for the filesystem the scratch root stands on, and a filesystem layered over a memory-backed one keeps its own name, so a run on such a stack would pass the check and lay its files in memory unnoticed. Nothing on the board runs that way today; he loses nothing until something does.

## Evidence

- `tests/ratchets/test_the_runtime_stands_on_the_floor.py::test_the_floors_stand_on_disk` (card #109) asks `stat -f %T` for pytest's resolved root and refuses `tmpfs` and `ramfs`.
- An overlay filesystem mounted under `/tmp` with its writable upper layer on `/dev/shm` stores new files in memory and answers `overlayfs` (Codex, 2026-09-10, from the kernel's overlay implementation and coreutils' name table; no mount was made). The same holds for any layered kind whose upper layer is memory.
- The plan's loop reads the same kernel answer from the suite's own ledger, so such a run would be counted as on disk there too.

## What would hold it

Either the ruling that the kernel's name is the bar, written into the plan of card #109 as a boundary, or a reader of the writable layer for each layered kind (for overlay, the `upperdir=` option in the root's mount entry, then the kernel's answer for that directory) beside the existing check, with a test that writes such a mount table.
