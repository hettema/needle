import { useState, type KeyboardEvent, type MouseEvent, type PointerEventHandler } from "react";
import { useDraggable } from "@dnd-kit/core";
import { openDoor, openPlan } from "../api";
import type { CardSummary } from "../types/board";
import { HANDS_ON } from "../types/lane";
import { Band, Button, CardFoot, CardShell, CardTitle, CardTop, Carries, Chip, Cid, Clash, DocState, Doubt, Essence, FailNote, Grow, Heard, KbdHint, Pick, Pill, Points, Rank, Said, StandingMark, type DragProps } from "../components/ui";
import type { MoveStatus } from "../state/board";
import { useLift } from "./LiftContext";
import { OpenCard } from "./OpenCard";
import { useProject } from "./ProjectContext";

const GATE_LABEL: Record<string, string> = { low: "Low", medium: "Medium", high: "High", xhigh: "Xhigh" };

export interface CardViewProps {
  card: CardSummary;
  rank: number | null;
  ghost: boolean;
  open: boolean;
  status: MoveStatus;
  draggable: boolean;
  focused: boolean;
  selected: boolean;
  selecting: boolean;
  onOpen: (number: number | null) => void;
  onRetry: (number: number) => void;
  onFocus: (number: number | null) => void;
  onMoveTo: (number: number, column: string) => Promise<boolean>;
  onSelect: (number: number, picked: boolean) => void;
}

/**
 * The collapsed face's doors (plan 06, items 3 and 5): Start where the pill
 * says free, Plan on every suggestion card, and the pick for planning several
 * together. Each opens through the same door the open card uses and says
 * what it did, or why not, under the card's foot.
 */
function FootDoors({ card, selected, selecting, onSelect }: { card: CardSummary; selected: boolean; selecting: boolean; onSelect: (number: number, picked: boolean) => void }) {
  const { slug } = useProject();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<{ text: string; bad: boolean } | null>(null);
  const through = async (what: string, work: () => Promise<{ said: string }>) => {
    setBusy(true);
    setSaid({ text: `${what}…`, bad: false });
    try {
      setSaid({ text: (await work()).said, bad: false });
    } catch (e) {
      setSaid({ text: `${what} did not open: ${e instanceof Error ? e.message : String(e)}`, bad: true });
    } finally {
      setBusy(false);
    }
  };
  const start = card.start;
  const plan = card.plan;
  return (
    <>
      {start?.offered ? (
        <Button small onClick={() => void through("Start", () => openDoor(slug, card.number, "start"))} disabled={busy} title={start.why}>
          {start.label}
        </Button>
      ) : null}
      {plan?.offered ? (
        <Button small ghost onClick={() => void through("Plan", () => openPlan(slug, [card.number]))} disabled={busy} title={plan.why}>
          Plan
        </Button>
      ) : null}
      {plan?.offered && !selecting ? (
        <Button small ghost onClick={() => onSelect(card.number, true)} title="Plan this together with other suggestions: pick it, then pick the others" label={`Plan #${card.number} together with others`}>
          +
        </Button>
      ) : null}
      {plan?.offered && selecting ? <Pick checked={selected} onChange={(picked) => onSelect(card.number, picked)} label={`Plan #${card.number} together`} /> : null}
      {said ? <Said bad={said.bad}>{said.text}</Said> : null}
    </>
  );
}

export function CardBody({ card, rank, open, onClose, selected = false, selecting = false, onSelect }: { card: CardSummary; rank: number | null; open: boolean; onClose?: (() => void) | undefined; selected?: boolean; selecting?: boolean; onSelect?: ((number: number, picked: boolean) => void) | undefined }) {
  const { heard } = useProject();
  return (
    <>
      <CardTop>
        {rank !== null ? <Rank n={rank} /> : null}
        <Cid n={card.number} />
        {card.is_new ? <Chip kind="new">New</Chip> : null}
        {open ? <DocState state={card.document_state} path={card.document_path} /> : null}
        {open ? <StandingMark standing={card.standing} /> : null}
        <Grow />
        {card.tags.map((t) => (
          <Chip key={t} kind="tag">
            {t}
          </Chip>
        ))}
        {card.gate ? <Chip kind="gate">{open ? `Gate · ${GATE_LABEL[card.gate] ?? card.gate}` : (GATE_LABEL[card.gate] ?? card.gate)}</Chip> : null}
        {open && onClose ? (
          <Chip onClick={onClose} title="Close">
            ▼ close
          </Chip>
        ) : null}
      </CardTop>
      <CardTitle>{card.title}</CardTitle>
      {!open ? (
        <>
          {card.essence ? <Essence>{card.essence}</Essence> : null}
          <Carries cards={card.folded} open={false} />
          <CardFoot>
            <DocState state={card.document_state} path={card.document_path} />
            {card.readiness ? <Pill readiness={card.readiness} /> : null}
            <Grow />
            <Points n={card.points} />
            {onSelect ? <FootDoors card={card} selected={selected} selecting={selecting} onSelect={onSelect} /> : null}
          </CardFoot>
          {card.lane_state !== "none" && card.lane_sentence ? <Band state={card.lane_state}>{card.lane_sentence}</Band> : null}
          {HANDS_ON.includes(card.lane_state) && heard ? <Heard who={heard.card_number === null ? "the board" : `#${heard.card_number}`}>{heard.text}</Heard> : null}
          {card.colliding ? <Clash>{card.colliding.sentence}</Clash> : null}
          {card.standing.state === "doubted" && card.standing.words ? <Doubt>{card.standing.words}</Doubt> : null}
        </>
      ) : null}
    </>
  );
}

export function CardView({ card, rank, ghost, open, status, draggable, focused, selected, selecting, onOpen, onRetry, onFocus, onMoveTo, onSelect }: CardViewProps) {
  const controller = useLift();
  const lifting = controller.lift !== null && controller.lift.number === card.number;
  const { attributes, listeners, setNodeRef } = useDraggable({
    id: `card:${card.number}`,
    data: { number: card.number, place: card.place },
    disabled: !draggable || open,
  });

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.target !== e.currentTarget) return;
    if (e.key === " ") {
      e.preventDefault();
      if (lifting) controller.drop();
      else if (controller.lift === null && draggable && !open) controller.start(card.number, card.place, "keyboard");
      return;
    }
    if (e.key === "Escape") {
      if (lifting) controller.cancel();
      else if (open) onOpen(null);
      return;
    }
    if (e.key === "Enter" && !lifting) {
      e.preventDefault();
      onOpen(open ? null : card.number);
      return;
    }
    if (lifting && (e.key === "ArrowUp" || e.key === "ArrowDown" || e.key === "ArrowLeft" || e.key === "ArrowRight")) {
      e.preventDefault();
      controller.step(e.key);
    }
  };

  const onClick = (e: MouseEvent<HTMLElement>) => {
    if (open || controller.lift !== null) return;
    const target = e.target as HTMLElement;
    if (target.closest("button, select, a, input, label")) return;
    onOpen(card.number);
  };

  const { role: _role, ...rest } = attributes;
  const pointer = listeners as { onPointerDown?: PointerEventHandler<HTMLElement> } | undefined;
  const dragProps: DragProps = { ...rest, onPointerDown: pointer?.onPointerDown, onFocus: () => onFocus(card.number), onBlur: () => onFocus(null) };

  return (
    <CardShell
      number={card.number}
      label={`#${card.number} ${card.title}`}
      open={open}
      ghost={ghost}
      saving={status.kind === "saving"}
      failed={status.kind === "failed"}
      isStatic={!draggable || open}
      nodeRef={setNodeRef}
      onClick={onClick}
      onKeyDown={onKeyDown}
      dragProps={dragProps}
    >
      <CardBody card={card} rank={rank} open={open} onClose={() => onOpen(null)} selected={selected} selecting={selecting} onSelect={onSelect} />
      {open ? <OpenCard card={card} onMoveTo={onMoveTo} /> : null}
      {status.kind === "failed" ? <FailNote reason={status.reason} onRetry={() => onRetry(card.number)} /> : null}
      {focused && !open && draggable ? <KbdHint lifted={lifting} /> : null}
    </CardShell>
  );
}
