# A board that is starting says so instead of answering nothing

**Kind:** defect
**Fix:** now — the intent is written (card #83's plan, item 3: the owner opens the board at its old address and does not know which machine ran it unless he looks; and the first board's "the board is the team's memory" — a page that answers nothing is a board that lies by silence); the fix stays inside `api/cli.py::serve` and `api/app.py` and removes the class — the server binds its port before its first read and answers every page with "the board is starting, N of M read" until the read is done — rather than the instance of one restart the owner met.
**Found by:** the lane on card #83 (2026-09-10, 17:52Z): after a fold that changed Needle's code the rented board restarted, its first read of five projects and the laptop over the wire took three minutes, and the owner's page at `127.0.0.1:8480` answered `ERR_EMPTY_RESPONSE` for the whole of it — the laptop's socket accepted the connection and the proxy found no port behind it.

## The intent it breaks

The board serves from the rented machine and the laptop's address is a doorway to it (item 3). `needle serve` binds its port only after its first read (`api/loops.py`, the served port binds after the first read — card #53's floor note), which on one machine took a second and now takes two to three minutes, since every project's checkouts, sessions and room on the laptop are read over the wire. For those minutes the doorway answers nothing, which reads as a broken board and not as a starting one; every fold of Needle's own code costs the owner that blackout.

## Evidence

- The rented board's journal: `Started needle-serve.service` at 17:50:43, `Needle at http://127.0.0.1:8480/` at 17:50:44, the port answering `200` at 17:53:23 (the record's thirteenth pass, the second live move: 115 s, 120 s, 140 s, 180 s on four restarts).
- The owner's screen at 17:52: "127.0.0.1 didn't send any data, ERR_EMPTY_RESPONSE".

## What done looks like

The port is bound the moment the service starts; until the first read lands, every page and every API answer is a "starting" state with what has been read so far and what has not, and the page shows it as the head's own sentence; a door pressed in that window is refused with the same words rather than left hanging.
