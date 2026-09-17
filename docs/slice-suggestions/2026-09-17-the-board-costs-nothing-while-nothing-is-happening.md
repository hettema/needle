# The board costs nothing while nothing is happening

**Kind:** defect
**Fix:** his — the thirty-second pass is a written choice in the board's loop (`api/loops.py`, `FLOOR_SECONDS`: "a session that dies without a hook (a kill, a reboot) is on the board within this, whatever else is quiet"), and card #83's remaining item moves the board to the rented machine, where a battery does not matter; so the owner chooses between thirty-second notice of a silent death and a board that is quiet at rest, and whether the cost still matters once the board leaves the laptop. Neither choice is written anywhere today.

**Found by:** #249's reading on Hello Revenue, 2026-09-17 — that card's signal asks whether the board that actually runs stays quiet at idle, and the board that runs is this one

## The intent it breaks

The board should cost nothing while nothing is happening, and today it takes a quarter to two thirds of a processor core around the clock, on the laptop, on battery. Hello Revenue's card #249 shipped a board that heard its inputs instead of asking them, so that it "is idle when the world is idle"; Needle replaced that board on 2026-09-04 and the replacement asks every machine every thirty seconds, day and night, and asks the rented machine over ssh forty times a minute for the cause of deaths it can never settle. While this stands the owner pays a warm laptop and a shorter battery for a board nobody is looking at overnight, and once the board moves to the rented machine he pays a rented core for the same silence.

## Evidence

Read on the laptop on 2026-09-17, between 12:57 and 13:10 CEST, with no lane on the laptop (`needle lanes` names none; the only sessions on it were two of the owner's own conversations on the machine repository).

- `systemctl --user show -p MainPID needle-serve.service` gave 530941, started 2026-09-16 22:04:15 CEST. Its `/proc/530941/stat` moved 1613 ticks of CPU in one 60-second sample, 3966 in another (100 ticks a second): 27 % and 66 % of one core. Since its start it has used 12,224 CPU-seconds over 14.9 hours: 23 % of a core on average, overnight included.
- The process before it, stopped by the owner's restart at 22:04 on 16 September, is accounted by systemd itself in the board's journal: "Consumed 6h 11min 47.223s CPU time over 19h 43min 59.516s wall clock time" — 31 % of one core for its whole life.
- `needle beats --count 20000` lists 96 to 125 passes in every hour of the last 24, the hours 00:00 to 06:00 UTC included, each holding the loops' lock 5 to 9 seconds. The pass rate does not change when the machines are quiet.
- In one 60-second sample the board had 46 distinct children: 41 `ssh rented -- needle cause <id> …` calls, two `git fetch`, two notification prompts. The cause calls name sessions that ended on 15 and 16 September (cards #554, #547, #591, #575) and each answers `"settled": false` ("the cause is not established"), so the same question is asked of the rented machine again on the next pass, and has been for two days.
- The other half of #249's signal holds: after the kernel's `PM: suspend exit` at 2026-09-16 12:21:59Z (journalctl -k), the board's next pass is at 12:22:28Z, 29 seconds later.

## Neighbours on this ground

- Card #83, `docs/plans/2026-09-07-the-work-runs-where-the-horsepower-is-and-the-board-feels-like-it-is-on-your-laptop.md` — "The loop reads every machine on every pass" is that plan's design, and its open item 3 moves the board to the rented machine. This card does not change what #83 delivers; it asks what the board costs at rest wherever it runs.
- `docs/slice-suggestions/done/2026-09-04-what-the-first-board-held-that-needle-does-not-yet.md` — the retirement's list of what the first board held mechanically; a board quiet at idle was not on it, which is how the design was lost without anyone declining it.
- The design that was retired, if the owner chooses quiet: Hello Revenue's `docs/plans/done/2026-09-03-the-board-stops-asking-and-starts-listening.md` — file watches on the written inputs, a ten-minute floor on the boot clock, and a page that is pushed rather than polled.
