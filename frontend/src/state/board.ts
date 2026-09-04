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

export function useBoard(slug: string): BoardStore {
  const [board, setBoard] = useState<BoardState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [statuses, setStatuses] = useState<Record<number, MoveStatus>>({});
  const version = useRef(-1);

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
      if (typeof data === "object" && data !== null && "version" in data) {
        const v = (data as { version: unknown }).version;
        if (typeof v === "number" && v !== version.current) void refresh();
      }
    });
    source.onopen = () => setConnected(true);
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
