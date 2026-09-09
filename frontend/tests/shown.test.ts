import { describe, expect, it } from "vitest";
import { nextShown } from "../src/state/board";
import type { Shown } from "../src/types/notice";

const shown = (id: number): Shown => ({ id, project: "proj", card_number: 253, at: "2026-09-09T12:00:00Z" });

describe("a shown on the stream (card #41)", () => {
  it("is not acted on when it stood before the page's first event", () => {
    expect(nextShown(null, shown(4))).toEqual({ seen: 4, act: false });
    expect(nextShown(null, null)).toEqual({ seen: 0, act: false });
  });
  it("is acted on once when its id is new, including the first press a page ever hears", () => {
    expect(nextShown(0, shown(1))).toEqual({ seen: 1, act: true });
    expect(nextShown(4, shown(5))).toEqual({ seen: 5, act: true });
    expect(nextShown(5, shown(5))).toEqual({ seen: 5, act: false });
    expect(nextShown(5, null)).toEqual({ seen: 5, act: false });
  });
  it("is acted on after a server restart counts from one again", () => {
    expect(nextShown(7, shown(1))).toEqual({ seen: 1, act: true });
  });
});
