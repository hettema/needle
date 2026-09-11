// The one place the page says which team a card runs with.

import type { Challenge, Route } from "../types/team";
import { rungWords } from "./rung";

const CHALLENGE_WORDS: Record<Challenge, string> = {
  alone: "the accountable hand alone",
  "same-make": "a same-make challenge",
  "different-make": "a different-make challenge",
};

/**
 * A team in one line, as every face says it: the mirror of
 * `board.team.team_words` (card #58), so the page and the card's history
 * name a hand and a challenger the same way.
 */
export function teamWords(route: Route): string {
  const hand = `${route.hand.make}, ${rungWords(route.hand.model, route.hand.slot)}`;
  const who = route.challenger ? `${route.challenger} challenges` : "nobody challenges";
  return `${CHALLENGE_WORDS[route.challenge]} — the hand is ${hand}; ${who}; ${route.conclusion}: ${route.why}`;
}
