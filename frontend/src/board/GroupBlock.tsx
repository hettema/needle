import { useDroppable } from "@dnd-kit/core";
import type { ColumnView, GroupView } from "../types/board";
import { DropGap, GroupBody, GroupHead } from "../components/ui";
import type { MoveStatus } from "../state/board";
import { CardView } from "./CardView";
import { groupId, type Lift, type Slot } from "./dnd";

export interface GroupBlockProps {
  column: ColumnView;
  group: GroupView;
  slots: Slot[];
  lift: Lift | null;
  open: number | null;
  focused: number | null;
  statuses: Record<number, MoveStatus>;
  draggable: boolean;
  onOpen: (number: number | null) => void;
  onRetry: (number: number) => void;
  onFocus: (number: number | null) => void;
  onMoveTo: (number: number, column: string) => Promise<boolean>;
}

const IDLE: MoveStatus = { kind: "idle" };

export function GroupBlock({ column, group, slots, open, focused, statuses, draggable, onOpen, onRetry, onFocus, onMoveTo }: GroupBlockProps) {
  const id = groupId(column.definition.column, group.name);
  const { setNodeRef } = useDroppable({ id, data: { column: column.definition.column, group: group.name } });
  return (
    <>
      {group.name !== null ? <GroupHead name={group.name} /> : null}
      <GroupBody nodeRef={setNodeRef} id={id} label={`${column.definition.column}${group.name ? ` · ${group.name}` : ""}`}>
        {slots.map((slot) =>
          slot.kind === "gap" ? (
            <DropGap key="gap" label={slot.label} />
          ) : (
            <CardView
              key={slot.card.number}
                card={slot.card}
              rank={slot.rank}
              ghost={slot.ghost}
              open={open === slot.card.number}
              status={statuses[slot.card.number] ?? IDLE}
              draggable={draggable}
              focused={focused === slot.card.number}
              onOpen={onOpen}
              onRetry={onRetry}
              onFocus={onFocus}
              onMoveTo={onMoveTo}
            />
          ),
        )}
      </GroupBody>
    </>
  );
}
