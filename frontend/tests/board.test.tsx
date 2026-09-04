import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within, waitFor, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, type DoorName } from "../src/api";
import { PROJECT, board, detail } from "./fixture";
import type { BoardState, CardDetail } from "../src/types/board";
import type { Place } from "../src/types/card";
import type { DoorResult, Lane } from "../src/types/lane";
import type { Project } from "../src/types/project";

const api = vi.hoisted(() => ({
  getBoard: vi.fn<(slug: string) => Promise<BoardState>>(),
  moveCard: vi.fn<(slug: string, number: number, to: Place) => Promise<BoardState>>(),
  getCard: vi.fn(),
  getFile: vi.fn(),
  getProjects: vi.fn<() => Promise<Project[]>>(),
  openDoor: vi.fn<(slug: string, number: number, door: DoorName, body?: object) => Promise<DoorResult>>(),
  streamUrl: (slug: string) => `/api/projects/${slug}/stream`,
}));

vi.mock("../src/api", async () => {
  const real = await vi.importActual<typeof import("../src/api")>("../src/api");
  return { ...real, ...api };
});

import { App } from "../src/App";

const SLUG = PROJECT.slug;
const SECOND: Project = { slug: "needle", name: "Needle", path: "/srv/needle", registered_at: "2026-09-04T07:00:00+00:00" };

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
  };
  d.summary.lane_state = state;
  d.summary.lane_sentence = sentence;
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
    expect(screen.getByText("Document gone")).toBeInTheDocument();
    expect(screen.getAllByText("Note — nothing written yet")).toHaveLength(4);
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(screen.getByText("cards cite documents that are nowhere")).toBeInTheDocument();
    expect(upNextOrder()).toEqual([253, 241, 228, 237, 174]);
    const second = within(screen.getByText("#241").closest("article") as HTMLElement);
    expect(second.getByText("2")).toBeInTheDocument();
    expect(second.getByText("4 points")).toBeInTheDocument();
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
    expect(screen.getByText("write failed")).toBeInTheDocument();
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
      collision: { verdict: "clear", sentence: "No running lane or trunk session touches this plan's files.", files: [] },
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
      collision: { verdict: "collides", sentence, files: ["engine/metering.py"] },
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

  it("shows a working lane's band on the resting card and Watch and Stop on the open one", async () => {
    const sentence = "Working, fable on alpha, hands on for 12 min.";
    const b = board();
    const column = b.columns.find((c) => c.definition.column === "Up next");
    const card = column?.groups[0]?.cards.find((c) => c.number === 253);
    if (!card) throw new Error("no #253");
    card.lane_state = "working";
    card.lane_sentence = sentence;
    api.getBoard.mockResolvedValue(b);
    api.getCard.mockResolvedValue(withLane("working", sentence));
    api.openDoor.mockResolvedValue({ door: "watch", said: "Window org.omarchy.board-watch-card-253 opened into aaaa0001; closing it ends nothing." });
    await renderBoard();
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    expect(within(resting).getByRole("status")).toHaveTextContent(`Working${sentence}`);
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
    const column = b.columns.find((c) => c.definition.column === "Up next");
    const card = column?.groups[0]?.cards.find((c) => c.number === 253);
    if (!card) throw new Error("no #253");
    card.standing = { actor: "machine", evidence: "hands-on", state: "doubted", words };
    b.attention = { ...b.attention, doubted: 1 };
    const d = detail(253);
    d.summary.standing = card.standing;
    api.getBoard.mockResolvedValue(b);
    api.getCard.mockResolvedValue(d);
    await renderBoard();
    expect(screen.getByText("status doubted — its evidence is gone")).toBeInTheDocument();
    const resting = screen.getByText("#253").closest("article") as HTMLElement;
    expect(within(resting).getByRole("status")).toHaveTextContent(`Doubted${words}`);
    await userEvent.click(screen.getByText("Every metered kilowatt is billed"));
    const open = await waitFor(() => {
      const el = screen.getByText("#253").closest("article") as HTMLElement;
      expect(el.className).toContain("open");
      return el;
    });
    await within(open).findByText("What it makes true");
    expect(within(open).getByRole("status")).toHaveTextContent(words);
    expect(within(open).getByText("doubted · hands-on")).toBeInTheDocument();
  });

  it("batches the signals only the owner can read into one list with one click each way per card", async () => {
    const b = board();
    b.attention = { ...b.attention, signals_asking: 2, asking_you: 2 };
    b.asks = [
      { number: 259, title: "The fuel pontoon takes cards, live", what: "Did the first card payment at the pontoon go through?", due: "2026-09-11" },
      { number: 134, title: "The office runs its own checks, nightly", what: "Did the nightly check email name a real event?", due: "2026-09-11" },
    ];
    api.getBoard.mockResolvedValue(b);
    api.openDoor.mockResolvedValue({ door: "signal", said: "Read as delivered; moved to Done." });
    await renderBoard();
    const rail = screen.getByRole("button", { name: "2 shipped cards wait on your reading" });
    expect(screen.queryByText(/only you can read these signals/)).not.toBeInTheDocument();
    await userEvent.click(rail);
    const list = screen.getByRole("region", { name: /2 shipped cards wait on your reading/ });
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("#259");
    expect(rows[0]).toHaveTextContent("Did the first card payment at the pontoon go through?");
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

  it("counts what needs the owner on the attention line and names a trunk that is not level", async () => {
    const b = board();
    b.attention = { ...b.attention, asking_you: 3, lanes_ended: 1, signals_due: 2 };
    b.trunk = { level: false, behind: 4, note: "the checkout has uncommitted work that is not the runtime's (README.md); not touched", read_at: "2026-09-04T12:00:00+00:00" };
    b.machine = { missing: ["hyprctl"] };
    api.getBoard.mockResolvedValue(b);
    await renderBoard();
    expect(screen.getByText("lane ended — Resume or Look")).toBeInTheDocument();
    expect(screen.getByText("signals past due")).toBeInTheDocument();
    expect(screen.getByText("the runtime cannot find: hyprctl")).toBeInTheDocument();
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
