/** The doors into the backend, typed by the generated mirrors of the domain. */

import type { BoardState, CardDetail, ProjectFile } from "./types/board";
import type { Move, Place } from "./types/card";
import type { DialState } from "./types/dial";
import type { FocusStrip } from "./types/focus";
import type { DoorResult } from "./types/lane";
import type { Project } from "./types/project";
import type { EvidenceClass, VerdictsRuled } from "./types/verdict";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    throw new ApiError(0, `The board could not be reached: ${error instanceof Error ? error.message : String(error)}`);
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body: unknown = await response.json();
      if (typeof body === "object" && body !== null && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        detail = typeof d === "string" ? d : JSON.stringify(d);
      }
    } catch {
      /* the status line is the detail */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function getProjects(): Promise<Project[]> {
  return call<Project[]>("/api/projects");
}

export function getBoard(slug: string): Promise<BoardState> {
  return call<BoardState>(`/api/projects/${encodeURIComponent(slug)}/board`);
}

export function getCard(slug: string, number: number): Promise<CardDetail> {
  return call<CardDetail>(`/api/projects/${encodeURIComponent(slug)}/cards/${number}`);
}

export function getFile(slug: string, path: string): Promise<ProjectFile> {
  return call<ProjectFile>(`/api/projects/${encodeURIComponent(slug)}/files?path=${encodeURIComponent(path)}`);
}

export function moveCard(slug: string, number: number, to: Place): Promise<BoardState> {
  const body: Move = { to };
  return call<BoardState>(`/api/projects/${encodeURIComponent(slug)}/cards/${number}/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** The doors a card offers; each answers with what it did, or fails by name. */
export type DoorName = "start" | "answer" | "watch" | "look" | "discuss" | "resume" | "stop" | "signal" | "accept" | "overturn";

export function openDoor(slug: string, number: number, door: DoorName, body: object = {}): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/cards/${number}/${door}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** The head's Idea door: a conversation about nothing yet, with the owner's first line when he typed one (plan 07, item 1). */
export function openIdea(slug: string, text: string): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/idea`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

/** The Plan door: a plan-writing conversation for one suggestion card, or one plan for several (plan 06, item 5). */
export function openPlan(slug: string, numbers: number[]): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numbers }),
  });
}

/** Accept every unread verdict in one class, each as its own act; the answer counts and names refusals. */
export function acceptClass(slug: string, evidenceClass: EvidenceClass): Promise<VerdictsRuled> {
  return call<VerdictsRuled>(`/api/projects/${encodeURIComponent(slug)}/triage/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ evidence_class: evidenceClass }),
  });
}

/** The dial (plan 11, item 3): the owner's standing ruling that a defect marked `Fix: now` enters execution without him — one board's switch, and the machine's number of fix lanes at once (card #80). Answers that board's head. */
export function turnDial(slug: string, on: boolean, lanes: number): Promise<DialState> {
  return call<DialState>("/api/dial", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project: slug, on, lanes }),
  });
}

/** The strip as the board shows it (card #87): the same object `needle strip` prints. */
export function getFocus(slug: string): Promise<FocusStrip> {
  return call<FocusStrip>(`/api/projects/${encodeURIComponent(slug)}/focus`);
}

/** The Focus door: a conversation that sharpens what matters now and finds what holds it back (card #87, item 2). */
export function openFocus(slug: string, text: string): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/focus`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

/** "Propose moves": the same conversation, asked what else could move the limit. */
export function proposeMoves(slug: string): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/focus/propose`, { method: "POST" });
}

/** "Use this focus": the owner's ruling, bound to the document's fingerprint (card #87, item 1). */
export function chooseFocus(slug: string): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/focus/choose`, { method: "POST" });
}

/** "Accept this order": the ticked moves through the move door, with the owner's name on each (card #87, item 5). */
export function acceptOrder(slug: string, numbers: number[]): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/leverage/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numbers }),
  });
}

/** "Put it back": every card of the last acceptance to its recorded place. */
export function putBack(slug: string): Promise<DoorResult> {
  return call<DoorResult>(`/api/projects/${encodeURIComponent(slug)}/leverage/put-back`, { method: "POST" });
}

export function streamUrl(slug: string): string {
  return `/api/projects/${encodeURIComponent(slug)}/stream`;
}
