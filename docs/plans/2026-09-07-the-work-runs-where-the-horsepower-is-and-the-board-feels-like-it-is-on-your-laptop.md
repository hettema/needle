# The work runs where the horsepower is, and the board feels like it is on your laptop

**Carries:** docs/slice-suggestions/done/2026-09-07-the-work-runs-where-the-horsepower-is-and-the-board-feels-like-it-is-on-your-laptop.md
**Status:** IN FLIGHT — started 2026-09-09 by the lane on card #83. The runtime knows a second machine and proves it on the fixture (item 4's fixture half, item 5's readers); the machine itself is not ordered yet, so items 1–3 and the live halves of 4 and 5 wait on the order, which is the owner's act — the lane ended its first turn on that question with the order written out below under *The order*. The owner opened the Netcup account the same evening.
**Written:** 2026-09-07, from Dennis: "My intent is to not be limited by horse power from my machine but still interface as if I'm on my machine." The bound: "up to 100 eur/month, cheaper better." On the flow, after the live pricing and a cold read of another make: "For the rest the flow looks good." On the one thing he raised: "how would we deal with captchas and stuff? Anthropic is throwing captchas nowadays" — answered in item 2: the browser step of every login stays on the laptop, so the rented machine never meets a captcha.
**Effort gate:** high — the mechanics are a machine record in a pattern that exists (`omarchy-machine`), a tunnel, one login per slot, and the runtime's session and window verbs taught a second machine; the judgment is where a lane runs (item 4's rule) and what must never move (the laptop's own cards), and the failure that would be silent — a token refreshed from two machines invalidating one — is what item 2 proves before anything else moves.
**Sequencing:** after #107 (the owner's word on 2026-09-09, "please sequence 83 to start after this lands": a walled lane gives its memory back and every lane's space carries the floor as its high mark, which the rented machine's admission and its kill count read), #53 (the floor the rented machine's admission rule reuses is #53's, read every beat) and #68 (a lane the machine ended comes back by itself, which on a second machine is the only way a dead lane returns at all — nobody is sitting at it). Items 1 and 2 can land and be proven before either; the runtime items wait.
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
**Deviated:** three of the four clauses hold and the fourth waits for the
fold; the image is Debian, not Arch. The owner ordered the RS 4000 G12 on
2026-09-09 (Netcup installed Debian 13 minimal; nothing the runtime needs
cares, since the tools are mise's and the user manager, `busctl`,
`journalctl` and `tmux` are Debian's own — reinstalling Arch from the
rescue system would cost hours and buy nothing; the machine's own record
carries the ruling). The laptop's key was laid with the emailed root
password through a terminal driver, the host's ED25519 fingerprint
matched Netcup's mail first, the root password was rotated and handed to
the owner once, and ssh is key-only since. Tailscale, as the Rulings said:
the owner made the tailnet that evening, the server is `rented` on it
(`rented.tail7a9c05.ts.net`, `100.111.233.23`) and the laptop `dh`, the
laptop's `ssh rented` reads the tunnel name, and the hostname is `rented`.
The record is `github.com/hettema/rented-machine`, cloned at
`~/Work/rented-machine` there, in the laptop's pattern with one difference
recorded in its tool: a file under `/etc` is a root-owned copy checked by
content, never a link, because sudo refused the linked sudoers file ("is
owned by uid 1001, should be 0") and locked the work user out until root
put a copy back. Its `machine check` printed `no drift` at 21:55Z. The
head's two machines: after the fold (origin/develop ec5b7bc, 2026-09-10
00:0xZ, dist rebuilt, needle-serve restarted, the shared store at 0017)
`needle machine add laptop --desktop --ground ~/Work/omarchy-machine` and
`needle machine add rented --host rented` registered both, and the served
board's head answered `laptop (here) 6.0 GB available, rented 30.4 GB
available` with the loop reading the rented machine over real ssh on every
pass and, once its clone was levelled to the fold, no complaint in the
journal. Every clause holds; **Met** in that reading. One thing the
evening taught, for item 3: the other machine's `needle` is its clone's,
so a fold that changes the wire is not live there until that clone is
levelled and `uv sync` run — the first pass after the fold read `needle
room` refused with a usage line, loud on the head, until `git pull` there;
the board's own `sync` should level every machine's clone at a fold.

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
In flight (2026-09-09, 21:50Z): what a Claude session shares on the laptop
— `settings.json`, the agents, skills, hooks and statusline — is linked on
the machine from the laptop's record cloned there, `~/.claude/CLAUDE.md`
resolves to Needle's HOW-WE-WORK (the one text), `claude-acct` is the
laptop's script linked with the same `accounts.json` and `roles.json`, and
`claude-acct init` laid the five slots, every one `NEEDS LOGIN`. The first
login, `hrclaude`, landed at 22:04Z through the browser-less flow as
written: `claude-acct login hrclaude` in a multiplexer session there
printed the sign-in link, the lane opened it in the laptop's hrclaude
Chromium profile, the owner authorised and pasted the code, and the lane
typed it into the waiting prompt — the first code, authorised a quarter of
an hour after its link, was refused with a 400 (they expire in minutes),
the second, pasted within a minute, was taken. No token file crossed: the
machine holds its own login for the same subscription. `claude -p` on that
slot there answered `ok`; the rule there answered the same slot as the
laptop's does ("Fable headroom on hrclaude, 53% used") once Omarchy's
allowance collector, which the rule calls and Debian lacks, was carried
into the machine's record (`docs/collector.md` there). The day's proof is
the machine record's `login-check`, read by the Loop line below from
2026-09-10; the laptop's own hrclaude login is the one the owner uses all
day, so its half of the proof is his ordinary work. Codex signed in on the
machine on 2026-09-10 (14:51Z) by its own device-code flow — a code
printed there, entered by the owner in the laptop's browser, no token
file crossing — once "device code authorization for Codex" was switched
on in the ChatGPT account's security settings, which the first code's
refusal named; `codex exec` there answered the same minute, and its
configuration is the laptop's record's, linked (the machine's
`docs/install.md`, step 8). What remains of this item: the other four
Claude slots, each the same round through the laptop's browser, after the
day has shown the first pair refreshing apart.

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
In flight (2026-09-10; the fixture half folded at 13:0xZ, origin/develop
71d1bbe, the page rebuilt, the served board restarted and the shared
store at 0018): the half the fixture proves is on the trunk. The gap it closes was found reading item 3 cold: once the store is
on the machine, a session on the laptop running `needle row`, `close` or
`fold` would open the laptop's copy and write a row the board never
reads. So a machine that is not the board's hands every verb that opens
the board's store — `card`, `row`, `close`, `reading`, `triage`, `fold`,
`watercooler`, `lanes`, `sync`, `add`, `projects` and the rest — to the
board's machine over the wire the board already reads it by: `needle
board rented` writes which machine that is (`~/.local/share/needle/
board.json`, beside the store it is about), `runtime/machine.py::forward`
runs the verb there with its output flowing back, `needle serve` on such
a machine refuses, and `needle board here` takes the board back. The fold
is the one verb whose git must run where the lane is, so the board's
`fold` pushes through the wire (`needle push --worktree` on the machine
that holds the lane, `Runtime.fold`), and every other machine's clone is
levelled on the trunk's beat outside the loop's lock, a stale one said on
that machine's line of the head and never as the board's own checkout's
state (`Runtime.level_elsewhere`, `needle level`, `MachineRoom.clones`;
the seam the first evening showed; the finding is a row per machine and
project in the store, so the head and `needle machines` read one record).
`needle machine host NAME HOST`
rewrites how the board reaches a machine once it has moved, proved by
that machine's id as `machine add` proves it. The registry verbs
(`machines`, `machine …`, `where --high-water`) are the board's too and
cross with the rest; a machine that hands its verbs away answers the
board for itself alone, never fanning out over the rows it copied. Proven
on the floor: `tests/runtime/test_board_elsewhere.py`; read cold on its
first commit by the other make and then for the completeness of each
round's repairs (the record's eighth to twelfth passes, thirty-three
findings; the loop for this half ended under §13's three-passes rule
with one corner of the clone record filed as a defect and the revert
script's last five repaired for the rehearsal to prove; the record says
which and why). The live half — the
store moved at a quiet moment with both services stopped, the laptop's
`127.0.0.1:8480` made the tunnel's end by a socket unit that proxies to
the machine's `tailscale serve`, the laptop's own `needle-serve` disabled
with its revert, sshd on the laptop for the board's way back to the
screen — is a procedure in the rented machine's record (`docs/board.md`
there, the revert in `docs/revert.md`), and runs when no lane is on the
laptop's board, which the day's lanes decide.

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
**Deviated:** the fixture half is met and the live half waits on the
machine. On the floor (`tests/runtime/test_machines.py`): a card in the
laptop's own record starts on the laptop while the rented floor has more
room; every other card starts on the rented floor through its own
`needle start` over the stand-in `ssh`, registers there and nowhere else,
is listed on the one list stamped `rented`, and its window on the desktop
runs `ssh -t rented -- tmux new-session -A -s needle-lane-<card> …` with
the multiplexer's word read back as the second half of the proof; both
floors full is refused with both machines' numbers, and a rented floor
that does not answer falls back to the laptop with room. The face says
`on rented` in the lane section only when the board knows more than one
machine (`board/lane.py`, `LaneFacts.many_machines`). The live clauses —
a Hello Revenue card from the served board, its fold on origin, an Omarchy
card on the laptop — are the resuming session's, and they come after item
3, as the plan's order says and the machine's first evening showed why: a
lane on the rented machine runs, but every `needle` verb it calls there
(`card`, `row`, `watercooler`, `close`, `fold`) opens that machine's own
store, and its hooks post to `127.0.0.1:8480`, which is nothing there.
Only once the board and its store serve from that machine (item 3) is a
lane there a lane like any other; until then the live half of this item is
the wire — both machines registered, the head naming both, the loop
reading the rented machine every pass over real `ssh`, the Start preview
choosing it for a Hello Revenue card — which the fold's evening read: with
both registered, Hello Revenue #121's Start door read `Start · hrclaude on
rented`, placed by the rented machine's room (30.4 GB) and its own rule
(hrclaude, 53% of Fable used, the same subscription reading as the
laptop's), and Needle #81's the same. Because that Start would have put a
lane on a machine with no board to write to, the rented machine was taken
off the board again the same minute (`needle machine rm rented`, the
removal guards passing: nothing live on it) and the board places every
card on the laptop as before; item 3 registers it again. The card's WAITS
row says so.

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
**Deviated:** the readers exist and the laptop's numbers are being taken;
the machine's wait on item 1. The loop's two commands run: `needle lanes
--killed --machine <name> --count` counts the deaths the board named as
the memory killer's, against the machine each session's slot record names
(`infrastructure/store.py::killed_on`), over the last day; `needle where
--high-water <name>` prints the day the board saw the least memory
available on that machine over the last two weeks, from a mark the loop
writes on every pass (`high_water`, one row per machine per day). Build
timings are written by hand with `needle machine timing <name> <what>
<seconds>` and read back by `needle machines --json`. The laptop's
frontend numbers exist: the execution role ran `npm ci` three times (2.00,
3.29, 1.18 s; median 2.00) and `vitest run` three times (14.66, 11.64,
10.73 s; median 11.64, 76 tests green) in the main checkout on the evening
of 2026-09-09, and the lane re-ran one of each by hand before writing them
(3.2 s and 20.4 s, on a laptop then running two other lanes' suites). The
backend number does not exist yet, and the reason is itself the plan's
finding: three attempts at `uv run pytest -q` in the main checkout that
evening — the hand's, and two of the lane's own — were each killed by the
memory killer or the harness while two other lanes ran their suites, the
last with the lane's whole process group (48 processes at 22:03Z), on a
laptop reading 2 GB available — part of which, the evening's last finding,
was test floors sitting in `/tmp`, a filesystem in memory (filed as a
defect: `docs/slice-suggestions/2026-09-09-a-suites-test-floors-never-take-the-memory-the-lanes-need.md`).
The number is taken on a quiet laptop by the resuming session, once, then
twice more, and written with `needle machine timing laptop pytest
<seconds>` beside the two above, which were written at the fold (`npm ci
2.0`, `vitest 11.6`, read back by `needle machines --json`). The laptop's
memory high-water mark is the board's own reading from the fold on; that
evening's sampler read 1.9 GB available at its lowest.

## Terrain

What the first session built, for the one that resumes with a machine to
reach (every path below is in Needle's repository unless said):

- **A machine is a row.** `domain/machine.py` — `Machine` (name, the
  kernel's `machine_id`, the `host` others reach it by, `desktop`, the
  `ground` project that is its own record, the `command` that runs
  `needle` there), `MachineRoom` (what the head shows per machine),
  `HighWater`, `Timing`, and `choose_machine`, the pure rule of item 4.
  Registered by `needle machine add NAME [--host H] [--desktop] [--ground
  PATH]`, which reads the identity from the machine itself (`ssh host cat
  /etc/machine-id`) so a row is never written for a machine the board
  cannot reach; `needle machines` lists them with their rooms. The board
  tells which row is itself by `runtime/machine.py::machine_id`, never by
  hostname; a board with no rows is a one-machine board whose machine is
  the desktop, which is every board until now.
- **Another machine's runtime is asked through its own `needle`.**
  `runtime/remote.py::Remote` runs `needle <verb> --json` there over `ssh`
  (`runtime/machine.py::run_line`: `ssh -o BatchMode=yes -o
  ConnectTimeout=5 <host> -- bash -lc '<command> <verb> --json'`, with a
  control socket under `$XDG_RUNTIME_DIR` so a pass pays one handshake)
  and validates the answer into the same domain value the verb answers
  here. The verbs the wire uses: `sessions`, `where`, `start
  [--windowless]`, `stop [--keep-handoff]`, `move`, `resume`, `rescope`,
  `room [--hold]`, `scopes --held|--pids|--stop`, `cause`, `ended`,
  `boots`, `limits`, `expire-handoff`, `show`, `tell`. `runtime/service.py`
  routes every session-, group- and screen-bound call by the machine that
  holds it (`machine_of`, `desktop`), stamps `Placement.machine` and
  `Session.machine`, and copies each remote answer into the board's own
  store (`_stamped`), since the other machine's `needle` writes only its
  own ledger.
- **The screen is the desktop's.** `runtime/windows.py` functions take
  `host=`; a window into a session on another machine is `via_tmux`: the
  desktop's terminal runs `ssh -t <host> -- tmux new-session -A -s
  needle-<kind>-<card> bash -lc '<attach>'`, and the proof is the
  compositor's window plus `tmux has-session` on that machine
  (`tmux_has`). `tell` and `show` go through the desktop's own `needle`
  when the board runs elsewhere (item 3's territory, written, unproven
  live).
- **A machine that is not the board's hands its board verbs over.**
  `needle board NAME` writes `domain/machine.py::BoardMachine` (name,
  host, command) to `infrastructure/paths.py::board_path`; `api/cli.py::
  main` reads it (`runtime/machine.py::board_elsewhere`) before any verb
  marked `board=True` opens the store and runs the verb there instead
  (`runtime/machine.py::forward`: the same `ssh … bash -lc` line, stdin
  closed, output flowing back, exit 255 said in the board's name); the
  runtime verbs are never forwarded, since the board asks them of this
  machine. `fold` from a lane names its worktree on the way over, and the
  board's `Runtime.fold` routes the push back to `lane_machine(worktree)`
  through `Remote.push`; `Runtime.level` levels the board's own checkout
  under the loop's lock and `Runtime.level_elsewhere` every other
  machine's through `Remote.level` outside it (`api/loops.py::
  level_clones_now`), the finding a row per machine and project in the
  store (`Store.record_clones`, `Store.clones`, migration 0018) read into
  `MachineRoom.clones` for the head's machine line and `needle machines`. `needle machine host` sets a registered
  row's host after the id read over ssh matches the row's. `Runtime.
  machines` keeps this machine's own row alone while `board.json` names
  another, so a lane recorded under its name still routes here and it
  never fans out over the rows it copied. `api/cli.py::_absolute` resolves
  a caller-relative path before it crosses: the fold's worktree, a
  project's path, a machine's ground, `where --repo`.
- **The loop reads every machine on every pass.** `api/loops.py::
  headroom_now` reads `Runtime.rooms(hold=True)`, sets the floor's high
  mark on every machine's lane scopes, writes the day's high-water mark
  per machine, and gives the head `MachineState.machines`; `_placement`
  is per project (`repo=`), `_boots` per machine, the sweep stops a group
  on the machine it was read on, deaths are named by the machine's own
  journal (`needle cause` there). The dial's beat is held only when no
  machine has room (`api/dial.py::_full`).
- **The floor stands in for the second machine.** `tests/floor.py::
  Floor.lay_host(name)` lays a second floor under the first's root with
  its own slots, registries, memory, store and machine id, reached by the
  stand-in `tests/fakes/bin/ssh` under `name` (exit 255 for a host never
  laid, or after `host_down`); `tests/fakes/bin/tmux` records sessions;
  the launcher stand-in runs an `exec ssh -t …` attach so the
  multiplexer's half of the proof is read. `needle` on the other floor is
  the venv's own script. Migration 0017: `machines`, `high_water`,
  `timings`, `session_slots.machine`.

**The order** (the owner's act; the pick and the bound are already his):
Netcup RS 4000 G12 — 12 dedicated cores, 32 GB DDR5 ECC, 1 TB NVMe — at
the one-month term, in Nuremberg, ex VAT under reverse charge (a
VAT-registered Swedish buyer; confirmed at order time). Image: Arch Linux
if Netcup's list offers it, else Debian 12 and the first session installs
Arch from the rescue system, since the laptop's tooling (`machine
install`, `claude-acct`, `needle`, mise) is Arch's. At order time or in
the panel afterwards: the laptop's public key (`~/.ssh/id_ed25519.pub`)
as the root key. What the resuming session needs from the owner, in one
message: the server's IPv4 address, whether the key was set (else the
root password, to be changed on first login), and which image was chosen.

**The first session on the machine** (item 1, in order): `ssh root@<ip>`
by key; make user `dennis` with the same uid as here (1001) and the same
home layout (`~/Work/<project>` for every project on the board, cloned
from origin); install Tailscale on both machines and name the rented one
`rented`, so `ssh rented` works from the laptop and `ssh laptop` from the
machine — the reason for Tailscale over an SSH tunnel is recorded under
Rulings; clone `omarchy-machine`'s pattern into a new repository
`~/Work/rented-machine` whose `home/` holds what the machine needs
(`machine install` lays links, `machine check` reads drift, a `revert`
section says how to take the board back to the laptop), and `needle add`
it on the board; then `needle machine add rented --host rented` on the
laptop and `needle machine add laptop --desktop --ground
~/Work/omarchy-machine`. Item 2 follows: one slot's `claude login` on the
machine through the browser-less flow, the laptop's browser answering,
then a day of use on both before the other slots move.

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
- **Another machine is asked through its own `needle`, never read as
  files or processes from here** (the lane's ruling, 2026-09-09). The
  board reads what runs from `/proc`, the registries, the journal and the
  user manager, none of which cross a wire as files; a runtime on the
  machine that holds them answers for them, over the typed JSON edge every
  verb already has. Rejected: mounting the other machine's filesystem and
  reading it with the same code (a process walk over `/proc` is a round
  trip per file, and a pid there is not a pid here); a second protocol
  beside the verbs (two ways to say one thing).
- **The board's store is the one record; the other machine's `needle`
  keeps only its own ledger.** A remote `start` or `move` writes where the
  session runs into that machine's default store, and the board's runtime
  copies the answer into the board's store as its own record. Rejected:
  pointing the other machine's `needle` at the board's store (SQLite over
  a network filesystem corrupts), and no store there at all (its launcher
  records where it put a session, and that record is what its own
  `window` and `stop` read).
- **A window into a session on another machine goes through a
  multiplexer there.** The desktop's terminal is `ssh -t` into `tmux
  new-session -A`, so a dropped tunnel — the laptop's lid — ends the
  viewer and never the session, and reattaching finds the same session.
  Rejected: a bare `ssh -t claude attach`, which the lid would end with
  the attach's own exit.
- **Tailscale, not an SSH tunnel, once the machine exists** (to prove in
  item 1). The board on the rented machine must reach the laptop's screen
  (windows, focus, notifications go to the desktop's own `needle`) and the
  laptop must reach the board; a single `ssh -R`/`-L` tunnel is one
  process on the laptop that its sleep kills, and Tailscale gives both
  machines a stable name in both directions and reconnects itself. If the
  live proof shows Tailscale cannot be installed or is refused by the
  provider, the SSH tunnel is the fallback and this ruling is rewritten
  with why.
- **On a one-machine board nothing changes on the face.** The machine's
  name is shown on a lane and on the Start preview only when the board
  knows more than one machine, and the head lists machines only then;
  every existing test reads as before. Why: the acceptance says he does
  not know which machine ran a card unless he looks, and on one machine
  there is nothing to look at.

- **A machine that is not the board's runs its board verbs on the
  board's machine, over the wire the board reads it by** (the lane's
  ruling, 2026-09-10). The board's store is one file on one machine, and
  the sessions that write it run on both; the verbs that open it are
  `needle`'s, so `needle` on the other machine hands them across and the
  words, the exit code and the files they name (a review's path under
  `docs/reviews/`, a plan's) mean the same there because every machine
  lays the projects out the same. Rejected: an HTTP endpoint per verb on
  the board (the hook's and `start-card`'s way), which is a second edge
  to keep typed for twenty verbs that already have one; the store over a
  network filesystem (SQLite corrupts); a store per machine reconciled
  later (the registry drift the doctrine refuses, and the fold's row
  would be on the wrong side). The fold is the exception that proves the
  rule: its git runs where the worktree is, so the board asks it back
  over the wire as one more runtime verb (`push`), the same way it asks
  for a lane's edits.

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
Loop: the slot that logged in on the rented machine through the laptop's browser still answers there a day later, refreshed apart from the laptop's login of the same subscription — command ssh rented login-check hrclaude expect ok by 2026-09-12 every 1d
