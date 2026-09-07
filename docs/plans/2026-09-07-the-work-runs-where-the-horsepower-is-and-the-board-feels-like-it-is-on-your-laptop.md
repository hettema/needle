# The work runs where the horsepower is, and the board feels like it is on your laptop

**Carries:** docs/slice-suggestions/done/2026-09-07-the-work-runs-where-the-horsepower-is-and-the-board-feels-like-it-is-on-your-laptop.md
**Status:** NEW — planned, not started; the owner placed it at the top of Planned on 2026-09-07 after setting the bound and confirming the flow.
**Written:** 2026-09-07, from Dennis: "My intent is to not be limited by horse power from my machine but still interface as if I'm on my machine." The bound: "up to 100 eur/month, cheaper better." On the flow, after the live pricing and a cold read of another make: "For the rest the flow looks good." On the one thing he raised: "how would we deal with captchas and stuff? Anthropic is throwing captchas nowadays" — answered in item 2: the browser step of every login stays on the laptop, so the rented machine never meets a captcha.
**Effort gate:** high — the mechanics are a machine record in a pattern that exists (`omarchy-machine`), a tunnel, one login per slot, and the runtime's session and window verbs taught a second machine; the judgment is where a lane runs (item 4's rule) and what must never move (the laptop's own cards), and the failure that would be silent — a token refreshed from two machines invalidating one — is what item 2 proves before anything else moves.
**Sequencing:** after #53 (the floor the rented machine's admission rule reuses is #53's, read every beat) and #68 (a lane the machine ended comes back by itself, which on a second machine is the only way a dead lane returns at all — nobody is sitting at it). Items 1 and 2 can land and be proven before either; the runtime items wait.
**Class:** the loop below counts lanes killed by the system on either machine and reads the memory high-water mark daily; the board shows on its head which machine each running lane is on, so a lane on the wrong machine is loud.

## Intent

The laptop holds two lanes; the work should hold as many as the intent
needs. So the lanes and the board run on a rented machine with the memory,
and the owner keeps using the laptop as he does now: the same board at the
same address, the same notifications, the same terminal into a session,
the same account switcher. Nothing he touches moves; only where a process
runs. The doctrine already expects it — a project on Needle is built the
way we work wherever it runs, and plan 18 made a new machine follow the way
we work from its first session — so this plan adds no rule, only a second
machine that obeys the existing ones.

The pick, from the live pricing of 2026-09-07 in the carried suggestion:
**Netcup RS 4000 G12** — 12 dedicated cores, 32 GB DDR5 ECC, 1 TB NVMe,
Nuremberg, €33.55 a month ex VAT on a one-month term. The step to the 64 GB
RS 8000 G12 at €59.97 is decided by the loop, never by the intent.

What does not change: the laptop's own cards. A card on the Omarchy board
changes this laptop, so its lane runs here and nowhere else. The one board
and its one store: there is still exactly one `needle serve` and one store,
now on the rented machine, and the laptop reaches it at the address it
already uses.

## Items

### 1. The machine exists, has a record, and is on the board
The Netcup root server is ordered at the bound, installed with Arch so the
laptop's tooling (`machine install`, the shared skills and agents, `claude-acct`,
`needle`) runs unchanged, and reached from the laptop over a private
network (Tailscale, or an SSH tunnel; the plan proves one and records why
the other was not taken). It gets a repository in the pattern of
`omarchy-machine` — what is installed, `machine check` as the reader that
reports drift, how to revert — and registers on the board as plan 18 says
a machine does. Nothing under the laptop's record changes.
Done means: `machine check` is green on the rented machine; `ssh` from the
laptop reaches it by a stable name; the machine's repository holds its
install and its revert; the board's head shows two machines.

### 2. Each subscription logs in once on the machine, and the laptop's browser answers
Every Claude slot and Codex log in on the rented machine through the
browser-less flow: the CLI on the machine prints a URL and a code, the
laptop's browser — the slot's own Chromium profile, which `claude-acct
login` already routes to — opens it, and the owner completes it there,
captcha and all; the machine never runs a browser and never meets one. No
token file is copied between machines (the cold read of 2026-09-07: a
refresh token used from two machines can race and invalidate one side), so
each machine holds its own login for the same subscription and the
allowance stays the subscription's. The captcha's observed behaviour on
the laptop (filled, it is rejected; clicked outside, it passes) is a fact
of the laptop's record, not of this plan, and is written there.
Done means: before any other slot moves, one slot is logged in on both
machines and both logins are used and refreshed for a full day, then both
still work — that is the fact this plan rests on and it is proven first;
after it, every slot answers a `claude` call on the machine and `codex
exec` answers there; `claude-acct` on the machine sees the same slots the
laptop does; the machine's record names the flow and the trap list from
`docs/claude-multi-subscription.md` that applies.

### 3. The board serves from the machine, and the laptop's address still reaches it
`needle serve` runs on the rented machine over the one store, moved once at
a quiet moment with the service stopped on both sides; on the laptop the
address the desktop entry, the bar, the hooks and #41's notifications use
(`127.0.0.1:8480`) is the tunnel's end, so nothing on the laptop is
reconfigured and a session started on the laptop still reports to the one
board. The laptop's `needle serve` is disabled with its revert written.
Done means: the board opens on the laptop at its old address and shows the
same cards with their history; a session on the laptop and a session on the
machine both appear on it; the laptop's service is off and the machine's
record says how to bring the board back to the laptop in one command.

### 4. A lane runs where its ground is, and a window into it opens here
The rule that places work (`needle where`, `claude-acct`'s one rule) gains
the machine: a card whose project's ground is the laptop (the Omarchy
board) runs on the laptop; every other card runs on the rented machine
when it has headroom under #53's floor and on the laptop when it does not
and the laptop has. A lane on the machine is a session in a scope there,
in a terminal multiplexer instead of a compositor window; the runtime's
"open a window into a session" opens a terminal on the laptop attached to
that session over the tunnel, and "focus" brings that terminal forward
through the compositor as today. The proof that a window is open is the
multiplexer's word on the machine plus the compositor's on the laptop.
The projects' repositories are cloned on the machine and each lane's
worktree lives beside its clone as it does here.
Done means: on the fixture, a card placed by the rule lands on the machine
its ground names, and the card face says which machine; live, a Hello
Revenue card started from the laptop's board runs on the rented machine,
its window opens on the laptop, and its fold lands on origin as any lane's
does; an Omarchy card started the same way runs on the laptop; a card
started with no headroom anywhere is refused by #53's door with the
machine's numbers.

### 5. The measure exists before the move
The machine's memory high-water mark, the count of lanes killed by the
system on either machine, and a build's wall-clock (the frontend's `npm
ci` plus `vitest`, and `uv run pytest -q`) on the machine against the
laptop's, each written where the loop below reads them.
Done means: the three numbers exist for the laptop before item 3 moves the
board, and for the machine on its first day; the loop's command reads
them.
Hands out: execution — the three timings on each machine, run three times
and the median kept; verifies by re-running one of them by hand before the
number is written.

## Acceptance criteria

- The owner opens the board, starts a card, gets its notification, opens
  its window and reads its close without doing anything he did not do
  before, and does not know which machine ran it unless he looks.
- Every subscription works from both machines a day after its login, with
  no token file copied.
- An Omarchy card never runs off the laptop.
- The step from 32 GB to 64 GB is taken, or not, on the loop's numbers.

## Rulings

- **32 GB first, at a one-month term.** From the cold read of another
  make: the 5 GB floor is a floor, not a safe peak, and memory pressure
  measured is the only reason to pay for 64. Rejected: 64 GB from the
  start on the strength of the intent.
- **No token file crosses machines.** Rejected: laying `.credentials.json`
  and `auth.json` from the machine repository. A race on refresh would
  fail silently on the other machine, which is the class §5 mechanises
  against; one login per machine per slot costs one browser round each.
- **One board, on the machine.** Rejected: two boards, one per machine,
  reconciled. Two stores is the registry drift the doctrine refuses, and
  the laptop reaching one board over a tunnel costs nothing.
- **The laptop's own cards stay on the laptop.** An Omarchy card edits this
  machine; running it elsewhere would edit the wrong machine and report
  success.

## Deliberately not

- The account viewer in the bar (Omarchy #38): it reads the subscriptions
  through the laptop's own logins and the board over the network, and
  needs nothing from this plan.
- A second rented machine, or a GPU: nothing here needs one.
- Moving the projects' remotes: origin stays where it is; the machine is
  one more clone.

## Loop

We think a rented machine with the memory, reached over a tunnel, will let
the owner run as many lanes as the work needs without noticing where they
run, because every surface he touches stays on the laptop and only
execution moves. We look two weeks after item 4 lands: if any lane was
killed by the system on the machine, #53's floor is wrong for it; if the
owner once had to know which machine a session ran on to do his work, the
window or the notification is what changes; if a build on the machine is
slower than on the laptop, the disk under load is the finding and the
provider is what changes, at the one-month term. The memory high-water
mark over the two weeks decides 32 or 64.

Loop: no lane was killed by the system on the rented machine — command uv --project /home/dennis/Work/needle run needle lanes --killed --machine rented --count expect 0 by 2026-10-05 every 1d
Loop: the memory high-water mark on the rented machine over two weeks — command uv --project /home/dennis/Work/needle run needle where --high-water rented by 2026-10-05 every 1d
