import { useState, type KeyboardEvent, type MouseEvent, type PointerEventHandler } from "react";
import { useDraggable } from "@dnd-kit/core";
import { openDoor, openPlan } from "../api";
import type { CardSummary, FaceDoor } from "../types/board";
import { HANDS_ON } from "../types/lane";
import { Button, CardShell, CardTitle, CardTop, Carries, Chip, Cid, Essence, FailNote, Grow, Heard, HowFar, KbdHint, Kind, Pick, Pickable, Said, StandingMark, StateLine, StateSentence, type DragProps } from "../components/ui";
import type { MoveStatus } from "../state/board";
import { useLift } from "./LiftContext";
import { OpenCard } from "./OpenCard";
import { useProject } from "./ProjectContext";

export interface CardViewProps {
  card: CardSummary;
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
 * The one door a state allows, bottom-right of the state line (plan 27, item
 * 2). The board names it — which door, what it says, whether it is this
 * card's primary act — and the page only decides its shape: filled for the
 * primary, outlined otherwise, never a colour.
 */
function FaceDoorButton({ number, door, onOpen }: { number: number; door: FaceDoor; onOpen: (number: number | null) => void }) {
  const { slug } = useProject();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<{ text: string; bad: boolean } | null>(null);
  // `open` is the door for a state whose act lives on the open face: Answer a
  // lane, Decide a card, Read a signal. It opens the card rather than acting.
  if (door.name === "open") {
    return (
      <Button small ghost={!door.primary} onClick={() => onOpen(number)} title={door.why}>
        {door.label}
      </Button>
    );
  }
  const name = door.name;
  const through = async () => {
    setBusy(true);
    setSaid({ text: `${door.label}…`, bad: false });
    try {
      const result = name === "plan" ? await openPlan(slug, [number]) : await openDoor(slug, number, name);
      setSaid({ text: result.said, bad: false });
    } catch (e) {
      setSaid({ text: `${door.label} did not open: ${e instanceof Error ? e.message : String(e)}`, bad: true });
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button small ghost={!door.primary} onClick={() => void through()} disabled={busy} title={door.why}>
        {door.label}
      </Button>
      {said ? <Said bad={said.bad}>{said.text}</Said> : null}
    </>
  );
}

/**
 * Picking this suggestion to plan together with others. At rest a card shows
 * exactly one door, so the `+` waits for the hand to be on the card; once a
 * selection exists every suggestion card shows its checkbox.
 */
function Together({ card, selected, selecting, onSelect }: { card: CardSummary; selected: boolean; selecting: boolean; onSelect: (number: number, picked: boolean) => void }) {
  if (card.state.door?.name !== "plan") return null;
  if (selecting) return <Pick checked={selected} onChange={(picked) => onSelect(card.number, picked)} label={`Plan #${card.number} together`} />;
  return (
    <Pickable>
      <Button small ghost onClick={() => onSelect(card.number, true)} title="Plan this together with other suggestions: pick it, then pick the others" label={`Plan #${card.number} together with others`}>
        +
      </Button>
    </Pickable>
  );
}

export function CardBody({ card, open, onOpen, onClose, selected = false, selecting = false, onSelect }: { card: CardSummary; open: boolean; onOpen?: ((number: number | null) => void) | undefined; onClose?: (() => void) | undefined; selected?: boolean; selecting?: boolean; onSelect?: ((number: number, picked: boolean) => void) | undefined }) {
  const { heard } = useProject();
  const state = card.state;
  return (
    <>
      <CardTop>
        <Cid n={card.number} />
        {card.gate ? <Chip kind="gate" title={`The effort gate on this card's plan: ${card.gate}`}>{card.gate}</Chip> : null}
        {card.is_new ? <Chip title="Arrived today">new</Chip> : null}
        {card.tags.map((t) => (
          <Chip key={t} kind="tag">
            {t}
          </Chip>
        ))}
        <Grow />
        {open ? <Chip title="Where this card sits">{card.place.column}</Chip> : null}
        {open ? <StandingMark standing={card.standing} /> : null}
        <Kind state={card.document_state} kind={card.kind} fix={card.fix} path={card.document_path} />
        {open && onClose ? (
          <Chip onClick={onClose} title="Close">
            ✕
          </Chip>
        ) : null}
      </CardTop>
      <CardTitle>{card.title}</CardTitle>
      {open ? (
        <StateSentence state={state} />
      ) : (
        <>
          {state.detail ? <Essence said>{state.detail}</Essence> : card.essence ? <Essence>{card.essence}</Essence> : null}
          <Carries cards={card.folded} open={false} />
          {card.place.column === "Executing" && card.progress ? <HowFar progress={card.progress} /> : null}
          {HANDS_ON.includes(card.lane_state) && heard ? <Heard who={heard.card_number === null ? "the board" : `#${heard.card_number}`}>{heard.text}</Heard> : null}
          <StateLine state={state}>
            {onSelect ? <Together card={card} selected={selected} selecting={selecting} onSelect={onSelect} /> : null}
            {state.door && onOpen ? <FaceDoorButton number={card.number} door={state.door} onOpen={onOpen} /> : null}
          </StateLine>
        </>
      )}
    </>
  );
}

export function CardView({ card, ghost, open, status, draggable, focused, selected, selecting, onOpen, onRetry, onFocus, onMoveTo, onSelect }: CardViewProps) {
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
      meaning={card.state.meaning}
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
      <CardBody card={card} open={open} onOpen={onOpen} onClose={() => onOpen(null)} selected={selected} selecting={selecting} onSelect={onSelect} />
      {open ? <OpenCard card={card} onMoveTo={onMoveTo} /> : null}
      {status.kind === "failed" ? <FailNote reason={status.reason} onRetry={() => onRetry(card.number)} /> : null}
      {focused && !open && draggable ? <KbdHint lifted={lifting} /> : null}
    </CardShell>
  );
}
