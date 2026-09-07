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

## The bound, and the machine read against it

The owner set the bound the same day: "I guess I could spend up to 100 eur/month, cheaper better." What remains his is the pick below, one word.

Prices read live on 2026-09-07, ex VAT (a VAT-registered Swedish buyer pays the net figure under reverse charge; the plan confirms this at order time):

| provider, model | cores | memory | disk | where | per month | once |
|---|---|---|---|---|---|---|
| Netcup RS 8000 G12 (root server, dedicated cores) | 16 EPYC | 64 GB DDR5 ECC | 2 TB NVMe | Nuremberg, Vienna or Amsterdam | €59.97, one-month term | none listed |
| Netcup RS 4000 G12 | 12 | 32 GB DDR5 ECC | 1 TB NVMe | same | €33.55 | none listed |
| OVH Rise-S (bare metal) | 8 Ryzen 7 9700X | 64 GB DDR5 ECC | 2×512 GB NVMe | France or Germany | €64.99 | €64.99 setup; "soon available" |
| Hetzner AX42-1 (bare metal) | 8 Ryzen 7 PRO | 64 GB DDR5 ECC | 2×512 GB NVMe | Falkenstein or Helsinki | €97.30 since the 15 June 2026 repricing | €49 setup |
| Hetzner auction, i7-6700/7700 (2016 hardware) | 4 | 64 GB DDR4 | 2×512 GB NVMe | Falkenstein or Helsinki | €89–95 | none |
| UpCloud, Stockholm | 8 | 64 GB | — | Stockholm | from €220 | — |

The recommendation, made here because it is execution once the bound is set: **Netcup RS 8000 G12, 64 GB, Nuremberg.** It is the only offer under the bound with modern hardware, ECC memory and dedicated cores; at the 5 GB floor it holds ten lanes beside the board, five times the laptop; the one-month term means a wrong pick costs one month. Against it: it is a virtual machine on shared hardware, not bare metal, so a noisy neighbour is possible; the plan's loop measures that (a build's wall-clock on the machine against the laptop's, weekly). Rejected: Hetzner, the usual answer until June 2026, now the dearest modern option and over budget with setup; the auction boxes, ten-year-old CPUs at ninety euros; UpCloud's Stockholm zone, the only one in Sweden, at more than twice the bound. The 32 GB Netcup at €33.55 is the honest fallback if the loop shows five lanes are never reached; the plan starts at 64 because the memory is the whole reason to rent.

Where Sweden sits: Nuremberg is about 25–35 ms from Stockholm on the wire, which is under the time a terminal takes to draw a keypress; the board page does not care.

**Accounts.** A slot is a directory under `~/.claude-accounts/<name>/` and its login is the file `.credentials.json` inside it (`docs/claude-multi-subscription.md`, the machine repository); Codex's is `~/.codex/auth.json`. Both are OAuth tokens that refresh themselves, so the machine repository lays them on the rented machine as it lays everything else, and no browser login happens there. Whether a token refreshed from two machines stays valid on both is the one fact the plan proves live in its first hour, on one slot, before the rest move; a login that has to happen again happens on the laptop and the file moves again.

**The account viewer in the bar (Omarchy #38)** stays on the laptop: it reads the subscriptions' allowances through the same tokens, which the laptop keeps, not the machine the sessions run on. What it would gain from the rented machine — which sessions are running where — the board already serves over the network, so the bar reads the board, not the machine.

**A cold read of another make** (Codex 0.153.4, read-only, 2026-09-07, no web) changed three things above and is kept here as the record:

- *Start at 32 GB, not 64.* Its argument: the 5 GB floor is a floor, not a safe peak, and four or five sessions on 32 GB at half the price is the honest first step; 64 GB earns its price through measured memory pressure, not through the intent. Taken: the pick is **Netcup RS 4000 G12, 32 GB, €33.55**, and the step to 64 GB is what the loop below decides, at a one-month term. The 64 GB row above stays as the step.
- *The objection to a root server is disk, not cores.* Dedicated cores do not mean dedicated storage, and this workload — parallel node builds, pytest, git worktrees — is judged by disk under load. Taken into the loop: a build's wall-clock on the machine against the laptop's, weekly, and a lane's `git` operations timed.
- *Do not copy the tokens; log in once per machine.* A refresh token used from two machines can race and invalidate one side, and neither provider's current rotation rule could be confirmed cold. Taken: each slot logs in on the rented machine once, through the browser-less flow (the CLI prints a URL and a code; the laptop's browser answers it), so each machine holds its own token for the same subscription; the allowance is the subscription's and stays shared. The paragraph on accounts above is corrected by this one.
- *What he will notice is interactive delay.* Taken as the shape already is: the terminal, the editor and the browser stay on the laptop; only execution is remote, over a private tunnel.

The doctrine's loop: within two weeks, the count of lanes killed by the system on either machine, whether he once noticed where a session ran, a build's wall-clock on the machine against the laptop's, and the memory high-water mark, which decides whether 32 GB becomes 64.
