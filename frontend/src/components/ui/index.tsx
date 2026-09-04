import "./tokens.css";
import "./primitives.css";
import type { FocusEventHandler, KeyboardEvent, MouseEvent, PointerEventHandler, ReactNode, Ref } from "react";
import type { DraggableAttributes } from "@dnd-kit/core";
import { marked } from "marked";
import DOMPurify from "dompurify";
import type { FoldedCard } from "../../types/board";
import type { DocumentState } from "../../types/document";
import type { Standing } from "../../types/evidence";
import type { LaneState, Readiness, StartState } from "../../types/lane";
import type { RowKind } from "../../types/row";
import { ASK_ROWS, LANDED_ROWS, LEAD_ROWS } from "../../types/row";

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
 * The head and the attention line, pinned above the columns (plan 06, item
 * 4). `folded` is the laptop's one-line head once a column has scrolled: the
 * wordmark, the project and the attention counts stay, the rest steps aside
 * so the columns keep their height.
 */
export function HeadFrame({ children, folded }: { children: ReactNode; folded: boolean }) {
  return (
    <div className={`head${folded ? " folded" : ""}`} data-folded={folded ? "true" : "false"}>
      {children}
    </div>
  );
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
export function ProjectSwitcher({ projects, current, onSwitch }: { projects: readonly { slug: string; name: string }[]; current: string; onSwitch: (slug: string) => void }) {
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
    </label>
  );
}

export function CorpusLine({ children }: { children: ReactNode }) {
  return <span className="corpus">{children}</span>;
}

export function Strong({ children }: { children: ReactNode }) {
  return <b>{children}</b>;
}

export function Off({ children }: { children: ReactNode }) {
  return <span className="off">{children}</span>;
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

// ── the attention line ────────────────────────────────────────────────

export function AttentionLine({ children, quiet }: { children: ReactNode; quiet: string }) {
  return (
    <div className="attn-line">
      {children}
      <span className="quiet">{quiet}</span>
    </div>
  );
}

export function Att({ n, label, tone = "plain", onClick, on }: { n: number; label: string; tone?: "plain" | "you" | "bad"; onClick?: (() => void) | undefined; on?: boolean }) {
  const className = `att ${tone === "plain" ? "" : tone}${on ? " on" : ""}`;
  // The label is its own span so the folded head can keep the count and drop the words.
  const body = (
    <>
      <b>{n}</b> <span className="alabel">{label}</span>
    </>
  );
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick} aria-pressed={on ?? false} title={label}>
        {body}
      </button>
    );
  }
  return (
    <span className={className} title={label}>
      {body}
    </span>
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
    <section className="asks" aria-label={title}>
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
    <section className="talks" aria-label={title}>
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

/** A column scrolls on its own (plan 06, item 4); `onScroll` says whether it is scrolled away from its top. */
export function ColumnBox({
  children,
  wide,
  yours,
  column,
  onScroll,
}: {
  children: ReactNode;
  wide: boolean;
  yours: boolean;
  column: string;
  onScroll?: ((scrolled: boolean) => void) | undefined;
}) {
  return (
    <section className={`col${wide ? " wide" : ""}${yours ? " yours" : ""}`} data-column={column} onScroll={onScroll ? (e) => onScroll(e.currentTarget.scrollTop > 0) : undefined}>
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
export function CardShell({ number, children, open, saving, failed, ghost, lift, isStatic, nodeRef, onClick, onKeyDown, dragProps, label }: CardShellProps) {
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

export function Rank({ n }: { n: number }) {
  return <span className="rank">{n}</span>;
}

export function Cid({ n }: { n: number }) {
  return <span className="cid">#{n}</span>;
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h3 className="card-title">{children}</h3>;
}

export function Essence({ children }: { children: ReactNode }) {
  return <p className="essence">{children}</p>;
}

export function CardFoot({ children }: { children: ReactNode }) {
  return <div className="card-foot">{children}</div>;
}

export function Points({ n }: { n: number }) {
  return (
    <span className="points">
      {n} point{n === 1 ? "" : "s"}
    </span>
  );
}

const START_LABEL: Record<StartState, string> = {
  free: "free",
  collides: "collides",
  "no gate": "no gate",
  "nowhere to run": "nowhere to run",
  "lane exists": "lane exists",
  elsewhere: "",
  unread: "not read yet",
};

/** The pill: whether the card can start now, from the Start door's own verdict (plan 06, item 3). */
export function Pill({ readiness }: { readiness: Readiness }) {
  const label = readiness.state === "collides" ? `collides with ${readiness.cards.map((n) => `#${n}`).join(", ")}` : START_LABEL[readiness.state];
  if (!label) return null;
  const title = readiness.state === "collides" && readiness.files.length ? `${readiness.why} On: ${readiness.files.join(", ")}` : readiness.why;
  return (
    <span className={`pill ${readiness.state.replace(/ /g, "-")}`} title={title} data-start={readiness.state}>
      {label}
    </span>
  );
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
  kind?: "plain" | "gate" | "tag" | "new";
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
  plan: "Plan",
  suggestion: "Suggestion",
  archived: "Archived",
  note: "Note — nothing written yet",
  gone: "Document gone",
};

/** What is written behind a card: five states, and a card always shows one. */
export function DocState({ state, path }: { state: DocumentState; path: string | null }) {
  return (
    <span className={`doc ${state}`} title={path ?? undefined}>
      {DOC_LABEL[state]}
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
    <div className="drop-gap" role="status" aria-live="polite">
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

export function RowLine({ kind, text }: { kind: RowKind; text: string }) {
  const classes = ["row"];
  if (LEAD_ROWS.includes(kind)) classes.push("lead");
  if (LANDED_ROWS.includes(kind)) classes.push("land");
  if (ASK_ROWS.includes(kind)) classes.push("ask");
  return (
    <div className={classes.join(" ")}>
      <span className="lbl">{kind}</span>
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

const LANE_LABEL: Record<LaneState, string> = {
  none: "",
  working: "Working",
  asking: "Asking you",
  stopped: "Stopped",
  blocked: "Blocked",
  moving: "Moving",
  ended: "Lane ended",
};

/** The thin band on a card: its lane reporting in, in one sentence. */
export function Band({ state, children }: { state: LaneState; children: ReactNode }) {
  return (
    <div className={`band ${state}`} role="status">
      <span className="bstate">{LANE_LABEL[state]}</span>
      <span className="bsay">{children}</span>
    </div>
  );
}

/** The board doubts a machine-placed status: its evidence is gone, and the missing fact is said (plan 04, item 1). */
export function Doubt({ children }: { children: ReactNode }) {
  return (
    <div className="doubt" role="status">
      <span className="bstate">Doubted</span>
      <span className="bsay">{children}</span>
    </div>
  );
}

/** Two live lanes are editing the same file: named on both cards, before the fold (plan 07, item 2). */
export function Clash({ children }: { children: ReactNode }) {
  return (
    <div className="clash" role="status">
      <span className="bstate">Colliding</span>
      <span className="bsay">{children}</span>
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
    <span className={`standing ${standing.state}`} title={standing.words ?? `placed by ${who} on ${standing.evidence ?? "no"} evidence`}>
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
  return <div className="ask-block">{children}</div>;
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
  return <span className={`said${bad ? " bad" : ""}`}>{children}</span>;
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
    <section className="triage" aria-label={title}>
      <div className="triage-h">{title}</div>
      {children}
    </section>
  );
}

export function TriageGroup({ name, count, onAcceptAll, disabled, children }: { name: string; count: number; onAcceptAll: () => void; disabled: boolean; children: ReactNode }) {
  return (
    <div className="triage-group">
      <div className="triage-gh">
        <span className="tg-name">{name}</span>
        <span className="tg-count">{count}</span>
        <button type="button" className="btn" onClick={onAcceptAll} disabled={disabled}>
          Accept all in this class
        </button>
      </div>
      <div role="list" aria-label={name}>
        {children}
      </div>
    </div>
  );
}

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
  landing: string;
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
      <span className="tr-col">{column}</span>
      <span className="tr-evidence">{evidence}</span>
      <span className="tr-to">{landing}</span>
      <span className="tr-acts">
        <button type="button" className="btn" onClick={onAccept} disabled={disabled}>
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

// ── page notes ────────────────────────────────────────────────────────

export function Notice({ children, quiet }: { children: ReactNode; quiet?: boolean }) {
  return (
    <div className={`notice${quiet ? " quiet" : ""}`} role={quiet ? "status" : "alert"}>
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
