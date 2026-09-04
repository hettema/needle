import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within, waitFor, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "../src/api";
import { PROJECT, board, detail } from "./fixture";
import type { BoardState } from "../src/types/board";
import type { Place } from "../src/types/card";
import type { Project } from "../src/types/project";

const api = vi.hoisted(() => ({
  getBoard: vi.fn<(slug: string) => Promise<BoardState>>(),
  moveCard: vi.fn<(slug: string, number: number, to: Place) => Promise<BoardState>>(),
  getCard: vi.fn(),
  getFile: vi.fn(),
  getProjects: vi.fn<() => Promise<Project[]>>(),
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
  window.history.replaceState(null, "", "/");
});

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
    expect(within(card).getByText(/Nothing has been done to this card/)).toBeInTheDocument();
    expect(within(card).getByText("TODAY")).toBeInTheDocument();
    expect(within(card).getByText("docs/plans/2026-09-03-every-metered-kilowatt-is-billed.md")).toBeInTheDocument();
    expect(within(card).getByText("Born")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Open the plan" })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Copy path" })).toBeInTheDocument();
    expect(within(card).getByRole("combobox", { name: "Move to" })).toHaveValue("Up next");
    expect(within(card).queryByText(/Start/)).not.toBeInTheDocument();
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
