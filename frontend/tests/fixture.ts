/**
 * The board as the API serves it for Harbourmaster, the synthetic project
 * under tests/fixtures/, with every card's detail: `fixture.json`, written by
 * `uv run python tools/board_fixture.py` from the real registration, import
 * and sweep, and held current by a ratchet. Nothing here is typed by hand,
 * so the page's tests can never drift from what the backend actually sends.
 */

import snapshot from "./fixture.json";
import type { BoardState, CardDetail, CardSummary } from "../src/types/board";
import type { Progress } from "../src/types/lane";
import type { Project } from "../src/types/project";

interface Snapshot {
  board: BoardState;
  details: Record<string, CardDetail>;
  language: LanguageCase[];
  progress: Record<ProgressCase, Progress>;
}

/** How far the storm-warning lane has come, from the real derivation over
 * its own copy of the plan (plan 13): nothing marked, two met, one deviated,
 * every item met with the review loop open, and the loop closed. */
export type ProgressCase = "nothing" | "two_met" | "deviated" | "review_open" | "review_clean";

/** One card in one state, from the real derivation: the table the page test
 * reads back (plan 27, item 6). */
export interface LanguageCase {
  case: string;
  card: CardSummary;
}

// The JSON module's inferred type has plain strings where the domain has enums; the ratchet that regenerates the file is what makes this cast true.
const SNAPSHOT = snapshot as Snapshot;

export const PROJECT: Project = SNAPSHOT.board.project;

/** The board; with `upNext`, the same board after a move put Up next in that order. */
export function board(upNext?: number[]): BoardState {
  const copy = structuredClone(SNAPSHOT.board);
  if (upNext) {
    const column = copy.columns.find((c) => c.definition.column === "Up next");
    const group = column?.groups[0];
    if (!group) throw new Error("the snapshot has no Up next");
    const cards = new Map(group.cards.map((c) => [c.number, c]));
    group.cards = upNext.map((number, position) => {
      const card = cards.get(number);
      if (!card) throw new Error(`no #${number} in Up next`);
      return { ...card, place: { ...card.place, position } };
    });
  }
  return copy;
}

export function summary(number: number): CardSummary {
  for (const column of SNAPSHOT.board.columns) for (const group of column.groups) for (const card of group.cards) if (card.number === number) return structuredClone(card);
  throw new Error(`no #${number} on the snapshot`);
}

/** Every state the rule can name, each with the card the board would send. */
export function language(): LanguageCase[] {
  return structuredClone(SNAPSHOT.language);
}

export function progress(name: ProgressCase): Progress {
  return structuredClone(SNAPSHOT.progress[name]);
}

export function detail(number: number): CardDetail {
  const found = SNAPSHOT.details[String(number)];
  if (!found) throw new Error(`no detail for #${number} in the snapshot`);
  return structuredClone(found);
}
