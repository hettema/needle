# The work runs where the horsepower is, and the board feels like it is on your laptop

**Kind:** idea
**Fix:** his — it spends money every month (a rented machine, a bound he has not set) and adds a second machine to the organisation, which is external exposure beyond anything authorised so far; the shape is execution once the bound is set, and this suggestion says what the shape is so the decision is one number
**Found by:** the owner on 2026-09-07, after the laptop was pushed past its memory twice in three days: "if my machine is the limit… can we rent a server in the cloud for cheap and control it naturally from here? I guess lag might drive me mad and I don't know how we'd log in all accounts etc. My intent is to not be limited by horse power from my machine but still interface as if I'm on my machine."

## Observation

- The laptop is the limit, and it is memory, not speed. The board's floor is 5 GB free per admitted lane (`board/dial.py`, raised from 3 GB the day a lane peaked at 4.7 GB); a 16 GB MacBook Pro holds two lanes beside a browser and the board, and on 2026-09-05 nine lanes were killed by the system in one evening. #53 stops the board admitting past the floor; it does not raise the floor.
- The doctrine already expects more than one machine. HOW-WE-WORK's contract says a project on Needle is built the way we work "wherever it runs", and plan 18 (card #54, shipped) made a new machine follow the way we work from its first session and teach back. What is missing is not permission but the runtime's assumption that the machine it runs on has a screen.
- What binds the runtime to this laptop, read in `runtime/`: the lane's window and focus verbs are proven by the compositor (`runtime/windows.py`, `hyprctl`); a session is a systemd user scope on the machine the board runs on (`runtime/service.py`, `runtime/machine.py`); the accounts are the slots under `~/.claude-accounts/` that `claude-acct` switches between, and Codex's under `~/.codex/`. None of that is the board's: `board/` never spawns a process, and the page is a web page.

## What would hold the intent

Not a decision here, only the shape, so the decision is a number.

1. **The board stays one board, reached from the laptop.** `needle serve` runs on the rented machine; the laptop reaches it over a private network (Tailscale, or an SSH tunnel) at the same URL shape it has today, so the desktop entry, the notifications of #41 and the bar are unchanged. A web page has no lag worth noticing at European distances.
2. **Lanes run where the memory is.** A lane's session runs in a scope on the rented machine, in a terminal multiplexer instead of a compositor window; the runtime's "open a window into a session" verb becomes "open a terminal here attached to that session there", proven by the multiplexer the way `hyprctl` proves it today. Typing latency to a Helsinki or Falkenstein machine from Sweden is tens of milliseconds, under what a keypress takes to render.
3. **Accounts travel once.** The slots are files; `machine install` on the rented machine lays them from the machine repository as it lays everything else, and `claude-acct` refreshes them there as it does here. A login that needs a browser happens once, on the laptop, and the token is what moves. Codex's `auth.json` is the same shape.
4. **A second machine record.** The rented machine gets its own repository in the pattern of `omarchy-machine` — what is installed, how it is checked, how it is reverted — and registers on the board as plan 18 says a machine does. The laptop keeps its record; nothing in it changes.
5. **The floor scales with the machine.** The 5 GB floor is per lane; a 32 GB machine holds five lanes beside the board, a 64 GB one ten. The dial's number becomes what it was meant to be, a ceiling the machine lowers, not a ceiling the laptop sets.

What the owner decides: the monthly bound. For orientation only, read on 2026-09-07 and to be re-priced by the plan: a shared-CPU cloud machine with 32 GB is in the tens of euros a month; a dedicated one with 64 GB is not much more. The doctrine's loop for it: within two weeks, the count of lanes killed by the system on either machine, and whether he once noticed where a session ran.
