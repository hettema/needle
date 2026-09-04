import type { ColumnView } from "../types/board";
import { ColumnBox, ColumnHead, ColumnNote, Definition, MoreRow, Stack, Tool } from "../components/ui";
import type { MoveStatus } from "../state/board";
import { GroupBlock } from "./GroupBlock";
import { groupSlots, throughLens, type LensKind, type Lift } from "./dnd";

export const FOLD_AT = 8;

export interface ColumnBlockProps {
  column: ColumnView;
  index: number;
  total: number;
  lens: LensKind;
  lift: Lift | null;
  open: number | null;
  focused: number | null;
  statuses: Record<number, MoveStatus>;
  unfurled: boolean;
  onUnfurl: () => void;
  onFurl: () => void;
  onOpen: (number: number | null) => void;
  onRetry: (number: number) => void;
  onFocus: (number: number | null) => void;
  onMoveTo: (number: number, column: string) => Promise<boolean>;
}

export function ColumnBlock({ column, index, total, lens, lift, open, focused, statuses, unfurled, onUnfurl, onFurl, onOpen, onRetry, onFocus, onMoveTo }: ColumnBlockProps) {
  const name = column.definition.column;
  const wide = open !== null && column.groups.some((g) => g.cards.some((c) => c.number === open));
  const draggable = lens === "rank";
  let budget = unfurled ? Number.POSITIVE_INFINITY : FOLD_AT;
  let rank = 1;
  const blocks = column.groups.map((group) => {
    const seen = throughLens(group.cards, lens);
    const visible = seen.slice(0, Math.max(0, budget));
    budget -= visible.length;
    const { slots, rankNext } = groupSlots(column, group, visible, draggable ? lift : null, rank);
    rank = rankNext;
    return { group, slots };
  });
  const hidden = Math.max(0, column.count - Math.min(column.count, unfurled ? column.count : FOLD_AT));

  return (
    <ColumnBox wide={wide} yours={column.definition.yours} column={name}>
      <ColumnHead
        name={name}
        count={column.count}
        tools={
          <>
            {column.definition.ranked ? (
              <Tool on={draggable} onClick={() => undefined} label={draggable ? "Position is rank" : "Sorted by a lens; the rank is not what you see"}>
                {draggable ? "rank" : lens}
              </Tool>
            ) : null}
            <Tool onClick={onFurl} label={`Furl ${name}`}>
              furl
            </Tool>
          </>
        }
        definition={<Definition name={name} paragraphs={column.definition.definition} movedBy={column.definition.moved_by} toLeft={index >= total - 2} />}
      />
      <ColumnNote>{column.definition.note}</ColumnNote>
      <Stack>
        {blocks.map(({ group, slots }) => (
          <GroupBlock
            key={group.name ?? ""}
            column={column}
            group={group}
            slots={slots}
            lift={lift}
            open={open}
            focused={focused}
            statuses={statuses}
            draggable={draggable}
            onOpen={onOpen}
            onRetry={onRetry}
            onFocus={onFocus}
            onMoveTo={onMoveTo}
          />
        ))}
        {hidden > 0 ? <MoreRow onClick={onUnfurl}>+ {hidden} more in {name}</MoreRow> : null}
      </Stack>
    </ColumnBox>
  );
}
