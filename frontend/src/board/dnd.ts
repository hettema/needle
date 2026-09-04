/**
 * Where a lifted card lands, for the pointer and the keyboard alike.
 *
 * One representation — a `Place` in the list without the lifted card — feeds
 * the gap on the page and the move sent to the store, so a dropped card lands
 * where the preview said. Pure functions; the components own the DOM.
 */

import type { BoardState, CardSummary, ColumnView, GroupView } from "../types/board";
import type { Place } from "../types/card";
import type { Column } from "../types/column";

export interface Lift {
  number: number;
  from: Place;
  target: Place;
  by: "pointer" | "keyboard";
}

export function samePlace(a: Place, b: Place): boolean {
  return a.column === b.column && a.group === b.group && a.position === b.position;
}

export function sameGroup(a: Place, b: Place): boolean {
  return a.column === b.column && a.group === b.group;
}

/** Every place a lifted card could land in a column: per group, 0..count. */
export function columnSlots(column: ColumnView, lift: Lift): Place[] {
  const slots: Place[] = [];
  for (const group of column.groups) {
    const count = group.cards.filter((c) => c.number !== lift.number).length;
    for (let i = 0; i <= count; i++) {
      slots.push({ column: column.definition.column, group: group.name, position: i });
    }
  }
  return slots;
}

function slotIndex(slots: Place[], place: Place): number {
  return slots.findIndex((s) => samePlace(s, place));
}

export type StepKey = "ArrowUp" | "ArrowDown" | "ArrowLeft" | "ArrowRight";

/** The keyboard's next target: up and down walk a column's slots, left and right change column. */
export function stepTarget(board: BoardState, lift: Lift, key: StepKey, open: readonly Column[]): Place {
  const columns = board.columns.filter((c) => open.includes(c.definition.column));
  const ci = columns.findIndex((c) => c.definition.column === lift.target.column);
  const column = columns[ci];
  if (!column) return lift.target;
  const slots = columnSlots(column, lift);
  const si = Math.max(0, slotIndex(slots, lift.target));
  if (key === "ArrowUp" || key === "ArrowDown") {
    const next = slots[Math.min(slots.length - 1, Math.max(0, si + (key === "ArrowUp" ? -1 : 1)))];
    return next ?? lift.target;
  }
  const neighbour = columns[ci + (key === "ArrowLeft" ? -1 : 1)];
  if (!neighbour) return lift.target;
  const neighbourSlots = columnSlots(neighbour, lift);
  return neighbourSlots[Math.min(si, neighbourSlots.length - 1)] ?? lift.target;
}

/** The place under a pointer inside a group, read from the cards' own boxes. */
export function targetInGroup(
  column: Column,
  group: string | null,
  cardBoxes: readonly { number: number; top: number; height: number }[],
  pointerY: number,
  lift: Lift,
): Place {
  let position = 0;
  for (const box of cardBoxes) {
    if (box.number === lift.number) continue;
    if (pointerY > box.top + box.height / 2) position++;
    else break;
  }
  return { column, group, position };
}

export type Slot =
  | { kind: "card"; card: CardSummary; ghost: boolean; rank: number | null }
  | { kind: "gap"; label: string; rank: number | null };

export function gapLabel(lift: Lift, ranked: boolean, rank: number | null): string {
  const base = `#${lift.number} lands here`;
  if (ranked && rank !== null) return `${base} — rank ${rank}`;
  if (lift.target.group !== null) return `${base} — in ${lift.target.group}`;
  return base;
}

/**
 * A group's rows as the page draws them: the lifted card as a ghost where it
 * was, a gap where it will land, and ranks renumbered live for the would-be
 * order. `rankFrom` is the rank the first card here would carry.
 */
export function groupSlots(
  column: ColumnView,
  group: GroupView,
  visible: readonly CardSummary[],
  lift: Lift | null,
  rankFrom: number,
): { slots: Slot[]; rankNext: number } {
  const ranked = column.definition.ranked;
  const slots: Slot[] = [];
  let rank = rankFrom;
  const gapHere =
    lift !== null &&
    lift.target.column === column.definition.column &&
    lift.target.group === group.name &&
    !samePlace(lift.target, lift.from);
  let placed = 0;
  let gapDone = false;
  for (const card of visible) {
    if (gapHere && !gapDone && placed === lift.target.position) {
      slots.push({ kind: "gap", label: gapLabel(lift, ranked, ranked ? rank : null), rank: ranked ? rank : null });
      rank++;
      gapDone = true;
    }
    const ghost = lift !== null && card.number === lift.number;
    if (ghost) {
      slots.push({ kind: "card", card, ghost: true, rank: null });
    } else {
      slots.push({ kind: "card", card, ghost: false, rank: ranked ? rank : null });
      rank++;
      placed++;
    }
  }
  if (gapHere && !gapDone) {
    slots.push({ kind: "gap", label: gapLabel(lift, ranked, ranked ? rank : null), rank: ranked ? rank : null });
    rank++;
  }
  return { slots, rankNext: rank };
}

export type LensKind = "rank" | "age" | "gate";

const GATE_ORDER: Record<string, number> = { xhigh: 0, high: 1, medium: 2, low: 3 };

/** A lens, never a write: sorting changes what you see and never the stored order. */
export function throughLens(cards: readonly CardSummary[], lens: LensKind): CardSummary[] {
  if (lens === "rank") return [...cards];
  const sorted = [...cards];
  if (lens === "age") sorted.sort((a, b) => (a.age_date < b.age_date ? -1 : a.age_date > b.age_date ? 1 : 0));
  if (lens === "gate") sorted.sort((a, b) => (GATE_ORDER[a.gate ?? ""] ?? 9) - (GATE_ORDER[b.gate ?? ""] ?? 9));
  return sorted;
}

export function groupId(column: Column, group: string | null): string {
  return `group:${column}::${group ?? ""}`;
}
