import "./tokens.css";
import "./primitives.css";
import { useEffect, useState, type FocusEventHandler, type KeyboardEvent, type MouseEvent, type PointerEventHandler, type ReactNode, type Ref } from "react";
import type { DraggableAttributes } from "@dnd-kit/core";
import { marked } from "marked";
import DOMPurify from "dompurify";
import type { CardState, ClaimCount, FoldedCard, Meaning } from "../../types/board";
import type { Column } from "../../types/column";
import type { DialState } from "../../types/dial";
import type { DocumentState, Fix, Item, Review, SuggestionKind } from "../../types/document";
import type { Progress } from "../../types/lane";
import type { Standing } from "../../types/evidence";
import type { RowKind } from "../../types/row";
import { ASK_ROWS } from "../../types/row";

// ── text ──────────────────────────────────────────────────────────────

const INLINE = /(`[^`]+`|\*\*[^*]+\*\*)/g;

/** Plain text with two marks: backticks for code, double asterisks for bold. */
export function Inline({ text }: { text: string }) {
  const parts = text.split(INLINE);
  return (
    <span className="inline">
      {parts.map((part, i) => {
        if (part.startsWith("`") && part.endsWith("`") && part.length > 1) {
          return <code key={i}>{part.slice(1, -1)}</code>;
        }
        if (part.startsWith("**") && part.endsWith("**") && part.length > 3) {
          return <b key={i}>{part.slice(2, -2)}</b>;
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}

marked.setOptions({ gfm: true, breaks: false });

/** Markdown rendered from a document, sanitised, in the plan block's type. */
export function Markdown({ text }: { text: string }) {
  const html = DOMPurify.sanitize(marked.parse(text, { async: false }));
  return <div className="plan-body" dangerouslySetInnerHTML={{ __html: html }} />;
}

// ── the head ──────────────────────────────────────────────────────────

/**
 * The head, pinned above the columns. One line, always: the wordmark, the
 * project pill with the quiet facts behind it, the three words that are
 * filters of the board, the lens and the Idea door (plan 27, item 1). It
 * never expands on its own, so it never needs to fold.
 */
export function HeadFrame({ children }: { children: ReactNode }) {
  return <div className="head">{children}</div>;
}

export function AppHead({ children }: { children: ReactNode }) {
  return <header className="app-head">{children}</header>;
}

export function Wordmark() {
  return <span className="wordmark">Needle</span>;
}

/**
 * The project pill is the switcher: a native select wearing the pill, so it
 * is one keyboard-reachable control with no menu of its own to manage, and
 * the path it lands on is the page's only state (plan 01b, item 1).
 */
export function ProjectSwitcher({ projects, current, onSwitch, facts }: { projects: readonly { slug: string; name: string }[]; current: string; onSwitch: (slug: string) => void; facts?: ReactNode }) {
  return (
    <label className="project" title="The projects on the board. Choosing one goes to its own address, /p/<slug>.">
      <select aria-label="Project" value={current} onChange={(e) => onSwitch(e.target.value)}>
        {projects.map((p) => (
          <option key={p.slug} value={p.slug}>
            {p.name}
          </option>
        ))}
      </select>
      <span className="caret" aria-hidden="true">
        ▾
      </span>
      {facts ? (
        <span className="facts" role="note">
          {facts}
        </span>
      ) : null}
    </label>
  );
}

/** One quiet fact behind the project pill; `meaning` only where one holds. */
export function Fact({ children, meaning }: { children: ReactNode; meaning?: Meaning }) {
  return (
    <span className="fact" {...(meaning ? { "data-meaning": meaning } : {})}>
      {children}
    </span>
  );
}

export function CorpusLine({ children }: { children: ReactNode }) {
  return <span className="corpus">{children}</span>;
}

export function Strong({ children }: { children: ReactNode }) {
  return <b>{children}</b>;
}

/** The corpus is not being watched: the board cannot see what it reads from. */
export function Off({ children }: { children: ReactNode }) {
  return (
    <span className="off" data-meaning="broken">
      {children}
    </span>
  );
}

export function HeadTools({ children }: { children: ReactNode }) {
  return <span className="grow">{children}</span>;
}

export function Lens<T extends string>({
  value,
  options,
  onChange,
  title,
}: {
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (value: T) => void;
  title: string;
}) {
  return (
    <span className="lens" title={title} role="group" aria-label={title}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          className={o.value === value ? "on" : ""}
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </span>
  );
}

/**
 * The Idea door in the head (plan 07, item 1): one click opens a conversation
 * about nothing yet, and the optional line beside it lands as the session's
 * opening prompt. Empty means the session asks.
 */
export function IdeaDoor({ onOpen, disabled, said }: { onOpen: (text: string) => void; disabled: boolean; said: string | null }) {
  return (
    <form
      className="idea"
      title="Opens a conversation in this project's checkout, about nothing yet. What it writes into the corpus becomes a card."
      onSubmit={(e) => {
        e.preventDefault();
        const field = e.currentTarget.elements.namedItem("idea") as HTMLInputElement | null;
        onOpen(field?.value.trim() ?? "");
        if (field) field.value = "";
      }}
    >
      <input name="idea" type="text" aria-label="Your first line" title="One line that lands as the session's opening prompt; empty means the session asks" disabled={disabled} autoComplete="off" />
      <button type="submit" className="btn" disabled={disabled}>
        Idea
      </button>
      {said ? <span className="said">{said}</span> : null}
    </form>
  );
}

/**
 * The dial in the head (plan 11, item 3): the owner's standing ruling that
 * a defect its finder marked `Fix: now` enters execution without him — a
 * toggle, the number of fix lanes that may run at once, and the fix lanes
 * live against that number. One dial for the whole board, because its limit
 * is the machine's slots and its one trunk. The number lands on blur or
 * Enter, so a keystroke is not a turn; the count is the one part that can
 * carry a meaning, and only while something runs.
 */
export function DialControl({ state, onTurn, disabled, said }: { state: DialState; onTurn: (on: boolean, lanes: number) => void; disabled: boolean; said: string | null }) {
  const { dial, running, held, full, quiet } = state;
  const [lanes, setLanes] = useState(String(dial.lanes));
  useEffect(() => {
    setLanes(String(dial.lanes));
  }, [dial.lanes]);
  const commit = () => {
    const wanted = Number.parseInt(lanes, 10);
    if (Number.isNaN(wanted) || wanted < 0) {
      setLanes(String(dial.lanes));
      return;
    }
    if (wanted !== dial.lanes) onTurn(dial.on, wanted);
  };
  return (
    <form
      className="dial"
      role="group"
      aria-label="Auto-fix"
      title="Auto-fix: while on, the board plans and starts a defect marked Fix: now on its own, up to this many fix lanes at once, and the lane then runs like every other lane. One dial for the whole board. The board's own defects run only while no lane is live anywhere."
      onSubmit={(e) => {
        e.preventDefault();
        commit();
      }}
    >
      <label className="dial-on">
        <input type="checkbox" checked={dial.on} disabled={disabled} onChange={(e) => onTurn(e.target.checked, dial.lanes)} aria-label="Auto-fix defects" />
        <span>auto-fix</span>
      </label>
      <input className="dial-lanes" type="number" inputMode="numeric" min={0} value={lanes} disabled={disabled} aria-label="Fix lanes at once" onChange={(e) => setLanes(e.target.value)} onBlur={commit} />
      <span className="dial-live" {...(running > 0 ? { "data-meaning": "live" as const } : {})} title={quiet ? "No lane has hands on any project: the board's own defects may run" : "A lane has hands on a project: the board's own defects wait"}>
        {running} of {dial.lanes} live
      </span>
      {held > 0 ? (
        <span className="dial-held" title="Planned cards the dial holds without counting them: their Start door is closed — parked, waiting on a Sequencing card, nowhere to run — so they are no process and take no slot">
          {held} held
        </span>
      ) : null}
      {full ? (
        <span className="dial-full" data-meaning="broken" title="The memory floor: while available memory or free swap is under it the dial opens nothing. The floor is the board's; the number stays yours">
          {full}
        </span>
      ) : null}
      {said ? <span className="said">{said}</span> : null}
    </form>
  );
}

// ── the three words, and their breakdown ──────────────────────────────

export function Words({ children }: { children: ReactNode }) {
  return (
    <span className="words" role="group" aria-label="What needs you">
      {children}
    </span>
  );
}

/**
 * One of the head's three words: its meaning's colour, its count, and a
 * filter of the board. A word nobody has to act on is quiet, whatever its
 * count — a number is never coloured for being large (plan 27, item 1).
 */
export function Word({ label, count, meaning, on, onClick }: { label: string; count: number; meaning: Meaning; on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      className="word"
      data-meaning={count > 0 ? meaning : "quiet"}
      data-word={label}
      aria-pressed={on}
      disabled={count === 0}
      onClick={onClick}
      title={count === 0 ? `Nothing is ${label.toLowerCase()}` : `Show only the cards this counts`}
    >
      {label} <b>{count}</b>
    </button>
  );
}

/** The chosen word's breakdown, as sub-filters that narrow the board. */
export function Breakdown({ children, label, onClear }: { children: ReactNode; label: string; onClear: () => void }) {
  return (
    <div className="breakdown" role="group" aria-label={label}>
      {children}
      <button type="button" className="clear" onClick={onClear}>
        clear
      </button>
    </div>
  );
}

export function Sub({ line, meaning, on, onClick }: { line: ClaimCount; meaning: Meaning; on: boolean; onClick: () => void }) {
  return (
    <button type="button" className="sub" data-meaning={meaning} data-claim={line.claim} aria-pressed={on} onClick={onClick}>
      <b>{line.count}</b> {line.label}
    </button>
  );
}

/** The bar over a selection of suggestion cards: one Plan door for all of them (plan 06, item 5). */
export function TogetherBar({ count, onPlan, onClear, disabled, said }: { count: number; onPlan: () => void; onClear: () => void; disabled: boolean; said: string | null }) {
  return (
    <section className="together" aria-label={`${count} suggestion${count === 1 ? "" : "s"} selected for one plan`}>
      <span className="together-n">
        <b>{count}</b> suggestion{count === 1 ? "" : "s"} selected for one plan
      </span>
      <button type="button" className="btn" onClick={onPlan} disabled={disabled || count === 0}>
        Plan these together
      </button>
      <button type="button" className="btn ghost" onClick={onClear} disabled={disabled}>
        Clear
      </button>
      {said ? <span className="said">{said}</span> : null}
    </section>
  );
}

/** The batched question: every shipped card waiting on the owner's reading, one click each way per card (plan 04, item 3). */
export function AskList({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="asks" aria-label={title} data-meaning="yours">
      <div className="asks-h">{title}</div>
      {children}
    </section>
  );
}

export function AskRow({ number, title, what, due, evidence, onRead, disabled }: { number: number; title: string; what: string; due: string; evidence: string | null; onRead: (delivered: boolean) => void; disabled: boolean }) {
  return (
    <div className="ask-row" role="listitem">
      <span className="cid">#{number}</span>
      <span className="ask-title">{title}</span>
      <span className="ask-what">
        {what}
        {evidence ? <span className="ask-evidence">A session read it and could not tell: {evidence}</span> : null}
      </span>
      <span className="ask-due">due {due}</span>
      <span className="ask-acts">
        <button type="button" className="btn" onClick={() => onRead(true)} disabled={disabled}>
          Delivered
        </button>
        <button type="button" className="btn ghost" onClick={() => onRead(false)} disabled={disabled}>
          Not delivered
        </button>
      </span>
    </div>
  );
}

/** Every conversation alive right now — an idea, or a card's Discuss — as the rail lists them (plan 07, item 1). */
export function TalkList({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="talks" aria-label={title} data-meaning="live">
      <div className="talks-h">{title}</div>
      {children}
    </section>
  );
}

export function TalkRow({ what, shortId, slot, since }: { what: string; shortId: string; slot: string; since: string }) {
  return (
    <div className="talk-row" role="listitem">
      <span className="talk-what">{what}</span>
      <span className="talk-where">
        {shortId} on {slot}
      </span>
      <span className="talk-since">since {since}</span>
    </div>
  );
}

// ── the board and its columns ─────────────────────────────────────────

export function BoardStrip({ children }: { children: ReactNode }) {
  return <main className="board">{children}</main>;
}

/** A column scrolls on its own (plan 06, item 4). It is never coloured: a
 * column is a stage, not a state — the cards in it say what they are. */
export function ColumnBox({ children, wide, column }: { children: ReactNode; wide: boolean; column: string }) {
  return (
    <section className={`col${wide ? " wide" : ""}`} data-column={column}>
      {children}
    </section>
  );
}

/** The column's head and note, pinned at its top while its cards scroll under them. */
export function ColumnTop({ children }: { children: ReactNode }) {
  return <div className="col-top">{children}</div>;
}

/** Backlog's defects rail: pinned at the column's top with its count, furled to that line by default so ideas are one scan and defects another (plan 06, item 2). */
export function RailGroup({ count, open, onToggle, children }: { count: number; open: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <div className="rail-group" data-rail="defects">
      <button type="button" className="rail-h" aria-expanded={open} onClick={onToggle} title={open ? "Furl the defects rail" : "Show the defects"}>
        <span className="rail-name">Defects</span>
        <span className="count">{count}</span>
        <span className="rail-tw">{open ? "▾ furl" : "▸ show"}</span>
      </button>
      {open ? children : null}
    </div>
  );
}

export function ColumnHead({
  name,
  count,
  tools,
  definition,
}: {
  name: string;
  count: number;
  tools: ReactNode;
  definition: ReactNode;
}) {
  return (
    <header className="col-head" tabIndex={0}>
      <h2>{name}</h2>
      <span className="count">{count}</span>
      <span className="tools">{tools}</span>
      {definition}
    </header>
  );
}

export function ColumnNote({ children }: { children: ReactNode }) {
  return <p className="col-note">{children}</p>;
}

export function Definition({
  name,
  paragraphs,
  movedBy,
  toLeft,
}: {
  name: string;
  paragraphs: string[];
  movedBy: string;
  toLeft: boolean;
}) {
  return (
    <div className={`def${toLeft ? " to-left" : ""}`} role="note">
      <div className="dk">{name}</div>
      {paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
      <div className="who">
        Moved by <b>{movedBy}</b>
      </div>
    </div>
  );
}

export function Tool({ on, onClick, children, label }: { on?: boolean; onClick: () => void; children: ReactNode; label: string }) {
  return (
    <button type="button" className={`tool${on ? " on" : ""}`} onClick={onClick} aria-label={label} aria-pressed={on ?? false}>
      {children}
    </button>
  );
}

export function Stack({ children }: { children: ReactNode }) {
  return <div className="stack">{children}</div>;
}

export function GroupHead({ name }: { name: string }) {
  return <h3 className="group-h">{name}</h3>;
}

export function GroupBody({ children, nodeRef, label, id }: { children: ReactNode; nodeRef: Ref<HTMLDivElement>; label: string; id: string }) {
  return (
    <div className="group-body" ref={nodeRef} role="list" aria-label={label} data-group={id}>
      {children}
    </div>
  );
}

export function MoreRow({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="more-row" onClick={onClick}>
      {children}
    </button>
  );
}

export function Rail({ name, count, onClick }: { name: string; count: number; onClick: () => void }) {
  return (
    <aside
      className="rail"
      title={`${name} — click to unfurl`}
      aria-label={`${name} — click to unfurl`}
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e: KeyboardEvent<HTMLElement>) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <span className="rcount">{count}</span>
      <span className="rname">{name}</span>
      <span className="runfurl">⟩</span>
    </aside>
  );
}

// ── the card ──────────────────────────────────────────────────────────

export interface CardShellProps {
  number: number;
  meaning: Meaning;
  children: ReactNode;
  open?: boolean;
  saving?: boolean;
  failed?: boolean;
  ghost?: boolean;
  lift?: boolean;
  isStatic?: boolean;
  nodeRef?: Ref<HTMLElement> | undefined;
  onClick?: ((e: MouseEvent<HTMLElement>) => void) | undefined;
  onKeyDown?: ((e: KeyboardEvent<HTMLElement>) => void) | undefined;
  dragProps?: DragProps | undefined;
  label: string;
}

/** What dnd-kit hands a draggable — its attributes and the pointer listener — plus the focus hooks the board adds. */
export type DragProps = Omit<DraggableAttributes, "role"> & {
  onPointerDown?: PointerEventHandler<HTMLElement> | undefined;
  onFocus: FocusEventHandler<HTMLElement>;
  onBlur: FocusEventHandler<HTMLElement>;
};

/** The article every card is. `dragProps` are dnd-kit's listeners and attributes, spread as given. */
export function CardShell({ number, meaning, children, open, saving, failed, ghost, lift, isStatic, nodeRef, onClick, onKeyDown, dragProps, label }: CardShellProps) {
  const classes = ["card"];
  if (open) classes.push("open");
  if (saving) classes.push("saving");
  if (failed) classes.push("failed");
  if (ghost) classes.push("ghost");
  if (lift) classes.push("lift");
  if (isStatic) classes.push("static");
  return (
    <article
      className={classes.join(" ")}
      data-meaning={failed ? "broken" : meaning}
      data-card={number}
      id={`card-${number}`}
      ref={nodeRef}
      tabIndex={0}
      aria-label={label}
      onClick={onClick}
      onKeyDown={onKeyDown}
      {...(dragProps ?? {})}
      role="listitem"
    >
      {children}
    </article>
  );
}

export function CardTop({ children }: { children: ReactNode }) {
  return <div className="card-top">{children}</div>;
}

export function Grow() {
  return <span className="grow" />;
}

export function Cid({ n }: { n: number }) {
  return <span className="cid">#{n}</span>;
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h3 className="card-title">{children}</h3>;
}

/**
 * One line of essence — or, when the state has something to say, its words in
 * the essence's place: a lane's question, a doubt, a signal and when it is
 * due (plan 27, item 2). `said` marks the second, which reads in ink on a
 * card that is asking you.
 */
export function Essence({ children, said }: { children: ReactNode; said?: boolean }) {
  return <p className={`essence${said ? " said" : ""}`}>{children}</p>;
}

/**
 * The state line: one word in its meaning's colour, always bottom-left, and
 * the one door that state allows, always bottom-right — or, when no door
 * opens, what opening the card gives (plan 27, item 2). The word and the
 * door both come from the board; the page invents neither.
 */
export function StateLine({ state, children }: { state: CardState; children?: ReactNode }) {
  return (
    <div className="state" {...(state.loop ? { "data-loop": state.loop.state } : {})}>
      <span className="state-word">
        {state.loop ? <LoopGlyph loop={state.loop} /> : null}
        <span className="say">{state.word}</span>
      </span>
      <Grow />
      {children}
      {state.door === null && state.hint ? <span className="hint">{state.hint}</span> : null}
    </div>
  );
}

/**
 * The open card's top answers three questions in order: what is this, what is
 * happening to it right now, and what can I do about it. This is the second —
 * the state sentence under the title, in the state's own colour (plan 27,
 * item 4).
 */
export function StateSentence({ state }: { state: CardState }) {
  return (
    <div className="state-sentence" role="status">
      {state.loop ? <LoopGlyph loop={state.loop} /> : <span className="dot" />}
      <span className="say">{state.word}</span>
      {state.detail ? <span className="then">— {state.detail}</span> : null}
    </div>
  );
}

/**
 * A shipped card's loop: an open ring in ink — a live obligation, just not
 * yours — or a filled dot in green once the signal was read. An owner-only
 * signal's ring is amber, because only he can close it (plan 27, item 3).
 */
export function LoopGlyph({ loop }: { loop: NonNullable<CardState["loop"]> }) {
  const owned = loop.state === "open" && loop.owner_only;
  return (
    <span
      className={`loop ${loop.state}`}
      aria-hidden="true"
      {...(loop.state === "closed" ? { "data-meaning": "proven" as const } : owned ? { "data-meaning": "yours" as const } : {})}
    />
  );
}

/**
 * The gesture for planning several suggestions together, kept out of the
 * card's one-door anatomy: it appears when the hand is on the card, so at
 * rest every card still reads as one state and one door (plan 27, item 2).
 */
export function Pickable({ children }: { children: ReactNode }) {
  return <span className="pickable">{children}</span>;
}

/** A checkbox on the collapsed face, for planning several suggestions together. */
export function Pick({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return (
    <label className="pick" title={label}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
    </label>
  );
}

/** The cards folded under this one: the suggestions its plan carries (plan 06, item 5). */
export function Carries({ cards, open }: { cards: readonly FoldedCard[]; open: boolean }) {
  if (!cards.length) return null;
  return (
    <div className={`carries${open ? " open" : ""}`} role="list" aria-label={`carries ${cards.length}`}>
      <span className="clbl">carries</span>
      {cards.map((c) => (
        <span key={c.number} role="listitem" className="carried" title={c.document_path ?? c.title}>
          <span className="cid">#{c.number}</span>
          {open ? <span className="ctitle">{c.title}</span> : null}
        </span>
      ))}
    </div>
  );
}

export function Chip({
  kind = "plain",
  children,
  onClick,
  title,
}: {
  kind?: "plain" | "gate" | "tag";
  children: ReactNode;
  onClick?: (() => void) | undefined;
  title?: string | undefined;
}) {
  const className = `chip${kind === "plain" ? "" : ` ${kind}`}`;
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick} title={title}>
        {children}
      </button>
    );
  }
  return (
    <span className={className} title={title}>
      {children}
    </span>
  );
}

export function Caret({ open }: { open: boolean }) {
  return <span className="caret-g">{open ? "▼" : "▶"}</span>;
}

const DOC_LABEL: Record<DocumentState, string> = {
  plan: "plan",
  suggestion: "suggestion",
  archived: "archived",
  note: "note",
  gone: "gone",
};

const DOC_WHY: Record<DocumentState, string> = {
  plan: "A plan is written behind this card",
  suggestion: "A suggestion is written behind this card; no plan yet",
  archived: "Its document is archived: the work shipped",
  note: "Nothing is written behind this card — it is your own note",
  gone: "This card cites a document, and no such file exists",
};

const FIX_WHY: Record<Fix["mark"], string> = {
  now: "its finder marked it a straight fix: the dial may plan and start it without the owner",
  when: "its fix waits for a trigger the board reads; delivered makes it a now",
  his: "its fix implies a decision the owner has to make first",
};

/**
 * What is written behind a card, right-aligned on its first line: a fact,
 * never a claim, so it is quiet monospace and never a hue. A suggestion says
 * which kind it is — defects and ideas are two rails, not two colours — and
 * a defect says who fixes it, from its `Fix:` line (plan 11, item 2):
 * `now`, `when`, `his`, or `unmarked` when the line is missing, which the
 * dial reads as his.
 */
export function Kind({ state, kind, fix, path }: { state: DocumentState; kind: SuggestionKind | null; fix?: Fix | null; path: string | null }) {
  const marked = state === "suggestion" && kind === "defect";
  const mark = marked ? (fix ? fix.mark : "unmarked") : null;
  const word = state === "suggestion" && kind ? kind : DOC_LABEL[state];
  const why = mark ? `; Fix: ${mark} — ${fix ? FIX_WHY[fix.mark] + (fix.trigger ? ` (${fix.trigger})` : fix.why ? ` (${fix.why})` : "") : "no Fix: line on its head; an unmarked defect reads as his"}` : "";
  return (
    <span className="kind" data-doc={state} {...(mark ? { "data-fix": mark } : {})} title={(path ? `${DOC_WHY[state]}: ${path}` : DOC_WHY[state]) + why}>
      {mark ? `${word} · ${mark}` : word}
    </span>
  );
}

export function FailNote({ reason, onRetry }: { reason: string; onRetry: () => void }) {
  return (
    <div className="fail-note" role="alert">
      <span>
        <b>Not moved.</b> {reason} The card is where it was.
      </span>
      <button type="button" className="retry" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}

export function DropGap({ label }: { label: string }) {
  return (
    <div className="drop-gap" role="status" aria-live="polite" data-meaning="live">
      <span className="lands">{label}</span>
    </div>
  );
}

export function KbdHint({ lifted }: { lifted: boolean }) {
  return (
    <div className="kbd-hint">
      {lifted ? (
        <>
          <kbd>↑</kbd>
          <kbd>↓</kbd> move <kbd>←</kbd>
          <kbd>→</kbd> column <kbd>space</kbd> drop <kbd>esc</kbd> cancel
        </>
      ) : (
        <>
          <kbd>space</kbd> lift <kbd>enter</kbd> open
        </>
      )}
    </div>
  );
}

// ── the expanded card ─────────────────────────────────────────────────

export function OpenBody({ children }: { children: ReactNode }) {
  return <div className="open-body">{children}</div>;
}

export function Section({ title, from, children }: { title: string; from?: string | undefined; children: ReactNode }) {
  return (
    <div className="sec">
      <div className="sec-h">
        {title}
        {from ? <span className="from">{from}</span> : null}
      </div>
      {children}
    </div>
  );
}

export function EssenceBig({ children }: { children: ReactNode }) {
  return <p className="essence-big">{children}</p>;
}

export function Quiet({ children }: { children: ReactNode }) {
  return <p className="q">{children}</p>;
}

export function Note({ children }: { children: ReactNode }) {
  return <div className="note">{children}</div>;
}

/** One row of the brief or the record. Its label is quiet unless the row is
 * the owner's own move to make, which is the one claim a row can carry. */
export function RowLine({ kind, text }: { kind: RowKind; text: string }) {
  return (
    <div className="row">
      <span className="lbl" {...(ASK_ROWS.includes(kind) ? { "data-meaning": "yours" as const } : {})}>
        {kind}
      </span>
      <span className="val">
        <Inline text={text} />
      </span>
    </div>
  );
}

export function PlanBlock({ children }: { children: ReactNode }) {
  return <div className="plan-block">{children}</div>;
}

export function PlanHead({ path, toggle, open, toggleLabel }: { path: string; toggle: () => void; open: boolean; toggleLabel: string }) {
  return (
    <div className="plan-head">
      <span className="path">{path}</span>
      <button type="button" className="tw" onClick={toggle} aria-expanded={open}>
        <Caret open={open} /> {toggleLabel}
      </button>
    </div>
  );
}

export function PlanBody({ children }: { children: ReactNode }) {
  return <div className="plan-body">{children}</div>;
}

export function StatLines({ children }: { children: ReactNode }) {
  return <div className="statlines">{children}</div>;
}

export function StatLine({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="statline">
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

export function PathText({ children }: { children: ReactNode }) {
  return <span className="path">{children}</span>;
}

export function Hist({ children }: { children: ReactNode }) {
  return <div className="hist">{children}</div>;
}

export function HistRow({ when, what, who, owner }: { when: string; what: ReactNode; who: string; owner: boolean }) {
  return (
    <div className="h">
      <span className="when">{when}</span>
      <span className="what">{what}</span>
      <span className={`who${owner ? " owner" : ""}`}>{who}</span>
    </div>
  );
}

export function Acts({ children }: { children: ReactNode }) {
  return <div className="acts">{children}</div>;
}

export function Button({ ghost, small, onClick, children, disabled, title, label }: { ghost?: boolean; small?: boolean; onClick: () => void; children: ReactNode; disabled?: boolean; title?: string | undefined; label?: string | undefined }) {
  return (
    <button type="button" className={`btn${ghost ? " ghost" : ""}${small ? " small" : ""}`} onClick={onClick} disabled={disabled ?? false} title={title} aria-label={label}>
      {children}
    </button>
  );
}

/** A door that does not open still shows, with why, so the owner knows what the card cannot do and why. */
export function ClosedDoor({ children, why }: { children: ReactNode; why: string }) {
  return (
    <span className="btn ghost off" title={why} aria-disabled="true">
      {children}
    </span>
  );
}

/**
 * The lane reporting in, on the open card: the card's own state word — the
 * same word the collapsed face shows, in the same colour — and the lane's
 * whole sentence beside it. The page makes no second judgment about a lane.
 */
export function Band({ state, children }: { state: CardState; children: ReactNode }) {
  return (
    <div className="band" role="status" data-meaning={state.meaning}>
      <span className="bstate">{state.word}</span>
      <span className="bsay">{children}</span>
    </div>
  );
}

/** The board doubts a machine-placed status: its evidence is gone, and the missing fact is said (plan 04, item 1). */
export function Doubt({ children }: { children: ReactNode }) {
  return (
    <div className="doubt" role="status" data-meaning="broken">
      <span className="bstate">Doubted</span>
      <span className="bsay">{children}</span>
    </div>
  );
}

/** Two live lanes are editing the same file: named on both cards, before the fold (plan 07, item 2). */
export function Clash({ children }: { children: ReactNode }) {
  return (
    <div className="clash" role="status" data-meaning="broken">
      <span className="bstate">Colliding</span>
      <span className="bsay">{children}</span>
    </div>
  );
}

/**
 * How far a running lane has come, in its own words (plan 13): one segment
 * per item of the plan — met in the live colour, the lane's own; deviated
 * outlined; the rest quiet — and under it the count and the last item marked,
 * or the review counter once every item is met. Nothing here is green: a met
 * item is the lane's claim, and green is the board's word for a loop it
 * closed itself (ruling 4). The counter is red while the loop is open and
 * quiet once a pass reads clean (ruling 5). The line is the board's; the
 * page invents no words.
 */
export function Strip({ items, label }: { items: readonly Item[]; label: string }) {
  return (
    <span className="strip" data-meaning="live" role="img" aria-label={label}>
      {items.map((item) => (
        <span key={item.number} className={`seg ${item.stance ?? "open"}`} title={`${item.number}. ${item.title}${item.stance ? ` — ${item.stance}` : ""}`} />
      ))}
    </span>
  );
}

export function HowFar({ progress }: { progress: Progress }) {
  const open = progress.review !== null && !progress.review.clean;
  return (
    <div className="howfar" role="status">
      <Strip items={progress.items} label={progress.line} />
      <span className="howfar-line" {...(open ? { "data-meaning": "broken" as const } : {})} title={`${progress.line} — as the lane wrote it in its own copy of the plan`}>
        {progress.line}
      </span>
    </div>
  );
}

const STANCE_WORD = { met: "met", deviated: "deviated" } as const;

/**
 * The plan's items on the open card, in order, each with its stance and
 * what stands beside it: the evidence for a met item, the pointer for a
 * deviated one, the item's own "done means" for one not yet met — so what
 * is left is readable without opening the plan.
 */
export function Items({ items }: { items: readonly Item[] }) {
  return (
    <div className="items" role="list" aria-label="the plan's items">
      {items.map((item) => (
        <div key={item.number} className="item" role="listitem" data-stance={item.stance ?? "open"}>
          <span className="inum">{item.number}</span>
          <span className="ibody">
            <span className="ihead">
              <span className="ititle">{item.title}</span>
              <span className="istance" {...(item.stance ? { "data-meaning": "live" as const } : {})}>
                {item.stance ? STANCE_WORD[item.stance] : "not yet"}
              </span>
            </span>
            {item.stance && item.text ? <span className="itext">{item.text}</span> : null}
            {!item.stance && item.done_means ? <span className="itext quiet">done means: {item.done_means}</span> : null}
          </span>
        </div>
      ))}
    </div>
  );
}

/** The review loop on the open card: one row per pass with its lens and what it found — the pass still open is the red one — and the findings this lane filed rather than fixed. */
export function Passes({ review }: { review: Review }) {
  const last = review.passes.length;
  return (
    <div className="passes" role="list" aria-label="the review's passes">
      {review.passes.map((pass) => {
        const open = pass.number === last && !pass.clean;
        return (
          <div key={pass.number} className="item" role="listitem">
            <span className="inum">{pass.number}</span>
            <span className="ibody">
              <span className="ihead">
                <span className="ititle">{pass.lens}</span>
                <span className="istance" {...(open ? { "data-meaning": "broken" as const } : {})}>
                  {pass.clean ? "clean" : open ? "open" : "read"}
                </span>
              </span>
              {pass.text ? <span className="itext">{pass.text}</span> : null}
            </span>
          </div>
        );
      })}
      {review.filed_names.map((name) => (
        <div key={name} className="item filed" role="listitem">
          <span className="inum">filed</span>
          <span className="ibody">
            <span className="itext">{name} — outside this change; a defect on the rail when the lane folds</span>
          </span>
        </div>
      ))}
    </div>
  );
}

/** The watercooler's last line, on every card with hands on it: what the lanes last said to each other. */
export function Heard({ who, children }: { who: string; children: ReactNode }) {
  return (
    <div className="heard" role="note">
      <span className="hwho">{who}</span>
      <span className="hsay">{children}</span>
    </div>
  );
}

const STANDING_LABEL: Record<Standing["state"], string> = {
  held: "evidence holds",
  doubted: "doubted",
  unknown: "evidence unknown",
  trusted: "",
};

/** What a placement rests on, in the open card's head: who put it here and whether that still holds. */
export function StandingMark({ standing }: { standing: Standing }) {
  if (standing.state === "trusted") return null;
  const who = standing.actor === "owner" ? "you" : standing.actor === "machine" ? "the board" : standing.actor === "import" ? "0.1's import" : standing.actor;
  return (
    <span
      className={`standing ${standing.state}`}
      {...(standing.state === "doubted" ? { "data-meaning": "broken" as const } : {})}
      title={standing.words ?? `placed by ${who} on ${standing.evidence ?? "no"} evidence`}
    >
      {STANDING_LABEL[standing.state]}
      {standing.evidence ? ` · ${standing.evidence}` : ""}
    </span>
  );
}

/** The doors this card cannot open right now, each with its reason in text rather than a tooltip (plan 04, item 2). */
export function ClosedDoors({ doors }: { doors: readonly { label: string; why: string }[] }) {
  if (!doors.length) return null;
  return (
    <div className="closed-doors">
      {doors.map((d) => (
        <span key={d.label} className="closed-door">
          <b>{d.label}</b> — {d.why}
        </span>
      ))}
    </div>
  );
}

/** The question a lane stopped with, as the owner's move. */
export function Ask({ children }: { children: ReactNode }) {
  return (
    <div className="ask-block" data-meaning="yours">
      {children}
    </div>
  );
}

/** One sentence typed on the card resumes the lane with it — or, labelled Overturn, is the owner's word on a verdict. */
export function AnswerBox({ onSend, disabled, hint, label = "Answer" }: { onSend: (text: string) => void; disabled?: boolean; hint: string; label?: string }) {
  return (
    <form
      className="answer"
      onSubmit={(e) => {
        e.preventDefault();
        const field = e.currentTarget.elements.namedItem("answer") as HTMLInputElement | null;
        const text = field?.value.trim() ?? "";
        if (!text) return;
        onSend(text);
        if (field) field.value = "";
      }}
    >
      <input name="answer" type="text" aria-label={label} title={hint} disabled={disabled ?? false} autoComplete="off" />
      <button type="submit" className="btn" disabled={disabled ?? false}>
        {label}
      </button>
    </form>
  );
}

export function Said({ children, bad }: { children: ReactNode; bad?: boolean }) {
  return (
    <span className="said" {...(bad ? { "data-meaning": "broken" as const } : {})}>
      {children}
    </span>
  );
}

export function MoveTo<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: readonly T[];
  onChange: (value: T) => void;
}) {
  return (
    <span className="moveto">
      <span className="lbl">MOVE TO</span>
      <select value={value} onChange={(e) => onChange(e.target.value as T)} aria-label="Move to">
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </span>
  );
}

// ── the triage lens ───────────────────────────────────────────────────

/** Every card carrying an unread verdict, grouped by class (plan 05, item 2). */
export function TriageList({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="triage" aria-label={title} data-meaning="yours">
      <div className="triage-h">{title}</div>
      {children}
    </section>
  );
}

/**
 * One class of verdicts. A class whose evidence is the same for every card in
 * it gets one filled button; the doubted class never does, because each doubt
 * is its own fact (plan 27, item 5).
 */
export function TriageGroup({ name, count, landing, onAcceptAll, disabled, children }: { name: string; count: number; landing: ReactNode; onAcceptAll: (() => void) | null; disabled: boolean; children: ReactNode }) {
  return (
    <div className="triage-group">
      <div className="triage-gh">
        <span className="tg-name">{name}</span>
        <span className="tg-count">{count} card{count === 1 ? "" : "s"} · {landing}</span>
        {onAcceptAll ? (
          <button type="button" className="btn" onClick={onAcceptAll} disabled={disabled}>
            Accept all {count}
          </button>
        ) : (
          <span className="tg-each">read each</span>
        )}
      </div>
      <div role="list" aria-label={name}>
        {children}
      </div>
    </div>
  );
}

/**
 * One card, its evidence, and where the evidence sends it. The line says
 * where the card is now and where it lands, and only the landing takes a
 * colour — so the table can be read by its right-hand column alone.
 */
export function TriageRow({
  number,
  title,
  column,
  evidence,
  landing,
  onAccept,
  onOverturn,
  overturning,
  disabled,
  children,
}: {
  number: number;
  title: string;
  column: string;
  evidence: string;
  landing: ReactNode;
  onAccept: () => void;
  onOverturn: () => void;
  overturning: boolean;
  disabled: boolean;
  children?: ReactNode;
}) {
  return (
    <div className={`triage-row${overturning ? " overturning" : ""}`} role="listitem">
      <span className="cid">#{number}</span>
      <span className="tr-title">{title}</span>
      <span className="tr-evidence">{evidence}</span>
      <span className="tr-move">
        <span className="tr-from">{column} →</span> {landing}
      </span>
      <span className="tr-acts">
        <button type="button" className="btn ghost" onClick={onAccept} disabled={disabled}>
          Accept
        </button>
        <button type="button" className="btn ghost" onClick={onOverturn} disabled={disabled} aria-pressed={overturning}>
          Overturn
        </button>
      </span>
      {children ? <div className="tr-word">{children}</div> : null}
    </div>
  );
}

/** Where a verdict lands, in the meaning's colour: Done is proven, Decision
 * moment is your move, a card that stays or is parked makes no claim. */
export function Landing({ column }: { column: Column | null }) {
  const meaning: Meaning = column === "Done" ? "proven" : column === "Decision moment" ? "yours" : "quiet";
  return (
    <span className="tr-to" data-meaning={meaning}>
      {column ?? "stays"}
    </span>
  );
}

// ── page notes ────────────────────────────────────────────────────────

/** A page-level note. A loud one is broken by definition: something the board
 * expected is not there. A quiet one makes no claim and takes no colour. */
export function Notice({ children, quiet }: { children: ReactNode; quiet?: boolean }) {
  return (
    <div className={`notice${quiet ? " quiet" : ""}`} role={quiet ? "status" : "alert"} {...(quiet ? {} : { "data-meaning": "broken" as const })}>
      {children}
    </div>
  );
}

export function List({ items }: { items: string[] }) {
  return (
    <ul className="alist">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}
