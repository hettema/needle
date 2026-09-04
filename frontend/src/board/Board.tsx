import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DndContext, DragOverlay, PointerSensor, pointerWithin, rectIntersection, useSensor, useSensors, type CollisionDetection, type DragEndEvent, type DragMoveEvent, type DragStartEvent } from "@dnd-kit/core";
import type { BoardState, CardSummary } from "../types/board";
import type { Place } from "../types/card";
import type { Column } from "../types/column";
import type { Project } from "../types/project";
import { openDoor, openIdea } from "../api";
import { AppHead, AskList, AskRow, Att, AttentionLine, BoardStrip, CardShell, CorpusLine, HeadTools, IdeaDoor, Lens, List, Notice, Off, ProjectSwitcher, Rail, Strong, TalkList, TalkRow, Wordmark } from "../components/ui";
import type { BoardStore } from "../state/board";
import { CardBody } from "./CardView";
import { ColumnBlock, FOLD_AT } from "./ColumnBlock";
import { LiftContext, type LiftController } from "./LiftContext";
import { ProjectContext } from "./ProjectContext";
import { Triage } from "./Triage";
import { samePlace, stepTarget, targetInGroup, type LensKind, type Lift, type StepKey } from "./dnd";
import { ago } from "./time";

export const WIDE_SCREEN = "(min-width: 2300px)";

const LENSES: readonly { value: LensKind; label: string }[] = [
  { value: "rank", label: "Rank" },
  { value: "age", label: "Age" },
  { value: "gate", label: "Gate" },
  { value: "triage", label: "Triage" },
];

function cardFromHash(): number | null {
  const match = /^#card-(\d+)$/.exec(window.location.hash);
  return match?.[1] ? Number(match[1]) : null;
}

function findCard(board: BoardState, number: number): CardSummary | null {
  for (const column of board.columns) for (const group of column.groups) for (const card of group.cards) if (card.number === number) return card;
  return null;
}

function cardBoxes(groupEl: Element): { number: number; top: number; height: number }[] {
  return Array.from(groupEl.querySelectorAll<HTMLElement>("[data-card]")).map((el) => {
    const rect = el.getBoundingClientRect();
    return { number: Number(el.dataset["card"]), top: rect.top, height: rect.height };
  });
}

const collision: CollisionDetection = (args) => {
  const within = pointerWithin(args);
  return within.length ? within : rectIntersection(args);
};

export function Board({ slug, store, projects, onSwitch }: { slug: string; store: BoardStore; projects: Project[]; onSwitch: (slug: string) => void }) {
  const { board } = store;
  const [lens, setLens] = useState<LensKind>("rank");
  const [open, setOpenState] = useState<number | null>(() => cardFromHash());
  const [focused, setFocused] = useState<number | null>(null);
  const [lift, setLift] = useState<Lift | null>(null);
  const [furled, setFurled] = useState<Set<Column>>(() => {
    const wide = typeof window.matchMedia === "function" && window.matchMedia(WIDE_SCREEN).matches;
    return new Set<Column>(wide ? [] : ["Executed", "Done", "Not now"]);
  });
  const [unfurledMore, setUnfurledMore] = useState<Set<Column>>(new Set());
  const [asksOpen, setAsksOpen] = useState(false);
  const [reading, setReading] = useState<number | null>(null);
  const [readSaid, setReadSaid] = useState<string | null>(null);
  const [talksOpen, setTalksOpen] = useState(false);
  const [ideaOpening, setIdeaOpening] = useState(false);
  const [ideaSaid, setIdeaSaid] = useState<string | null>(null);
  const pointerY = useRef(0);
  const liftRef = useRef<Lift | null>(null);
  liftRef.current = lift;
  // The window's tab is the project's name: two boards tabbed together on
  // one workspace both read "Needle" otherwise (owner, 2026-09-04).
  const projectName = board?.project.name ?? null;
  useEffect(() => {
    if (projectName === null) return;
    document.title = `${projectName} · Needle`;
    return () => {
      document.title = "Needle";
    };
  }, [projectName]);

  const setOpen = useCallback((number: number | null) => {
    setOpenState(number);
    const hash = number === null ? "" : `#card-${number}`;
    if (window.location.hash !== hash) history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
  }, []);

  useEffect(() => {
    const onHash = () => setOpenState(cardFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // A card opened by its link may sit in a furled column; the column unfurls so the card is on screen.
  useEffect(() => {
    if (open === null || !board) return;
    const card = findCard(board, open);
    if (!card || !furled.has(card.place.column)) return;
    setFurled((f) => {
      const next = new Set(f);
      next.delete(card.place.column);
      return next;
    });
  }, [open, board, furled]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointerY.current = e.clientY;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  const openColumns = useMemo<Column[]>(() => (board ? board.columns.map((c) => c.definition.column).filter((c) => !furled.has(c)) : []), [board, furled]);

  const unfurlMore = useCallback((column: Column) => setUnfurledMore((s) => new Set(s).add(column)), []);

  const controller = useMemo<LiftController>(() => {
    const retarget = (target: Place) => {
      const current = liftRef.current;
      if (!current) return;
      if (samePlace(current.target, target)) return;
      if (board) {
        const column = board.columns.find((c) => c.definition.column === target.column);
        if (column && column.count > FOLD_AT) unfurlMore(target.column);
      }
      setLift({ ...current, target });
    };
    return {
      lift,
      start: (number, from, by) => setLift({ number, from, target: from, by }),
      retarget,
      step: (key: StepKey) => {
        const current = liftRef.current;
        if (!current || !board) return;
        retarget(stepTarget(board, current, key, openColumns));
      },
      drop: () => {
        const current = liftRef.current;
        setLift(null);
        if (!current) return;
        if (!samePlace(current.target, current.from)) void store.move(current.number, current.target);
      },
      cancel: () => setLift(null),
    };
  }, [lift, board, openColumns, store, unfurlMore]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const onDragStart = (e: DragStartEvent) => {
    const data = e.active.data.current as { number: number; place: Place } | undefined;
    if (!data) return;
    controller.start(data.number, data.place, "pointer");
  };

  // On every move, not only when the droppable changes: within one group the
  // droppable never changes, and the target is where the pointer is now.
  const onDragMove = (e: DragMoveEvent) => {
    const current = liftRef.current;
    if (!current || !e.over) return;
    const data = e.over.data.current as { column: Column; group: string | null } | undefined;
    if (!data) return;
    const groupEl = document.querySelector<HTMLElement>(`[data-group="${CSS.escape(String(e.over.id))}"]`);
    if (!groupEl) return;
    controller.retarget(targetInGroup(data.column, data.group, cardBoxes(groupEl), pointerY.current, current));
  };

  const onDragEnd = (e: DragEndEvent) => {
    if (e.over === null) {
      controller.cancel();
      return;
    }
    controller.drop();
  };

  const moveTo = useCallback(
    async (number: number, column: string): Promise<boolean> => store.move(number, { column: column as Column, group: null, position: 1_000_000 }),
    [store],
  );

  // One click each way per card: the owner's reading is a reading, recorded
  // and acted on by the same door the card offers; the board is re-read after.
  const readSignal = useCallback(
    async (number: number, delivered: boolean) => {
      setReading(number);
      try {
        const result = await openDoor(slug, number, "signal", { delivered });
        setReadSaid(`#${number}: ${result.said}`);
      } catch (e) {
        setReadSaid(`#${number}: the reading did not land — ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setReading(null);
        await store.refresh();
      }
    },
    [slug, store],
  );

  // The Idea door opens through the runtime like every door and answers with
  // its evidence, or fails by name; the board's stream then lists the conversation.
  const openAnIdea = useCallback(
    async (text: string) => {
      setIdeaOpening(true);
      setIdeaSaid("Opening…");
      try {
        const result = await openIdea(slug, text);
        setIdeaSaid(result.said);
      } catch (e) {
        setIdeaSaid(`Idea did not open: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setIdeaOpening(false);
      }
    },
    [slug],
  );

  if (!board) {
    return (
      <>
        <AppHead>
          <Wordmark />
        </AppHead>
        {store.error ? <Notice>The board could not be read: {store.error}</Notice> : <Notice quiet>Reading the board…</Notice>}
      </>
    );
  }

  const lifted = lift ? findCard(board, lift.number) : null;
  // A deep link can land before the project list has: the board's own project is always listed.
  const listed = projects.some((p) => p.slug === slug) ? projects : [board.project, ...projects];
  const corpusState = board.corpus.watching ? <Strong>watching</Strong> : <Off>not watching{board.corpus.watch_note ? ` — ${board.corpus.watch_note}` : ""}</Off>;
  const streamState = store.connected ? null : <Off> · page not connected, showing the board as read {ago(board.generated_at)}</Off>;

  const heard = board.watercooler.length ? (board.watercooler[board.watercooler.length - 1] ?? null) : null;

  return (
    <ProjectContext.Provider value={{ slug, path: board.project.path, heard }}>
    <LiftContext.Provider value={controller}>
      <AppHead>
        <Wordmark />
        <ProjectSwitcher projects={listed} current={slug} onSwitch={onSwitch} />
        <CorpusLine>
          <Strong>{board.corpus.live_plans}</Strong> live plans · <Strong>{board.corpus.live_suggestions}</Strong> suggestions · <Strong>{board.corpus.archived}</Strong> archived · {corpusState}
          {streamState}
        </CorpusLine>
        <HeadTools>
          <Lens value={lens} options={LENSES} onChange={setLens} title="A lens, never a write: sorting changes what you see, never the rank. Drag needs Rank." />
          <IdeaDoor onOpen={(text) => void openAnIdea(text)} disabled={ideaOpening} said={ideaSaid} />
        </HeadTools>
      </AppHead>
      <AttentionLine quiet={board.machine.missing.length ? `the runtime cannot find: ${board.machine.missing.join(", ")}` : board.trunk.level === null ? "the trunk has not been read yet" : `trunk ${board.trunk.level ? "level with" : `${board.trunk.behind} behind`} origin/develop`}>
        <Att n={board.attention.asking_you} label="asking you" tone="you" />
        <Att n={board.attention.in_flight} label="in flight" />
        {board.attention.colliding > 0 ? <Att n={board.attention.colliding} label={board.attention.colliding === 1 ? "lane colliding — editing another lane's file" : "lanes colliding — editing each other's files"} tone="bad" /> : null}
        {board.attention.in_discussion > 0 ? <Att n={board.attention.in_discussion} label="in discussion" onClick={() => setTalksOpen((v) => !v)} on={talksOpen} /> : null}
        {board.attention.lanes_ended > 0 ? <Att n={board.attention.lanes_ended} label={board.attention.lanes_ended === 1 ? "lane ended — Resume or Look" : "lanes ended — Resume or Look"} tone="bad" /> : null}
        {board.attention.signals_asking > 0 ? <Att n={board.attention.signals_asking} label={board.attention.signals_asking === 1 ? "shipped card waits on your reading" : "shipped cards wait on your reading"} tone="you" onClick={() => setAsksOpen((v) => !v)} on={asksOpen} /> : null}
        {board.attention.signals_due > 0 ? <Att n={board.attention.signals_due} label={board.attention.signals_due === 1 ? "signal past due" : "signals past due"} tone="you" /> : null}
        {board.attention.doubted > 0 ? <Att n={board.attention.doubted} label={board.attention.doubted === 1 ? "status doubted — its evidence is gone" : "statuses doubted — their evidence is gone"} tone="bad" /> : null}
        {board.attention.verdicts_unread > 0 ? <Att n={board.attention.verdicts_unread} label={board.attention.verdicts_unread === 1 ? "card carries a verdict you have not read" : "cards carry a verdict you have not read"} tone="you" onClick={() => setLens(lens === "triage" ? "rank" : "triage")} on={lens === "triage"} /> : null}
        <Att n={board.attention.arrived_today} label="arrived today" />
        {board.attention.documents_gone > 0 ? <Att n={board.attention.documents_gone} label={board.attention.documents_gone === 1 ? "card cites a document that is nowhere" : "cards cite documents that are nowhere"} tone="bad" /> : null}
        {board.attention.documents_without_card > 0 ? <Att n={board.attention.documents_without_card} label="documents have no card" tone="bad" /> : null}
        {Object.values(store.statuses).filter((s) => s.kind === "failed").length > 0 ? <Att n={Object.values(store.statuses).filter((s) => s.kind === "failed").length} label="write failed" tone="bad" /> : null}
      </AttentionLine>
      {asksOpen && board.asks.length ? (
        <AskList title={`${board.asks.length} shipped card${board.asks.length === 1 ? "" : "s"} wait${board.asks.length === 1 ? "s" : ""} on your reading — only you can read these signals`}>
          {board.asks.map((a) => (
            <AskRow key={a.number} number={a.number} title={a.title} what={a.what} due={a.due} onRead={(delivered) => void readSignal(a.number, delivered)} disabled={reading !== null} />
          ))}
          {readSaid ? <Notice quiet>{readSaid}</Notice> : null}
        </AskList>
      ) : null}
      {talksOpen && board.conversations.length ? (
        <TalkList title={`${board.conversations.length} conversation${board.conversations.length === 1 ? "" : "s"} alive — never hands on a tree`}>
          {board.conversations.map((c) => (
            <TalkRow key={c.short_id} what={c.what} shortId={c.short_id} slot={c.slot} since={ago(c.started_at)} />
          ))}
        </TalkList>
      ) : null}
      {store.error ? <Notice>The board could not be re-read: {store.error}. Showing it as last read, {ago(board.generated_at)}.</Notice> : null}
      {board.trunk.note ? <Notice>The main checkout is not level with origin/develop: {board.trunk.note}</Notice> : null}
      {board.documents_without_card.length ? (
        <Notice>
          Documents in the corpus with no card — the watcher should have carded them; it did not:
          <List items={board.documents_without_card.map((d) => `${d.path} — ${d.title}`)} />
        </Notice>
      ) : null}
      {lens === "triage" ? (
        <Triage slug={slug} verdicts={board.verdicts} onRuled={() => store.refresh()} />
      ) : (
      <DndContext sensors={sensors} collisionDetection={collision} onDragStart={onDragStart} onDragMove={onDragMove} onDragEnd={onDragEnd} onDragCancel={() => controller.cancel()}>
        <BoardStrip>
          {board.columns.map((column, index) =>
            furled.has(column.definition.column) ? (
              <Rail
                key={column.definition.column}
                name={column.definition.column}
                count={column.count}
                onClick={() =>
                  setFurled((f) => {
                    const next = new Set(f);
                    next.delete(column.definition.column);
                    return next;
                  })
                }
              />
            ) : (
              <ColumnBlock
                key={column.definition.column}
                column={column}
                index={index}
                total={board.columns.length}
                lens={lens}
                lift={lift}
                open={open}
                focused={focused}
                statuses={store.statuses}
                unfurled={unfurledMore.has(column.definition.column)}
                onUnfurl={() => unfurlMore(column.definition.column)}
                onFurl={() => setFurled((f) => new Set(f).add(column.definition.column))}
                onOpen={setOpen}
                onRetry={(n) => void store.retry(n)}
                onFocus={setFocused}
                onMoveTo={moveTo}
              />
            ),
          )}
        </BoardStrip>
        <DragOverlay dropAnimation={null}>
          {lifted && lift?.by === "pointer" ? (
            <CardShell number={lifted.number} label={`#${lifted.number} in flight`} lift isStatic>
              <CardBody card={lifted} rank={null} open={false} />
            </CardShell>
          ) : null}
        </DragOverlay>
      </DndContext>
      )}
    </LiftContext.Provider>
    </ProjectContext.Provider>
  );
}
