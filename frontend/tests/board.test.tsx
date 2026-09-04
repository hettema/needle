import { describe, expect, it, vi, beforeEach } from "vitest";
import { cleanup, render, screen, within, waitFor, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, type DoorName } from "../src/api";
import { PROJECT, board, detail, language } from "./fixture";
import type { BoardState, CardDetail } from "../src/types/board";
import type { Place } from "../src/types/card";
import type { DoorResult, Lane } from "../src/types/lane";
import type { Project } from "../src/types/project";
import type { ClaimCount } from "../src/types/board";
import type { EvidenceClass, VerdictLine, VerdictsRuled } from "../src/types/verdict";

const api = vi.hoisted(() => ({
  getBoard: vi.fn<(slug: string) => Promise<BoardState>>(),
  moveCard: vi.fn<(slug: string, number: number, to: Place) => Promise<BoardState>>(),
  getCard: vi.fn(),
  getFile: vi.fn(),
  getProjects: vi.fn<() => Promise<Project[]>>(),
  openDoor: vi.fn<(slug: string, number: number, door: DoorName, body?: object) => Promise<DoorResult>>(),
  openIdea: vi.fn<(slug: string, text: string) => Promise<DoorResult>>(),
  openPlan: vi.fn<(slug: string, numbers: number[]) => Promise<DoorResult>>(),
  acceptClass: vi.fn<(slug: string, evidenceClass: EvidenceClass) => Promise<VerdictsRuled>>(),
  streamUrl: (slug: string) => `/api/projects/${slug}/stream`,
}));

vi.mock("../src/api", async () => {
  const real = await vi.importActual<typeof import("../src/api")>("../src/api");
  return { ...real, ...api };
});

import { App } from "../src/App";

const SLUG = PROJECT.slug;
const SECOND: Project = { slug: "needle", name: "Needle", path: "/srv/needle", registered_at: "2026-09-04T07:00:00+00:00" };

/** The head's breakdown for one word, as `{claim: count}`. */
function claims(entries: [string, number][]): ClaimCount[] {
  return entries.map(([claim, count]) => ({ claim: claim as ClaimCount["claim"], count, label: claim }));
}

/** A board whose head counts these claims, with the cards carrying them. */
function withClaims(b: BoardState, word: "yours" | "broken" | "live", entries: [string, number][]): BoardState {
  b.attention = { ...b.attention, [word]: claims(entries) };
  return b;
}

function cardOf(b: BoardState, number: number) {
  for (const column of b.columns) for (const group of column.groups) for (const card of group.cards) if (card.number === number) return card;
  throw new Error(`no #${number}`);
}

function upNextOrder(): number[] {
  const column = document.querySelector('[data-column="Up next"]');
  if (!column) throw new Error("no Up next");
  return Array.from(column.querySelectorAll<HTMLElement>("article[data-card]")).map((el) => Number(el.dataset["card"]));
}

beforeEach(() => {
  // Reset, not clear: a one-shot answer queued by an earlier test would otherwise outlive it.
  api.getProjects.mockReset().mockResolvedValue([PROJECT]);
  api.getBoard.mockReset().mockResolvedValue(board());
  api.getCard.mockReset().mockImplementation((_slug: string, number: number) => Promise.resolve(detail(number)));
  api.moveCard.mockReset();
  api.openDoor.mockReset();
  api.openIdea.mockReset();
  api.openPlan.mockReset();
  api.acceptClass.mockReset();
  window.history.replaceState(null, "", "/");
});

/** #253 with a lane: a live session on alpha, the doors a working lane offers. */
function withLane(state: Lane["state"], sentence: string, question: string | null = null, windowOpen = false): CardDetail {
  const d = detail(253);
  const session = {
    slot: "alpha",
    config_dir: "/x/alpha",
    short_id: "aaaa0001",
    session_id: "aaaa0001-0000-4000-8000-000000000000",
    kind: "background" as const,
    name: "card-253-every-metered-kilowatt-is-billed",
    cwd: "/srv/harbourmaster/.claude/worktrees/card-253-every-metered-kilowatt-is-billed",
    worktree: "/srv/harbourmaster/.claude/worktrees/card-253-every-metered-kilowatt-is-billed",
    state: state === "working" ? ("working" as const) : ("done" as const),
    recorded: "working",
    detail: "",
    pid: state === "ended" ? null : 4242,
    scope: null,
    model: "fable" as const,
    effort: "medium" as const,
    stale: false,
    wall: null,
    intent: "",
    created_at: null,
    updated_at: null,
  };
  d.lane = {
    card_number: 253,
    name: session.name,
    path: session.worktree,
    state,
    sentence,
    session,
    question,
    said: question,
    said_at: null,
    discussing: [],
    window_open: windowOpen,
    hands_on_since: null,
    died: state === "ended" ? "the journal says: Killed process 4242" : null,
    moved: null,
    folded: false,
    trunk_synced: false,
    main_synced: false,
    edits: [],
    declared: [],
    colliding: null,
  };
  d.summary.lane_state = state;
  d.summary.state = {
    word: state === "asking" ? "asking you" : state === "ended" ? "lane ended" : `${state} · fable on alpha`,
    meaning: state === "asking" ? "yours" : state === "ended" ? "broken" : "live",
    detail: question ? `“${question.split("\n").filter(Boolean).slice(-1)[0]}”` : sentence,
    loop: null,
    door: null,
    hint: "open to see",
  };
  const open = (label: string, why: string) => ({ offered: true, label, why });
  const closed = (label: string, why: string) => ({ offered: false, label, why });
  d.doors = {
    ...d.doors,
    start: closed("Start", `A session already has hands on it: ${sentence}`),
    watch: state === "ended" ? closed("Watch", "No live session to watch.") : windowOpen ? open("Focus its window", "Brings the open window into this session forward, through the compositor.") : open("Watch", "Opens a window into the live session; closing it ends nothing."),
    answer: state === "asking" ? open("Answer", "Your sentence resumes the lane with it; one live copy stays.") : closed("Answer", "The session is working; answer it when it stops."),
    look: state === "ended" ? open("Look", "A fresh session in the worktree from the transcript; its first line says so.") : closed("Look", "The session is live; watch it instead."),
    resume: state === "ended" ? open("Resume", "Resumes the lane's session where the rule says.") : closed("Resume", "The session is live; watch it instead."),
    stop: state === "ended" ? closed("Stop", "No background session to stop.") : open("Stop", "Ends the session through its own slot and says where the card is then."),
  };
  return d;
}

async function renderBoard() {
  render(<App />);
  await screen.findByText("Every metered kilowatt is billed");
}

describe("the board at rest", () => {
  it("shows every column, the archive furled, groups, and what each card is", async () => {
    await renderBoard();
    expect(screen.getByRole("heading", { name: "Backlog" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Up next" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Executed — click to unfurl" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Executed" })).not.toBeInTheDocument();
    expect(screen.getByText("Next to plan")).toBeInTheDocument();
    expect(screen.getAllByText("Skipper-facing quality", { selector: "h3" })).toHaveLength(2);
    expect(screen.getByText("gone")).toBeInTheDocument();
    expect(screen.getAllByText("note")).toHaveLength(4);
    expect(screen.getByText("new")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Broken/ })).toHaveTextContent("Broken 2");
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);
    // Position is rank: no card carries a rank digit any more.
    expect(document.querySelector(".rank")).toBeNull();
  });

  it("names the project in the window's tab", async () => {
    await renderBoard();
    expect(document.title).toBe(`${PROJECT.name} · Needle`);
  });

  it("unfurls a rail into its column and back", async () => {
    await renderBoard();
    await userEvent.click(screen.getByRole("button", { name: "Executed — click to unfurl" }));
    expect(screen.getByRole("heading", { name: "Executed" })).toBeInTheDocument();
    expect(screen.getByText("The office runs its own checks, nightly")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Furl Executed" }));
    expect(screen.getByRole("button", { name: "Executed — click to unfurl" })).toBeInTheDocument();
  });
});

describe("moving a card by keyboard", () => {
  it("lifts, shows where it lands with the new rank, and drops where the preview said", async () => {
    api.moveCard.mockResolvedValue(board([241, 253, 228, 237, 174]));
    await renderBoard();
    const card = screen.getByText("#241").closest("article") as HTMLElement;
    act(() => card.focus());
    expect(screen.getByText(/lift/)).toBeInTheDocument();
    fireEvent.keyDown(card, { key: " " });
    expect(card.className).toContain("ghost");
    fireEvent.keyDown(card, { key: "ArrowUp" });
    expect(screen.getByText(/lands here/)).toHaveTextContent("#241 lands here — rank 1");
    fireEvent.keyDown(card, { key: " " });
    await waitFor(() => expect(api.moveCard).toHaveBeenCalledWith(SLUG, 241, { column: "Up next", group: null, position: 0 }));
    await waitFor(() => expect(upNextOrder()).toEqual([241, 253, 228, 237, 174]));
    expect(screen.queryByText(/lands here/)).not.toBeInTheDocument();
  });

  it("walks into the next column and a named group", async () => {
    api.moveCard.mockResolvedValue(board());
    await renderBoard();
    const card = screen.getByText("#253").closest("article") as HTMLElement;
    act(() => card.focus());
    fireEvent.keyDown(card, { key: " " });
    fireEvent.keyDown(card, { key: "ArrowLeft" });
    expect(screen.getByText(/lands here/)).toHaveTextContent("#253 lands here — in Season opening");
    fireEvent.keyDown(card, { key: " " });
    await waitFor(() => expect(api.moveCard).toHaveBeenCalledWith(SLUG, 253, { column: "Planned", group: "Season opening", position: 0 }));
  });

  it("cancels with escape and writes nothing", async () => {
    await renderBoard();
    const card = screen.getByText("#241").closest("article") as HTMLElement;
    act(() => card.focus());
    fireEvent.keyDown(card, { key: " " });
    fireEvent.keyDown(card, { key: "ArrowUp" });
    fireEvent.keyDown(card, { key: "Escape" });
    expect(screen.queryByText(/lands here/)).not.toBeInTheDocument();
    expect(api.moveCard).not.toHaveBeenCalled();
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);
  });
});

describe("a write that fails", () => {
  it("leaves the card where it was, says why in the store's words, and offers a retry", async () => {
    api.moveCard.mockRejectedValueOnce(new ApiError(500, "The store refused: OperationalError: database is locked"));
    api.moveCard.mockResolvedValueOnce(board([241, 253, 228, 237, 174]));
    await renderBoard();
    const card = screen.getByText("#241").closest("article") as HTMLElement;
    act(() => card.focus());
    fireEvent.keyDown(card, { key: " " });
    fireEvent.keyDown(card, { key: "ArrowUp" });
    fireEvent.keyDown(card, { key: " " });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Not moved. The store refused: OperationalError: database is locked The card is where it was.");
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);
    expect(document.querySelector(".facts")).toHaveTextContent("1 write failed — see the card");
    expect((screen.getByText("#241").closest("article") as HTMLElement).dataset["meaning"]).toBe("broken");
    await userEvent.click(within(alert).getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(api.moveCard).toHaveBeenCalledTimes(2));
    expect(api.moveCard).toHaveBeenLastCalledWith(SLUG, 241, { column: "Up next", group: null, position: 0 });
    await waitFor(() => expect(upNextOrder()).toEqual([241, 253, 228, 237, 174]));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("the open card", () => {
  it("opens in place with the five sections in order, an empty record that says so, and only honest actions", async () => {
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    await waitFor(() => expect(api.getCard).toHaveBeenCalledWith(SLUG, 253));
    const card = await waitFor(() => {
      const el = screen.getByText("#253").closest("article") as HTMLElement;
      expect(el.className).toContain("open");
      return el;
    });
    await within(card).findByText("What it makes true");
    const headings = Array.from(card.querySelectorAll(".sec-h")).map((h) => h.firstChild?.textContent?.trim());
    expect(headings).toEqual(["What it makes true", "The brief", "The record", "The plan", "History"]);
    // The doors sit directly under the title, before the summary (plan 04, item 2).
    const body = card.querySelector(".open-body") as HTMLElement;
    expect(body.firstElementChild?.className).toBe("acts");
    expect(within(body.firstElementChild as HTMLElement).getByRole("combobox", { name: "Move to" })).toBeInTheDocument();
    expect(within(card).getByText(/Nothing has been done to this card/)).toBeInTheDocument();
    expect(within(card).getByText("TODAY")).toBeInTheDocument();
    expect(within(card).getByText("docs/plans/2026-09-03-every-metered-kilowatt-is-billed.md")).toBeInTheDocument();
    expect(within(card).getByText("Born")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Open the plan" })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Copy path" })).toBeInTheDocument();
    expect(within(card).getByRole("combobox", { name: "Move to" })).toHaveValue("Up next");
    // Before the runtime's first read no door opens, and Start says why rather than vanishing.
    const start = within(card).getByText("Start");
    expect(start).toHaveAttribute("aria-disabled", "true");
    expect(start).toHaveAttribute("title", expect.stringContaining("the runtime has not read this board yet"));
    expect(within(card).queryByRole("button", { name: /Watch|Answer|Stop|Look|Resume|Discuss/ })).not.toBeInTheDocument();
    expect(card.closest("section")?.className).toContain("wide");
    expect(window.location.hash).toBe("#card-253");
  });

  it("moves through the Move to select and lands at the end of the column", async () => {
    api.moveCard.mockResolvedValue(board());
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const select = await screen.findByRole("combobox", { name: "Move to" });
    await userEvent.selectOptions(select, "Not now");
    await waitFor(() => expect(api.moveCard).toHaveBeenCalledWith(SLUG, 253, { column: "Not now", group: null, position: 1000000 }));
  });
});

describe("the doors", () => {
  it("offers Start with the slot and model the rule named, opens it, and shows the evidence", async () => {
    const d = detail(253);
    d.doors = {
      ...d.doors,
      start: { offered: true, label: "Start · fable on alpha", why: "Fable headroom on alpha (12% of Fable used)" },
      discuss: { offered: true, label: "Discuss", why: "A fresh conversation about this card, never hands on its tree." },
      placement: { slot: "alpha", model: "fable", config_dir: "/x", why: "Fable headroom on alpha (12% of Fable used)" },
      collision: { verdict: "clear", sentence: "No running lane or trunk session touches this plan's files.", files: [], cards: [] },
    };
    api.getCard.mockResolvedValue(d);
    api.openDoor.mockResolvedValue({ door: "start", said: "Started aaaa0001, fable on alpha, at medium, in card-253-every-metered-kilowatt-is-billed, in needle-card-253.scope" });
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const start = await screen.findByRole("button", { name: "Start · fable on alpha" });
    expect(start).toHaveAttribute("title", "Fable headroom on alpha (12% of Fable used)");
    expect(screen.getByRole("button", { name: "Discuss" })).toBeInTheDocument();
    await userEvent.click(start);
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 253, "start", {}));
    expect(await screen.findByText(/Started aaaa0001, fable on alpha/)).toBeInTheDocument();
  });

  it("names a collision, closes Start and offers Start anyway with the reason", async () => {
    const d = detail(253);
    const sentence = "#241's lane is editing engine/metering.py right now.";
    d.doors = {
      ...d.doors,
      start: { offered: false, label: "Start", why: `Lane collision — ${sentence}` },
      start_anyway: { offered: true, label: "Start anyway · fable on alpha", why: `Overrides the collision with its reason in front of you: ${sentence}` },
      collision: { verdict: "collides", sentence, files: ["engine/metering.py"], cards: [241] },
    };
    api.getCard.mockResolvedValue(d);
    api.openDoor.mockResolvedValue({ door: "start", said: "Started; collision overridden" });
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const anyway = await screen.findByRole("button", { name: "Start anyway · fable on alpha" });
    expect(screen.getByText("Start")).toHaveAttribute("title", `Lane collision — ${sentence}`);
    expect(screen.getByText(sentence)).toBeInTheDocument();
    await userEvent.click(anyway);
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 253, "start", { anyway: true }));
  });

  it("shows a working lane as one live word on the resting card, and Watch and Stop on the open one", async () => {
    const sentence = "Working, fable on alpha, hands on for 12 min.";
    const b = board();
    const card = cardOf(b, 253);
    card.lane_state = "working";
    card.state = { word: "working · 12 min · fable on alpha", meaning: "live", detail: null, loop: null, door: null, hint: "open to see" };
    api.getBoard.mockResolvedValue(b);
    api.getCard.mockResolvedValue(withLane("working", sentence));
    api.openDoor.mockResolvedValue({ door: "watch", said: "Window org.omarchy.board-watch-card-253 opened into aaaa0001; closing it ends nothing." });
    await renderBoard();
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    expect(resting.dataset["meaning"]).toBe("live");
    expect(within(resting).getByText("working · 12 min · fable on alpha")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const watch = await screen.findByRole("button", { name: "Watch" });
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Look" })).not.toBeInTheDocument();
    expect(screen.getByText("Start")).toHaveAttribute("aria-disabled", "true");
    // Every door he would expect on a card with a lane says why it is closed, in text.
    const closedDoors = document.querySelector(".closed-doors") as HTMLElement;
    expect(closedDoors).toHaveTextContent("Look — The session is live; watch it instead.");
    expect(closedDoors).toHaveTextContent("Answer — The session is working; answer it when it stops.");
    expect(closedDoors).toHaveTextContent("Resume — The session is live; watch it instead.");
    await userEvent.click(watch);
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 253, "watch", {}));
    expect(await screen.findByText(/closing it ends nothing/)).toBeInTheDocument();
  });

  it("offers Focus its window in Watch's place while a window is open, and it proves the focus", async () => {
    api.getCard.mockResolvedValue(withLane("working", "Working, fable on alpha, hands on for 12 min.", null, true));
    api.openDoor.mockResolvedValue({ door: "watch", said: "Focused org.omarchy.board-watch-card-253; the compositor reports org.omarchy.board-watch-card-253 active." });
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const focus = await screen.findByRole("button", { name: "Focus its window" });
    expect(screen.queryByRole("button", { name: "Watch" })).not.toBeInTheDocument();
    expect(document.querySelector(".closed-doors")).not.toHaveTextContent("Watch");
    await userEvent.click(focus);
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 253, "watch", {}));
    expect(await screen.findByText(/the compositor reports org.omarchy.board-watch-card-253 active/)).toBeInTheDocument();
  });

  it("marks a card whose evidence is gone as doubted, on the resting card and the open one, and counts it", async () => {
    const words = "the board doubts this: no live session has hands on its worktree (its worktree is gone from disk)";
    const b = board();
    const card = cardOf(b, 253);
    card.standing = { actor: "machine", evidence: "hands-on", state: "doubted", words };
    card.state = { word: "doubted", meaning: "broken", detail: words, loop: null, door: null, hint: "open to decide" };
    card.claims = ["doubted"];
    withClaims(b, "broken", [["doubted", 1]]);
    const d = detail(253);
    d.summary.standing = card.standing;
    api.getBoard.mockResolvedValue(b);
    api.getCard.mockResolvedValue(d);
    await renderBoard();
    expect(screen.getByRole("button", { name: /^Broken/ })).toHaveTextContent("Broken 1");
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    expect(resting.dataset["meaning"]).toBe("broken");
    expect(within(resting).getByText("doubted")).toBeInTheDocument();
    expect(within(resting).getByText(words)).toBeInTheDocument();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const open = await waitFor(() => {
      const el = screen.getByText("#253").closest("article") as HTMLElement;
      expect(el.className).toContain("open");
      return el;
    });
    await within(open).findByText("What it makes true");
    expect(within(open).getAllByRole("status").map((el) => el.textContent).join(" ")).toContain(words);
    expect(within(open).getByText("doubted · hands-on")).toBeInTheDocument();
  });

  it("batches the signals only the owner can read into one list with one click each way per card", async () => {
    const b = board();
    withClaims(b, "yours", [["signal asking", 2]]);
    b.asks = [
      { number: 259, title: "The fuel pontoon takes cards, live", what: "Did the first card payment at the pontoon go through?", due: "2026-09-11", kind: "owner", evidence: null },
      { number: 134, title: "The office runs its own checks, nightly", what: "Did the nightly check email name a real event?", due: "2026-09-11", kind: "session", evidence: "no check email since the close; Friday's run decides it" },
    ];
    api.getBoard.mockResolvedValue(b);
    api.openDoor.mockResolvedValue({ door: "signal", said: "Read as delivered; moved to Done." });
    await renderBoard();
    expect(screen.queryByText(/only you can read these signals/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Your move/ }));
    await userEvent.click(screen.getByRole("button", { name: "2 signal asking" }));
    const list = screen.getByRole("region", { name: /2 shipped cards wait on your reading/ });
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("#259");
    expect(rows[0]).toHaveTextContent("Did the first card payment at the pontoon go through?");
    expect(rows[0]).not.toHaveTextContent("could not tell");
    expect(rows[1]).toHaveTextContent("A session read it and could not tell: no check email since the close; Friday's run decides it");
    await userEvent.click(within(rows[0] as HTMLElement).getByRole("button", { name: "Delivered" }));
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 259, "signal", { delivered: true }));
    expect(await screen.findByText("#259: Read as delivered; moved to Done.")).toBeInTheDocument();
    await userEvent.click(within(rows[1] as HTMLElement).getByRole("button", { name: "Not delivered" }));
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 134, "signal", { delivered: false }));
  });

  it("puts a lane's question on the card and one sentence answers it", async () => {
    api.getCard.mockResolvedValue(withLane("asking", "Asking you: High or medium?", "The parser is in.\n\nHigh or medium?"));
    api.openDoor.mockResolvedValue({ door: "answer", said: "Answered, and the lane resumed as aaaa0001 (fable on alpha): High." });
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    expect(await screen.findByText(/High or medium\?/, { selector: ".ask-block" })).toBeInTheDocument();
    const field = screen.getByRole("textbox", { name: "Answer" });
    await userEvent.type(field, "High.{enter}");
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 253, "answer", { text: "High." }));
    expect(await screen.findByText(/the lane resumed as aaaa0001/)).toBeInTheDocument();
  });

  it("offers Look and Resume, never Watch, on a lane whose session is gone, with the machine's reason", async () => {
    api.getCard.mockResolvedValue(withLane("ended", "Lane ended 3 min ago: the journal says: Killed process 4242. nothing folded."));
    api.openDoor.mockRejectedValue(new ApiError(502, "Look did not open: no window appeared under org.omarchy.board-look-card-253 within 8 s"));
    await renderBoard();
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const look = await screen.findByRole("button", { name: "Look" });
    expect(screen.getByRole("button", { name: "Resume" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Watch" })).not.toBeInTheDocument();
    expect(screen.getByText("the journal says: Killed process 4242")).toBeInTheDocument();
    await userEvent.click(look);
    expect(await screen.findByText(/Look did not open: no window appeared/)).toBeInTheDocument();
  });

  it("says what needs the owner in three words, and keeps the quiet facts behind the project pill", async () => {
    const b = board();
    withClaims(b, "yours", [["decision", 3]]);
    withClaims(b, "broken", [["lane ended", 1]]);
    b.trunk = { level: false, behind: 4, note: "the checkout has uncommitted work that is not the runtime's (README.md); not touched", read_at: "2026-09-04T12:00:00+00:00" };
    b.machine = { missing: ["hyprctl"] };
    api.getBoard.mockResolvedValue(b);
    await renderBoard();
    // The head is one line: three words, each its meaning's colour and nothing else's.
    const head = document.querySelector(".app-head") as HTMLElement;
    const words = within(head).getAllByRole("button").filter((el) => el.classList.contains("word"));
    expect(words.map((el) => [el.textContent, el.dataset["meaning"]])).toEqual([
      ["Your move 3", "yours"],
      ["Broken 1", "broken"],
      ["Live 0", "quiet"],
    ]);
    // Nothing is live, so its count claims nobody and is not painted teal.
    expect(words[2]).toBeDisabled();
    // The quiet facts are behind the pill, not on the head.
    const facts = document.querySelector(".facts") as HTMLElement;
    expect(facts).toHaveTextContent("the runtime cannot find: hyprctl");
    expect(facts).toHaveTextContent("trunk 4 behind origin/develop");
    expect(within(facts).getByText("trunk 4 behind origin/develop").dataset["meaning"]).toBe("broken");
    // "Behind the pill" is literal: the facts hang off the project switcher.
    expect(facts.closest(".project")).not.toBeNull();
    expect(within(head).getByRole("group", { name: "What needs you" })).not.toHaveTextContent("hyprctl");
    expect(screen.getByRole("alert")).toHaveTextContent("The main checkout is not level with origin/develop: the checkout has uncommitted work");
  });
});

describe("the lens", () => {
  it("re-sorts what is seen without writing, and lifts nothing while on", async () => {
    await renderBoard();
    await userEvent.click(screen.getByRole("button", { name: "Age" }));
    expect(upNextOrder()).toEqual([237, 174, 241, 253, 228]);
    const card = screen.getByText("#241").closest("article") as HTMLElement;
    act(() => card.focus());
    fireEvent.keyDown(card, { key: " " });
    expect(card.className).not.toContain("ghost");
    expect(api.moveCard).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Rank" }));
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);
  });
});

describe("the project switcher", () => {
  it("lists every project with the current one chosen, and choosing another goes to its path", async () => {
    api.getProjects.mockResolvedValue([PROJECT, SECOND]);
    await renderBoard();
    const switcher = screen.getByRole("combobox", { name: "Project" });
    expect(switcher).toHaveValue(SLUG);
    expect(within(switcher).getAllByRole("option").map((o) => o.textContent)).toEqual([PROJECT.name, SECOND.name]);
    await userEvent.selectOptions(switcher, SECOND.slug);
    expect(window.location.pathname).toBe(`/p/${SECOND.slug}`);
    await waitFor(() => expect(api.getBoard).toHaveBeenLastCalledWith(SECOND.slug));
    expect(screen.getByRole("combobox", { name: "Project" })).toHaveValue(SECOND.slug);
  });

  it("reads the project from the path, so a deep link and the back button land where they say", async () => {
    api.getProjects.mockResolvedValue([PROJECT, SECOND]);
    window.history.replaceState(null, "", `/p/${SECOND.slug}`);
    await renderBoard();
    expect(api.getBoard).toHaveBeenCalledWith(SECOND.slug);
    expect(screen.getByRole("combobox", { name: "Project" })).toHaveValue(SECOND.slug);
    window.history.replaceState(null, "", `/p/${SLUG}`);
    act(() => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(api.getBoard).toHaveBeenLastCalledWith(SLUG));
    expect(screen.getByRole("combobox", { name: "Project" })).toHaveValue(SLUG);
  });

  it("shows a project the page did not know of once the board changes", async () => {
    api.getProjects.mockResolvedValueOnce([PROJECT]).mockResolvedValueOnce([PROJECT, SECOND]);
    api.getBoard.mockResolvedValueOnce(board()).mockResolvedValueOnce({ ...board(), version: 2 });
    await renderBoard();
    expect(within(screen.getByRole("combobox", { name: "Project" })).getAllByRole("option")).toHaveLength(1);
    // The stream would call for a refetch; the lens click does not, so the board is re-read through a move.
    api.moveCard.mockResolvedValue({ ...board(), version: 3 });
    const card = screen.getByText("#241").closest("article") as HTMLElement;
    act(() => card.focus());
    fireEvent.keyDown(card, { key: " " });
    fireEvent.keyDown(card, { key: "ArrowUp" });
    fireEvent.keyDown(card, { key: " " });
    await waitFor(() => expect(within(screen.getByRole("combobox", { name: "Project" })).getAllByRole("option")).toHaveLength(2));
  });
});

describe("the board that cannot be read", () => {
  it("says so instead of showing anything", async () => {
    api.getBoard.mockRejectedValue(new ApiError(0, "The board could not be reached: fetch failed"));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The board could not be read: The board could not be reached: fetch failed");
    act(() => undefined);
  });
});

describe("the triage lens", () => {
  const verdicts: VerdictLine[] = [
    { number: 228, title: "The skipper is told what the office decided", place: { column: "Up next", group: null, position: 2 }, verdict: { evidence_class: "superseded", evidence: "card #263 carries the same intent as a plan", to: "Not now" } },
    { number: 237, title: "The fuel pontoon takes cards, live", place: { column: "Up next", group: null, position: 3 }, verdict: { evidence_class: "built under another name", evidence: "docs/plans/done/2026-09-03-the-fuel-pontoon.md delivered it", to: "Done" } },
    { number: 241, title: "Berths are billed by the metre", place: { column: "Up next", group: null, position: 1 }, verdict: { evidence_class: "live and open", evidence: "waits on the four Search rulings (#144)", to: null } },
  ];

  function withVerdicts() {
    const b = board();
    b.verdicts = verdicts;
    withClaims(b, "yours", [["verdict", verdicts.length]]);
    for (const line of verdicts) cardOf(b, line.number).claims = ["verdict"];
    return b;
  }

  it("is reached from Your move, lists every unread verdict grouped by class, and rules through the doors", async () => {
    api.getBoard.mockResolvedValue(withVerdicts());
    api.openDoor.mockResolvedValue({ door: "accept", said: "#228 moved to Not now: superseded — card #263 carries the same intent as a plan" });
    api.acceptClass.mockResolvedValue({ evidence_class: "live and open", accepted: 1, refused: [] });
    await renderBoard();
    expect(screen.queryByRole("region", { name: /carry a verdict you have not read/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Your move/ }));
    await userEvent.click(screen.getByRole("button", { name: "3 verdict" }));
    const lens = screen.getByRole("region", { name: "3 cards carry a verdict you have not read" });
    expect(screen.queryByRole("heading", { name: "Backlog" })).not.toBeInTheDocument();
    const groups = Array.from(lens.querySelectorAll(".tg-name")).map((el) => el.textContent);
    expect(groups).toEqual(["built under another name", "superseded", "live and open"]);
    const superseded = within(lens).getByRole("list", { name: "superseded" });
    const row = within(superseded).getByRole("listitem");
    expect(row).toHaveTextContent("#228");
    expect(row).toHaveTextContent("card #263 carries the same intent as a plan");
    expect(row).toHaveTextContent("→ Not now");
    expect(within(within(lens).getByRole("list", { name: "live and open" })).getByRole("listitem")).toHaveTextContent("stays");

    await userEvent.click(within(row).getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 228, "accept", {}));
    expect(await screen.findByText("#228 moved to Not now: superseded — card #263 carries the same intent as a plan")).toBeInTheDocument();
    await waitFor(() => expect(api.getBoard.mock.calls.length).toBeGreaterThan(1));

    const open = within(lens).getByRole("list", { name: "live and open" }).closest(".triage-group") as HTMLElement;
    await userEvent.click(within(open).getByRole("button", { name: "Accept all 1" }));
    await waitFor(() => expect(api.acceptClass).toHaveBeenCalledWith(SLUG, "live and open"));
    expect(await screen.findByText('Accepted 1 in "live and open"')).toBeInTheDocument();

    const built = within(within(lens).getByRole("list", { name: "built under another name" })).getByRole("listitem");
    api.openDoor.mockResolvedValue({ door: "overturn", said: "#237 stays in Up next; your word: that plan built the pump" });
    await userEvent.click(within(built).getByRole("button", { name: "Overturn" }));
    const word = within(built).getByRole("textbox", { name: "Overturn" });
    await userEvent.type(word, "that plan built the pump{enter}");
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 237, "overturn", { text: "that plan built the pump" }));
    expect(await screen.findByText("#237 stays in Up next; your word: that plan built the pump")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Rank" }));
    expect(screen.getByRole("heading", { name: "Backlog" })).toBeInTheDocument();
  });
});

describe("conversations and lanes that know each other", () => {
  it("opens an idea from the head with the first line typed into the door, and lists the conversations alive", async () => {
    const b = board();
    withClaims(b, "live", [["conversation", 1]]);
    b.conversations = [{ short_id: "a1b2c3d4", slot: "alpha", card_number: null, what: "Idea", started_at: "2026-09-04T08:20:00+00:00" }];
    api.getBoard.mockResolvedValue(b);
    api.openIdea.mockResolvedValue({ door: "idea", said: "Talking in org.omarchy.board-idea-harbourmaster, fable on alpha; a conversation about nothing yet (a1b2c3d4), never hands on a tree." });
    await renderBoard();
    const line = screen.getByRole("textbox", { name: "Your first line" });
    await userEvent.type(line, "should berths be priced by the metre?{enter}");
    await waitFor(() => expect(api.openIdea).toHaveBeenCalledWith(SLUG, "should berths be priced by the metre?"));
    expect(await screen.findByText(/a conversation about nothing yet \(a1b2c3d4\)/)).toBeInTheDocument();
    expect(line).toHaveValue("");
    await userEvent.click(screen.getByRole("button", { name: "Idea" }));
    await waitFor(() => expect(api.openIdea).toHaveBeenLastCalledWith(SLUG, ""));

    expect(screen.queryByRole("region", { name: /conversation.*alive/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Live/ }));
    await userEvent.click(screen.getByRole("button", { name: "1 conversation" }));
    const talks = screen.getByRole("region", { name: "1 conversation alive — never hands on a tree" });
    expect(within(talks).getByRole("listitem")).toHaveTextContent("Idea");
    expect(within(talks).getByRole("listitem")).toHaveTextContent("a1b2c3d4 on alpha");
  });

  it("marks two lanes in one file as colliding on both cards and the rail, and shows the watercooler's last line on every live card", async () => {
    const b = board();
    const mine = cardOf(b, 253);
    const theirs = cardOf(b, 241);
    for (const [card, other] of [[mine, 241], [theirs, 253]] as const) {
      card.lane_state = "working";
      card.claims = ["colliding", "lane working"];
      card.colliding = { verdict: "collides", sentence: `#${other}'s lane is also editing engine/metering.py.`, files: ["engine/metering.py"], cards: [other] };
      // Two live lanes in one file is broken, and broken beats live: the card
      // says so in one word, in red, where every other state's word sits.
      card.state = { word: `colliding with #${other}`, meaning: "broken", detail: card.colliding.sentence, loop: null, door: null, hint: "open to see" };
    }
    withClaims(b, "broken", [["colliding", 2]]);
    b.watercooler = [
      { id: 1, project: SLUG, card_number: 241, actor: "session", at: "2026-09-04T08:10:00+00:00", text: "touching engine/metering.py for the tariff; leave it" },
      { id: 2, project: SLUG, card_number: null, actor: "machine", at: "2026-09-04T08:25:00+00:00", text: "#241 folded over #253's edits in engine/metering.py" },
    ];
    api.getBoard.mockResolvedValue(b);
    const d = withLane("working", "Working, fable on alpha, hands on for 12 min.");
    if (d.lane) {
      d.lane.edits = ["engine/metering.py", "engine/tariff.py"];
      d.lane.declared = ["engine/metering.py"];
      d.lane.colliding = mine.colliding;
    }
    d.watercooler = b.watercooler;
    d.heard = { project: SLUG, card_number: 253, watercooler_id: 2, collision: "#241's lane is also editing engine/metering.py.", at: "2026-09-04T08:26:00+00:00", text: "The board said on the watercooler: #241 folded over #253's edits in engine/metering.py" };
    api.getCard.mockResolvedValue(d);
    await renderBoard();
    expect(screen.getByRole("button", { name: /^Broken/ })).toHaveTextContent("Broken 2");
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    expect(within(resting).getByText("#241's lane is also editing engine/metering.py.")).toBeInTheDocument();
    expect(within(resting).getByRole("note")).toHaveTextContent("the board#241 folded over #253's edits in engine/metering.py");
    const other = screen.getByText("#241").closest("article") as HTMLElement;
    expect(within(other).getByText("#253's lane is also editing engine/metering.py.")).toBeInTheDocument();
    // A card with no hands on it carries no watercooler line.
    const still = screen.getByText("#228").closest("article") as HTMLElement;
    expect(within(still).queryByRole("note")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    await screen.findByRole("button", { name: "Watch" });
    expect(screen.getByText("Touching: engine/metering.py, engine/tariff.py")).toBeInTheDocument();
    expect(screen.getByText("Its plan names: engine/metering.py")).toBeInTheDocument();
    const cooler = screen.getByText("The watercooler").closest(".sec") as HTMLElement;
    expect(cooler).toHaveTextContent("touching engine/metering.py for the tariff; leave it");
    expect(cooler).toHaveTextContent("#241");
    expect(cooler).toHaveTextContent("board");
    // The open card says when its lane last heard the board inside its session, and what (plan 10).
    const heard = within(cooler).getByRole("note");
    expect(heard).toHaveTextContent("its lane heard");
    expect(heard).toHaveTextContent("The board said on the watercooler: #241 folded over #253's edits in engine/metering.py");
  });
});

describe("the board at a glance (plan 06)", () => {
  const why = "Fable headroom on alpha (12% of Fable used)";

  it("says whether a queued card can start, and starts a free one from its collapsed face", async () => {
    const b = board();
    const mine = cardOf(b, 253);
    const theirs = cardOf(b, 241);
    const note = cardOf(b, 228);
    mine.state = { word: "free to start", meaning: "proven", detail: null, loop: null, door: { name: "start", label: "Start", why: `Start · fable on alpha — ${why}`, primary: true }, hint: null };
    theirs.state = { word: "collides with #253 · waits", meaning: "quiet", detail: null, loop: null, door: null, hint: "1 file · open to see" };
    note.state = { word: "no gate", meaning: "quiet", detail: "This card names no effort gate; only a planned card is startable.", loop: null, door: null, hint: "open to see" };
    api.getBoard.mockResolvedValue(b);
    api.openDoor.mockResolvedValue({ door: "start", said: "Started aaaa0001, fable on alpha, at medium, in card-253-every-metered-kilowatt-is-billed" });
    await renderBoard();
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    expect(within(resting).getByText("free to start")).toBeInTheDocument();
    // A collision before Start is quiet: nothing is broken, the card waits.
    const colliding = screen.getByText("#241").closest("article") as HTMLElement;
    expect(colliding.dataset["meaning"]).toBe("quiet");
    expect(within(colliding).getByText("collides with #253 · waits")).toBeInTheDocument();
    expect(within(colliding).getByText("1 file · open to see")).toBeInTheDocument();
    expect(within(colliding).queryByRole("button", { name: /Start/ })).not.toBeInTheDocument();
    const gateless = screen.getByText("#228").closest("article") as HTMLElement;
    expect(within(gateless).getByText("no gate")).toBeInTheDocument();
    // Start on the collapsed face, the same door as the open card's, and the card does not open on the click.
    await userEvent.click(within(resting).getByRole("button", { name: "Start" }));
    await waitFor(() => expect(api.openDoor).toHaveBeenCalledWith(SLUG, 253, "start"));
    expect(await within(resting).findByText(/Started aaaa0001/)).toBeInTheDocument();
    expect(resting.className).not.toContain("open");
  });

  it("shows a gateless queued card's Start closed with its reason on the open face", async () => {
    const d = detail(228);
    d.doors = { ...d.doors, start: { offered: false, label: "Start", why: "This card names no effort gate; only a planned card is startable." } };
    api.getCard.mockResolvedValue(d);
    await renderBoard();
    await userEvent.click(screen.getByText("The skipper is told what the office decided"));
    const card = await waitFor(() => {
      const el = screen.getByText("#228").closest("article") as HTMLElement;
      expect(el.className).toContain("open");
      return el;
    });
    const start = await within(card).findByText("Start");
    expect(start).toHaveAttribute("aria-disabled", "true");
    expect(within(card).getByText(/Start is closed: This card names no effort gate/)).toBeInTheDocument();
  });

  it("offers Plan on a suggestion card, collapsed and open, and plans several together from a selection", async () => {
    const b = board();
    const backlog = b.columns.find((c) => c.definition.column === "Backlog");
    const suggestions = backlog?.groups.flatMap((g) => g.cards).filter((c) => c.document_state === "suggestion") ?? [];
    const planWhy = "Opens a plan-writing conversation for this suggestion; the plan it writes carries the card.";
    for (const card of suggestions) {
      card.state = { word: "no plan yet", meaning: "quiet", detail: null, loop: null, door: { name: "plan", label: "Create plan", why: planWhy, primary: false }, hint: null };
    }
    api.getBoard.mockResolvedValue(b);
    const d = detail(252);
    d.doors = { ...d.doors, plan: { offered: true, label: "Create plan", why: planWhy } };
    api.getCard.mockResolvedValue(d);
    api.openPlan.mockResolvedValue({ door: "plan", said: "Planning #252 in org.omarchy.board-plan-card-252-x, fable on alpha; the plan it writes carries this card." });
    await renderBoard();
    const one = screen.getByText("#252").closest("article") as HTMLElement;
    expect(within(one).getByText("no plan yet")).toBeInTheDocument();
    await userEvent.click(within(one).getByRole("button", { name: "Create plan" }));
    await waitFor(() => expect(api.openPlan).toHaveBeenCalledWith(SLUG, [252]));
    expect(await within(one).findByText(/Planning #252/)).toBeInTheDocument();
    // A selection: + on the first, then a checkbox on every suggestion card, then one door for all.
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    await userEvent.click(within(one).getByRole("button", { name: "Plan #252 together with others" }));
    const other = screen.getByText("#242").closest("article") as HTMLElement;
    expect(within(one).getByRole("checkbox", { name: "Plan #252 together" })).toBeChecked();
    await userEvent.click(within(other).getByRole("checkbox", { name: "Plan #242 together" }));
    const bar = screen.getByRole("region", { name: "2 suggestions selected for one plan" });
    api.openPlan.mockResolvedValue({ door: "plan", said: "Planning #242, #252 in org.omarchy.board-plan-cards-242-252, fable on alpha; the plan it writes carries these cards, the first keeping its number." });
    await userEvent.click(within(bar).getByRole("button", { name: "Plan these together" }));
    await waitFor(() => expect(api.openPlan).toHaveBeenLastCalledWith(SLUG, [242, 252]));
    expect(await screen.findByText(/Planning #242, #252/)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    // The open card offers Plan too.
    await userEvent.click(screen.getByText("The quay display polls the office all night"));
    const opened = await waitFor(() => {
      const el = screen.getByText("#252").closest("article") as HTMLElement;
      expect(el.className).toContain("open");
      return el;
    });
    expect(await within(opened).findByRole("button", { name: "Create plan" })).toHaveAttribute("title", expect.stringContaining("plan-writing conversation"));
  });

  it("pins the defects rail at the top of Backlog with its count, furled until asked", async () => {
    await renderBoard();
    const backlog = document.querySelector('[data-column="Backlog"]') as HTMLElement;
    const rail = within(backlog).getByRole("button", { name: /Defects/ });
    expect(rail).toHaveAttribute("aria-expanded", "false");
    expect(rail).toHaveTextContent("Defects1");
    expect(within(backlog).queryByText("#232")).not.toBeInTheDocument();
    expect(backlog.querySelector(".stack")?.firstElementChild?.getAttribute("data-rail")).toBe("defects");
    await userEvent.click(rail);
    expect(rail).toHaveAttribute("aria-expanded", "true");
    expect(within(backlog).getByText("#232")).toBeInTheDocument();
    // A category is not a colour: the rail is a rail, and the counts of what is
    // unplanned are a quiet fact behind the project pill, not a claim on him.
    expect(rail.getAttribute("data-meaning")).toBeNull();
    expect(document.querySelector(".facts")).toHaveTextContent("1 defects and 7 ideas unplanned");
  });

  it("shows what a card carries on both faces", async () => {
    const b = board();
    const mine = cardOf(b, 253);
    mine.folded = [
      { number: 7, title: "An archived document moves its card", document_path: "docs/slice-suggestions/done/a.md" },
      { number: 10, title: "Defects are their own rail", document_path: null },
    ];
    api.getBoard.mockResolvedValue(b);
    const d = detail(253);
    d.summary.folded = mine.folded;
    api.getCard.mockResolvedValue(d);
    await renderBoard();
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    const carries = within(resting).getByRole("list", { name: "carries 2" });
    expect(carries).toHaveTextContent("carries#7#10");
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const section = await screen.findByText("What it carries");
    expect(section.closest(".sec")).toHaveTextContent("An archived document moves its card");
  });

  it("keeps the head one line whatever a column does — there is nothing left to fold", async () => {
    await renderBoard();
    const head = document.querySelector(".app-head") as HTMLElement;
    const before = head.textContent;
    const column = document.querySelector('[data-column="Backlog"]') as HTMLElement;
    Object.defineProperty(column, "scrollTop", { value: 240, configurable: true });
    fireEvent.scroll(column);
    expect(head.textContent).toBe(before);
    expect(document.querySelector(".head.folded")).toBeNull();
  });

  it("re-reads the board once when the stream reconnects", async () => {
    const sources: FakeEventSource[] = [];
    class FakeEventSource {
      onopen: (() => void) | null = null;
      onerror: (() => void) | null = null;
      private listeners: ((event: MessageEvent<string>) => void)[] = [];
      constructor(public url: string) {
        sources.push(this);
      }
      addEventListener(_name: string, listener: (event: MessageEvent<string>) => void) {
        this.listeners.push(listener);
      }
      close() {
        return undefined;
      }
      say(version: number) {
        for (const listener of this.listeners) listener({ data: JSON.stringify({ version }) } as MessageEvent<string>);
      }
    }
    (window as unknown as { EventSource: typeof FakeEventSource }).EventSource = FakeEventSource;
    try {
      await renderBoard();
      const source = sources[0];
      if (!source) throw new Error("the page opened no stream");
      const reads = api.getBoard.mock.calls.length;
      act(() => source.onopen?.());
      act(() => source.say(board().version));
      expect(api.getBoard.mock.calls.length).toBe(reads);
      // The server restarted: the stream reconnects and the first message re-reads, even at the same version.
      act(() => source.onerror?.());
      act(() => source.onopen?.());
      act(() => source.say(board().version));
      await waitFor(() => expect(api.getBoard.mock.calls.length).toBe(reads + 1));
      act(() => source.say(board().version));
      expect(api.getBoard.mock.calls.length).toBe(reads + 1);
    } finally {
      delete (window as unknown as { EventSource?: unknown }).EventSource;
    }
  });
});

/**
 * The colour language (plan 27, item 6). Every state the rule can name is
 * rendered here — one card each, from the real derivation in the fixture —
 * and read back for its word, its meaning, the border it takes and the door
 * it allows. The meaning is the page's only route to a colour
 * (`tests/ratchets/test_the_colour_language.py` holds that), so asserting the
 * meaning is asserting the colour; and because the cards come from the
 * backend, a rule that changes a word fails here too.
 */
describe("the colour language", () => {
  const CASES = language();

  /** One card in one state, alone in Up next, as the page renders it. */
  async function render1(index: number): Promise<HTMLElement> {
    const one = CASES[index];
    if (!one) throw new Error(`no case ${index}`);
    cleanup();
    const b = board();
    for (const column of b.columns) for (const group of column.groups) group.cards = [];
    const upNext = b.columns.find((c) => c.definition.column === "Up next")?.groups[0];
    if (!upNext) throw new Error("no Up next");
    upNext.cards = [{ ...one.card, place: { column: "Up next", group: null, position: 0 } }];
    api.getBoard.mockResolvedValue(b);
    render(<App />);
    await screen.findByText("A card in every state");
    return screen.getByText("A card in every state").closest("article") as HTMLElement;
  }

  // `door` is the label of the one door the state allows, or the grey line
  // where it would be — `null` where the state has said everything already.
  const table: { case: string; word: string; meaning: string; border: boolean; door: string | null }[] = [
    { case: "free to start", word: "free to start", meaning: "proven", border: false, door: "Start" },
    { case: "collides", word: "collides with #241 · waits", meaning: "quiet", border: false, door: "1 file · open to see" },
    { case: "no gate", word: "no gate", meaning: "quiet", border: false, door: "open to see" },
    { case: "nowhere to run", word: "nowhere to run", meaning: "quiet", border: false, door: "open to see" },
    { case: "working", word: "working · 12 min · fable on alpha", meaning: "live", border: true, door: "Watch" },
    { case: "asking you", word: "asking you", meaning: "yours", border: true, door: "Answer" },
    { case: "colliding", word: "colliding with #241", meaning: "broken", border: true, door: "open to see" },
    { case: "lane ended", word: "lane ended", meaning: "broken", border: true, door: "open to resume" },
    { case: "doubted", word: "doubted", meaning: "broken", border: true, door: "open to decide" },
    { case: "document nowhere", word: "document nowhere", meaning: "broken", border: true, door: "open to see" },
    { case: "your move", word: "your move", meaning: "yours", border: true, door: "Decide" },
    { case: "loop open", word: "loop open · a session reads it 11 Sep", meaning: "quiet", border: false, door: null },
    { case: "loop open, owner only", word: "loop open · you read it 11 Sep", meaning: "quiet", border: false, door: null },
    { case: "signal for you to read", word: "signal for you to read", meaning: "yours", border: true, door: "Read" },
    { case: "a session is reading it", word: "loop open · a session reads it now · beta", meaning: "live", border: true, door: null },
    { case: "signal past due", word: "loop open · 1 Sep passed, unread", meaning: "broken", border: true, door: null },
    { case: "loop closed", word: "loop closed · read 09:30, delivered", meaning: "proven", border: false, door: null },
    { case: "not now", word: "not now", meaning: "quiet", border: false, door: "open ▸" },
  ];

  it("has one card per state and no state the table does not name", () => {
    expect(CASES.map((c) => c.case)).toEqual(table.map((t) => t.case));
    // Every one of the five meanings is exercised, so none of them is a
    // colour nothing on the board ever says.
    expect(new Set(table.map((t) => t.meaning))).toEqual(new Set(["yours", "broken", "live", "proven", "quiet"]));
  });

  table.forEach((expected, index) => {
    it(`renders "${expected.case}" as one word in one meaning, with the one door it allows`, async () => {
      const card = await render1(index);
      // The word, always bottom-left of the state line, always in the same place.
      const state = card.querySelector(".state") as HTMLElement;
      expect(within(state).getByText(expected.word)).toBeInTheDocument();
      // The meaning is the colour: nothing on the page can paint without it.
      expect(card.dataset["meaning"]).toBe(expected.meaning);
      // The border takes the state's colour only for live, asking you and broken.
      expect(["live", "yours", "broken"].includes(expected.meaning)).toBe(expected.border);
      // The one door the state allows, bottom-right — or what opening gives,
      // or nothing at all where the loop line is the whole sentence.
      if (expected.door === null) {
        expect(state.querySelector(".btn")).toBeNull();
        expect(state.querySelector(".hint")).toBeNull();
      } else {
        const door = within(state).queryByRole("button", { name: expected.door });
        if (door) expect(door).toBeInTheDocument();
        else expect(within(state).getByText(expected.door)).toBeInTheDocument();
      }
    });
  });

  it("carries a shipped card's loop as a glyph, and an owner-only ring is amber", async () => {
    const open = await render1(table.findIndex((t) => t.case === "loop open"));
    const ring = open.querySelector(".loop") as HTMLElement;
    expect(ring.className).toContain("open");
    // An open loop is ink, not a meaning: a live obligation, just not yours.
    expect(ring.dataset["meaning"]).toBeUndefined();

    const owned = await render1(table.findIndex((t) => t.case === "loop open, owner only"));
    expect((owned.querySelector(".loop") as HTMLElement).dataset["meaning"]).toBe("yours");

    const closed = await render1(table.findIndex((t) => t.case === "loop closed"));
    const dot = closed.querySelector(".loop") as HTMLElement;
    expect(dot.className).toContain("closed");
    expect(dot.dataset["meaning"]).toBe("proven");
  });

  it("never colours a button, a column or a count", async () => {
    await renderBoard();
    for (const button of Array.from(document.querySelectorAll("button.btn"))) {
      expect((button as HTMLElement).dataset["meaning"]).toBeUndefined();
    }
    for (const column of Array.from(document.querySelectorAll(".col"))) {
      expect((column as HTMLElement).dataset["meaning"]).toBeUndefined();
      expect((column.querySelector(".col-head") as HTMLElement).dataset["meaning"]).toBeUndefined();
    }
    // The kind is a fact, not a claim: defects and ideas are two rails, not two hues.
    for (const kind of Array.from(document.querySelectorAll(".kind"))) {
      expect((kind as HTMLElement).dataset["meaning"]).toBeUndefined();
    }
  });

  it("filters the board to a word, narrows to one claim, and clears", async () => {
    const b = board();
    cardOf(b, 253).claims = ["decision"];
    cardOf(b, 241).claims = ["lane asking"];
    withClaims(b, "yours", [["verdict", 0], ["lane asking", 1], ["decision", 1]]);
    b.attention = { ...b.attention, yours: b.attention.yours.filter((l) => l.count > 0) };
    api.getBoard.mockResolvedValue(b);
    await renderBoard();
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);

    await userEvent.click(screen.getByRole("button", { name: /^Your move/ }));
    expect(upNextOrder()).toEqual([253, 241]);
    // A filtered column counts what it shows and names no empty group.
    const upNext = document.querySelector('[data-column="Up next"]') as HTMLElement;
    expect(within(upNext).getByRole("heading", { name: "Up next" }).nextElementSibling).toHaveTextContent("2");
    expect(upNext.querySelector(".more-row")).toBeNull();
    const backlog = document.querySelector('[data-column="Backlog"]') as HTMLElement;
    expect(backlog.querySelectorAll(".group-h")).toHaveLength(0);
    expect(backlog.querySelector(".more-row")).toBeNull();
    const breakdown = screen.getByRole("group", { name: "What Your move counts" });
    expect(within(breakdown).getAllByRole("button").map((el) => el.textContent)).toEqual(["1 lane asking", "1 decision", "clear"]);

    await userEvent.click(within(breakdown).getByRole("button", { name: "1 decision" }));
    expect(upNextOrder()).toEqual([253]);

    await userEvent.click(screen.getByRole("button", { name: /^Your move/ }));
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);
    expect(screen.queryByRole("group", { name: /What Your move counts/ })).not.toBeInTheDocument();
  });
});
