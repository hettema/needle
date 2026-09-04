/**
 * The head's three words are filters of the board (plan 27, item 1): a word
 * shows only the cards that claim the owner's eye that way, and a sub-filter
 * narrows it to one claim. A filter is a lens, never a write — it changes
 * what is seen and never what is stored.
 */

import type { Attention, CardSummary, Claim, ClaimCount, Meaning } from "../types/board";

export type WordKey = "yours" | "broken" | "live";

export const WORDS: readonly { key: WordKey; label: string; meaning: Meaning }[] = [
  { key: "yours", label: "Your move", meaning: "yours" },
  { key: "broken", label: "Broken", meaning: "broken" },
  { key: "live", label: "Live", meaning: "live" },
];

export interface Filter {
  word: WordKey;
  claim: Claim | null;
}

export function lines(attention: Attention, word: WordKey): ClaimCount[] {
  return attention[word];
}

export function counted(attention: Attention, word: WordKey): number {
  return lines(attention, word).reduce((n, line) => n + line.count, 0);
}

/** The claims a filter admits: one, or every claim under its word. */
export function claimsOf(attention: Attention, filter: Filter): Claim[] {
  if (filter.claim !== null) return [filter.claim];
  return lines(attention, filter.word).map((line) => line.claim);
}

export function keeps(card: CardSummary, claims: readonly Claim[]): boolean {
  return card.claims.some((claim) => claims.includes(claim));
}
