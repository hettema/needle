# A lane that grows toward the machine's ceiling pauses new starts before oomd has to kill it

**Kind:** defect
**Fix:** now — the intent is written (the plan "as many lanes as the machine can hold": "without crashing the machine"; ruling 4, the number is a ceiling the machine lowers); the fix stays inside the dial and the runtime's one door to the machine; it removes the class — every lane that grows after the beat let it in — not the one kill.
**Found by:** the owner, from card #50's close-out conversation on 2026-09-05, after the card's first signal reading found the kill the review had missed. The owner: "I want to stop the machine from crashing and I want to work at max capacity."

## Observation

The memory floor (`board/dial.py::MEMORY_FLOOR_BYTES`, `api/dial.py::_full`) is read once per beat, before the dial opens a planning session or a Start. Nothing reads the machine while lanes run. On 2026-09-05 at 10:59:22, forty-one seconds after the board restarted on the floor, `systemd-oomd` killed Hello Revenue #386's lane scope (65 processes): the machine was at 15.4 of 16.4 GB used and 14.8 of 16.4 GB of swap, and the killed scope had peaked at 4.7 GB (`MemoryPeak`) after the dial started it at 10:49 with the floor satisfied. Four lanes, the board, and a fifth lane running the full suite by hand shared a 16 GB machine; the floor could see none of that growth.

## Evidence

- `journalctl --since 10:58 --until 11:02`: "Marked …needle-card-386….scope for killing due to memory used (15449980928) / total (16437264384) and swap used (14808154112) / total (16436412416) being more than 90.00%".
- `systemctl --user show needle-card-386-the-continuity-check-route-has-n.scope -p MemoryPeak` → 4718346240.
- Card #50's history at 09:05Z: the reading session's words, and the WATCH row rewritten without its memory clause.
- `docs/reviews/2026-09-05-as-many-lanes-as-the-machine-can-hold.md`, pass 9.

## What would hold it

The board reads the machine on every lane-loop pass, not only at the dial's beat, and reads each lane scope's memory beside it (`systemctl --user show -p MemoryCurrent`, through the runtime's one door). While available memory or free swap is under the floor, or any lane's scope is growing past the peak the floor was set from, the dial opens nothing and the head says which lane is growing and how far. The floor itself stays the owner's number. Rejected: the board stopping or pausing a running lane — a lane's work is its own, and the fold judges it; the board's move is to stop admitting, and to say so.
