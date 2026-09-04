import type { KeyboardEvent, MouseEvent, PointerEventHandler } from "react";
import { useDraggable } from "@dnd-kit/core";
import type { CardSummary } from "../types/board";
import { Band, CardFoot, CardShell, CardTitle, CardTop, Chip, Cid, DocState, Essence, FailNote, Grow, KbdHint, Points, Rank, type DragProps } from "../components/ui";
import type { MoveStatus } from "../state/board";
import { useLift } from "./LiftContext";
import { OpenCard } from "./OpenCard";

const GATE_LABEL: Record<string, string> = { low: "Low", medium: "Medium", high: "High", xhigh: "Xhigh" };

export interface CardViewProps {
  card: CardSummary;
  rank: number | null;
  ghost: boolean;
  open: boolean;
  status: MoveStatus;
  draggable: boolean;
  focused: boolean;
  onOpen: (number: number | null) => void;
  onRetry: (number: number) => void;
  onFocus: (number: number | null) => void;
  onMoveTo: (number: number, column: string) => Promise<boolean>;
}

export function CardBody({ card, rank, open, onClose }: { card: CardSummary; rank: number | null; open: boolean; onClose?: (() => void) | undefined }) {
  return (
    <>
      <CardTop>
        {rank !== null ? <Rank n={rank} /> : null}
        <Cid n={card.number} />
        {card.is_new ? <Chip kind="new">New</Chip> : null}
        {open ? <DocState state={card.document_state} path={card.document_path} /> : null}
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
          <CardFoot>
            <DocState state={card.document_state} path={card.document_path} />
            <Grow />
            <Points n={card.points} />
          </CardFoot>
          {card.lane_state !== "none" && card.lane_sentence ? <Band state={card.lane_state}>{card.lane_sentence}</Band> : null}
        </>
      ) : null}
    </>
  );
}

export function CardView({ card, rank, ghost, open, status, draggable, focused, onOpen, onRetry, onFocus, onMoveTo }: CardViewProps) {
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
    if (target.closest("button, select, a")) return;
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
      <CardBody card={card} rank={rank} open={open} onClose={() => onOpen(null)} />
      {open ? <OpenCard card={card} onMoveTo={onMoveTo} /> : null}
      {status.kind === "failed" ? <FailNote reason={status.reason} onRetry={() => onRetry(card.number)} /> : null}
      {focused && !open && draggable ? <KbdHint lifted={lifting} /> : null}
    </CardShell>
  );
}
