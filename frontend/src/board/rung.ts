// The one place the page says where a session runs.

/**
 * A rung as every face says it: the model and the slot when a model is
 * named, the slot alone when none is. The mirror of `domain.slot.rung_words`
 * (card #63). The page used to write `model ?? "fable"`, which named a
 * Claude rung for a session of another make, and for a terminal of the
 * owner's that recorded no model at all.
 */
export function rungWords(model: string | null, slot: string): string {
  return model ? `${model} on ${slot}` : slot;
}
