/**
 * The page's copy of the board, and the one write.
 *
 * Board state is set from exactly two places: the answer to a read, and the
 * answer to a move the store has already persisted. There is no optimistic
 * rendering anywhere: a failed move leaves the board as it was and puts the
 * store's own words on the card. A ratchet holds this
 * (tests/ratchets/test_the_page_shows_only_held_state.py).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getBoard, moveCard, streamUrl } from "../api";
import type { BoardState } from "../types/board";
import type { Place } from "../types/card";
import type { Shown } from "../types/notice";

export type MoveStatus = { kind: "idle" } | { kind: "saving" } | { kind: "failed"; reason: string; to: Place };

export interface BoardStore {
  board: BoardState | null;
  error: string | null;
  connected: boolean;
  statuses: Record<number, MoveStatus>;
  refresh: () => Promise<void>;
  move: (number: number, to: Place) => Promise<boolean>;
  retry: (number: number) => Promise<boolean>;
  dismiss: (number: number) => void;
}

const IDLE: MoveStatus = { kind: "idle" };

/** What one stream event carries: the version, and beside it the card the runtime last asked every open page to put in front of the owner (card #41) — a request to the page, never board state. */
interface BoardEvent {
  version: number;
  shown: Shown | null;
}

function isBoardEvent(data: unknown): data is BoardEvent {
  return typeof data === "object" && data !== null && "version" in data && typeof (data as { version: unknown }).version === "number";
}

/**
 * Whether a `shown` on the stream is one this page should act on (card #41). The first event a
 * page hears primes it: whatever `shown` stood then was raised before this page existed, or before
 * it reconnected, and is not acted on — `0` stands for none yet. After that, a `shown` whose id is
 * not the one last seen is a press, including the first press a page ever hears and a server that
 * restarted and counts from one again.
 */
export function nextShown(seen: number | null, asked: Shown | null): { seen: number; act: boolean } {
  const id = asked === null ? 0 : asked.id;
  if (seen === null) return { seen: id, act: false };
  if (asked === null || id === seen) return { seen, act: false };
  return { seen: id, act: true };
}

/** The notification's button pressed (card #41): the card opens on its project's board — a hash on this page, a navigation when the card is another project's. */
export function showCard(slug: string, shown: Shown): void {
  const hash = `#card-${shown.card_number}`;
  if (shown.project === slug) {
    if (window.location.hash !== hash) window.location.hash = hash;
    return;
  }
  window.location.assign(`/p/${encodeURIComponent(shown.project)}${hash}`);
}

export function useBoard(slug: string): BoardStore {
  const [board, setBoard] = useState<BoardState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [statuses, setStatuses] = useState<Record<number, MoveStatus>>({});
  const version = useRef(-1);
  // The first `shown` the page hears is one it was not asked for: it was
  // raised before this page existed, or before it reconnected.
  const shown = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await getBoard(slug);
      version.current = next.version;
      setBoard(next);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [slug]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    const source = new EventSource(streamUrl(slug));
    source.addEventListener("board", (event: MessageEvent<string>) => {
      const data: unknown = JSON.parse(event.data);
      if (!isBoardEvent(data)) return;
      if (data.version !== version.current) void refresh();
      const asked = data.shown ?? null;
      const next = nextShown(shown.current, asked);
      shown.current = next.seen;
      if (next.act && asked !== null) showCard(slug, asked);
    });
    // A reconnect — the server restarted, the page slept — forgets the version
    // it knew, so the first message re-reads the board exactly once: a new
    // server's counter can land on the old number and say nothing changed.
    let opened = 0;
    source.onopen = () => {
      setConnected(true);
      if (opened++ > 0) version.current = -1;
    };
    source.onerror = () => setConnected(false);
    return () => source.close();
  }, [slug, refresh]);

  const setStatus = useCallback((number: number, status: MoveStatus) => {
    setStatuses((s) => ({ ...s, [number]: status }));
  }, []);

  const move = useCallback(
    async (number: number, to: Place): Promise<boolean> => {
      setStatus(number, { kind: "saving" });
      try {
        const next = await moveCard(slug, number, to);
        version.current = next.version;
        setBoard(next);
        setStatus(number, IDLE);
        return true;
      } catch (e) {
        const reason = e instanceof ApiError ? e.message : `${String(e)}`;
        setStatus(number, { kind: "failed", reason, to });
        return false;
      }
    },
    [slug, setStatus],
  );

  const retry = useCallback(
    async (number: number): Promise<boolean> => {
      const status = statuses[number];
      if (!status || status.kind !== "failed") return false;
      return move(number, status.to);
    },
    [statuses, move],
  );

  const dismiss = useCallback((number: number) => setStatus(number, IDLE), [setStatus]);

  return { board, error, connected, statuses, refresh, move, retry, dismiss };
}
