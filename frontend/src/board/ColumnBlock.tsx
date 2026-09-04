import { useState } from "react";
import type { ColumnView } from "../types/board";
import { ColumnBox, ColumnHead, ColumnNote, ColumnTop, Definition, MoreRow, RailGroup, Stack, Tool } from "../components/ui";
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
  selected: ReadonlySet<number>;
  onUnfurl: () => void;
  onFurl: () => void;
  onOpen: (number: number | null) => void;
  onRetry: (number: number) => void;
  onFocus: (number: number | null) => void;
  onMoveTo: (number: number, column: string) => Promise<boolean>;
  onSelect: (number: number, picked: boolean) => void;
}

export function ColumnBlock({ column, index, total, lens, lift, open, focused, statuses, unfurled, selected, onUnfurl, onFurl, onOpen, onRetry, onFocus, onMoveTo, onSelect }: ColumnBlockProps) {
  const name = column.definition.column;
  const wide = open !== null && column.groups.some((g) => g.cards.some((c) => c.number === open));
  const draggable = lens === "rank";
  // The defects rail starts furled to its one line; the owner opens it for the second scan.
  const [railOpen, setRailOpen] = useState(false);
  let budget = unfurled ? Number.POSITIVE_INFINITY : FOLD_AT;
  // The rank digit is gone from the card — position is rank — but the drop
  // preview still names the rank a card would land on.
  let rank = 1;
  let furledInRail = 0;
  const blocks = column.groups.map((group) => {
    const seen = throughLens(group.cards, lens);
    if (group.rail && !railOpen) {
      furledInRail += seen.length;
      return { group, slots: [] };
    }
    const visible = seen.slice(0, Math.max(0, budget));
    budget -= visible.length;
    const { slots, rankNext } = groupSlots(column, group, visible, draggable ? lift : null, rank);
    rank = rankNext;
    return { group, slots };
  });
  const shown = blocks.reduce((n, b) => n + b.slots.filter((s) => s.kind === "card").length, 0);
  const hidden = Math.max(0, column.count - furledInRail - shown);

  return (
    <ColumnBox wide={wide} column={name}>
      <ColumnTop>
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
      </ColumnTop>
      <Stack>
        {blocks.map(({ group, slots }) => {
          const block = (
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
              selected={selected}
              onOpen={onOpen}
              onRetry={onRetry}
              onFocus={onFocus}
              onMoveTo={onMoveTo}
              onSelect={onSelect}
            />
          );
          return group.rail ? (
            <RailGroup key="rail" count={group.cards.length} open={railOpen} onToggle={() => setRailOpen((v) => !v)}>
              {block}
            </RailGroup>
          ) : (
            block
          );
        })}
        {hidden > 0 ? <MoreRow onClick={onUnfurl}>+ {hidden} more in {name}</MoreRow> : null}
      </Stack>
    </ColumnBox>
  );
}
