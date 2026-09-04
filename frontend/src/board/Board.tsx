import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DndContext, DragOverlay, PointerSensor, pointerWithin, rectIntersection, useSensor, useSensors, type CollisionDetection, type DragEndEvent, type DragMoveEvent, type DragStartEvent } from "@dnd-kit/core";
import type { BoardState, CardSummary } from "../types/board";
import type { Place } from "../types/card";
import type { Claim } from "../types/board";
import type { Column } from "../types/column";
import type { Project } from "../types/project";
import { openDoor, openIdea, openPlan, turnDial } from "../api";
import { AppHead, AskList, AskRow, BoardStrip, Breakdown, CardShell, CorpusLine, DialControl, Fact, HeadFrame, HeadTools, IdeaDoor, Lens, List, Notice, Off, ProjectSwitcher, Rail, Strong, Sub, TalkList, TalkRow, TogetherBar, Word, Wordmark, Words } from "../components/ui";
import type { BoardStore } from "../state/board";
import { CardBody } from "./CardView";
import { ColumnBlock, FOLD_AT } from "./ColumnBlock";
import { LiftContext, type LiftController } from "./LiftContext";
import { ProjectContext } from "./ProjectContext";
import { Triage } from "./Triage";
import { samePlace, stepTarget, targetInGroup, type LensKind, type Lift, type StepKey } from "./dnd";
import { WORDS, claimsOf, counted, keeps, lines, type Filter, type WordKey } from "./filter";
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

function isWide(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(WIDE_SCREEN).matches;
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
  const [furled, setFurled] = useState<Set<Column>>(() => new Set<Column>(isWide() ? [] : ["Executed", "Done", "Not now"]));
  const [unfurledMore, setUnfurledMore] = useState<Set<Column>>(new Set());
  const [filter, setFilter] = useState<Filter | null>(null);
  const [reading, setReading] = useState<number | null>(null);
  const [readSaid, setReadSaid] = useState<string | null>(null);
  const [ideaOpening, setIdeaOpening] = useState(false);
  const [ideaSaid, setIdeaSaid] = useState<string | null>(null);
  const [dialTurning, setDialTurning] = useState(false);
  const [dialSaid, setDialSaid] = useState<string | null>(null);
  // Suggestion cards picked for one plan (plan 06, item 5).
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [planning, setPlanning] = useState(false);
  const [planSaid, setPlanSaid] = useState<string | null>(null);
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

  const onSelect = useCallback((number: number, picked: boolean) => {
    setSelected((s) => {
      const next = new Set(s);
      if (picked) next.add(number);
      else next.delete(number);
      return next;
    });
  }, []);

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

  // The dial is the owner's standing ruling (plan 11, item 3): a turn is
  // persisted and audited as his before the head shows it, and the board is
  // re-read so the count beside it is the store's, never the page's.
  const turnTheDial = useCallback(
    async (on: boolean, lanes: number) => {
      setDialTurning(true);
      try {
        const state = await turnDial(on, lanes);
        setDialSaid(`auto-fix ${state.dial.on ? "on" : "off"}, ${state.dial.lanes} fix lane${state.dial.lanes === 1 ? "" : "s"} at most`);
      } catch (e) {
        setDialSaid(`The dial did not turn: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setDialTurning(false);
        await store.refresh();
      }
    },
    [store],
  );

  // One Plan door for every picked suggestion: the brief lists them all and the plan carries them all.
  const planTogether = useCallback(async () => {
    const numbers = Array.from(selected).sort((a, b) => a - b);
    setPlanning(true);
    setPlanSaid("Opening…");
    try {
      const result = await openPlan(slug, numbers);
      setPlanSaid(result.said);
      setSelected(new Set());
    } catch (e) {
      setPlanSaid(`Plan did not open: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setPlanning(false);
    }
  }, [slug, selected]);

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

  // The three words filter the board; a sub-filter narrows to one claim.
  // Clicking a word again clears it — the whole board is one click away.
  const attention = board.attention;
  const admitted = filter ? claimsOf(attention, filter) : null;
  // A filtered column counts and folds what it is actually showing: a group
  // with nothing left in it names nothing, and "+ N more" never promises
  // cards the filter has already taken away.
  const shown = admitted
    ? board.columns.map((column) => {
        const groups = column.groups
          .map((group) => ({ ...group, cards: group.cards.filter((c) => keeps(c, admitted)) }))
          .filter((group) => group.cards.length > 0);
        return { ...column, groups, count: groups.reduce((n, g) => n + g.cards.length, 0) };
      })
    : board.columns;
  // Clicking the word that is already filtering clears it, narrowed or not:
  // the whole board is always one click away.
  const pick = (word: WordKey) => setFilter((f) => (f !== null && f.word === word ? null : { word, claim: null }));
  const narrow = (word: WordKey, claim: Claim) => {
    // The verdicts have a surface of their own; narrowing to them is how the
    // head reaches it, so there is one way into the triage lens, not two.
    if (claim === "verdict") setLens("triage");
    setFilter((f) => (f !== null && f.claim === claim ? { word, claim: null } : { word, claim }));
  };
  // A sub-filter shows the surface that acts on its claim, where one exists:
  // the batched signals, the conversations alive, the documents with no card.
  const on = (claim: Claim) => filter !== null && (filter.claim === claim || (filter.claim === null && lines(attention, filter.word).some((l) => l.claim === claim)));
  const failed = Object.values(store.statuses).filter((st) => st.kind === "failed").length;

  return (
    <ProjectContext.Provider value={{ slug, path: board.project.path, heard }}>
    <LiftContext.Provider value={controller}>
      <HeadFrame>
      <AppHead>
        <Wordmark />
        <ProjectSwitcher
          projects={listed}
          current={slug}
          onSwitch={onSwitch}
          facts={
            <>
              <CorpusLine>
                <Strong>{board.corpus.live_plans}</Strong> live plans · <Strong>{board.corpus.live_suggestions}</Strong> suggestions · <Strong>{board.corpus.archived}</Strong> archived · {corpusState}
                {streamState}
              </CorpusLine>
              <Fact>
                <Strong>{attention.arrived_today}</Strong> arrived today · <Strong>{attention.unplanned_defects}</Strong> defects and <Strong>{attention.unplanned_ideas}</Strong> ideas unplanned
              </Fact>
              {board.machine.missing.length ? (
                <Fact meaning="broken">the runtime cannot find: {board.machine.missing.join(", ")}</Fact>
              ) : null}
              {board.trunk.level === null ? (
                <Fact>the trunk has not been read yet</Fact>
              ) : board.trunk.level ? (
                <Fact meaning="proven">trunk level with origin/develop</Fact>
              ) : (
                <Fact meaning="broken">trunk {board.trunk.behind} behind origin/develop</Fact>
              )}
              {failed > 0 ? <Fact meaning="broken">{failed} write{failed === 1 ? "" : "s"} failed — see the card</Fact> : null}
            </>
          }
        />
        <Words>
          {WORDS.map((word) => (
            <Word key={word.key} label={word.label} count={counted(attention, word.key)} meaning={word.meaning} on={filter?.word === word.key} onClick={() => pick(word.key)} />
          ))}
        </Words>
        <HeadTools>
          <DialControl state={board.dial} onTurn={(on, lanes) => void turnTheDial(on, lanes)} disabled={dialTurning} said={dialSaid} />
          <Lens value={lens} options={LENSES} onChange={setLens} title="A lens, never a write: sorting changes what you see, never the rank. Drag needs Rank." />
          <IdeaDoor onOpen={(text) => void openAnIdea(text)} disabled={ideaOpening} said={ideaSaid} />
        </HeadTools>
      </AppHead>
      {filter ? (
        <Breakdown label={`What ${WORDS.find((w) => w.key === filter.word)?.label} counts`} onClear={() => setFilter(null)}>
          {lines(attention, filter.word).map((line) => (
            <Sub key={line.claim} line={line} meaning={filter.word} on={filter.claim === line.claim} onClick={() => narrow(filter.word, line.claim)} />
          ))}
        </Breakdown>
      ) : null}
      </HeadFrame>
      {on("signal asking") && board.asks.length ? (
        <AskList title={`${board.asks.length} shipped card${board.asks.length === 1 ? "" : "s"} wait${board.asks.length === 1 ? "s" : ""} on your reading — only you can read these signals, or a session read them and could not tell`}>
          {board.asks.map((a) => (
            <AskRow key={a.number} number={a.number} title={a.title} what={a.what} due={a.due} evidence={a.evidence} onRead={(delivered) => void readSignal(a.number, delivered)} disabled={reading !== null} />
          ))}
          {readSaid ? <Notice quiet>{readSaid}</Notice> : null}
        </AskList>
      ) : null}
      {on("conversation") && board.conversations.length ? (
        <TalkList title={`${board.conversations.length} conversation${board.conversations.length === 1 ? "" : "s"} alive — never hands on a tree`}>
          {board.conversations.map((c) => (
            <TalkRow key={c.short_id} what={c.what} shortId={c.short_id} slot={c.slot} since={ago(c.started_at)} />
          ))}
        </TalkList>
      ) : null}
      {selected.size > 0 || planSaid ? <TogetherBar count={selected.size} onPlan={() => void planTogether()} onClear={() => { setSelected(new Set()); setPlanSaid(null); }} disabled={planning} said={planSaid} /> : null}
      {store.error ? <Notice>The board could not be re-read: {store.error}. Showing it as last read, {ago(board.generated_at)}.</Notice> : null}
      {board.trunk.note ? <Notice>The main checkout is not level with origin/develop: {board.trunk.note}</Notice> : null}
      {on("document without card") && board.documents_without_card.length ? (
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
          {shown.map((column, index) =>
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
                total={shown.length}
                lens={lens}
                lift={lift}
                open={open}
                focused={focused}
                statuses={store.statuses}
                unfurled={unfurledMore.has(column.definition.column)}
                selected={selected}
                onUnfurl={() => unfurlMore(column.definition.column)}
                onFurl={() => setFurled((f) => new Set(f).add(column.definition.column))}
                onOpen={setOpen}
                onRetry={(n) => void store.retry(n)}
                onFocus={setFocused}
                onMoveTo={moveTo}
                onSelect={onSelect}
              />
            ),
          )}
        </BoardStrip>
        <DragOverlay dropAnimation={null}>
          {lifted && lift?.by === "pointer" ? (
            <CardShell number={lifted.number} meaning={lifted.state.meaning} label={`#${lifted.number} in flight`} lift isStatic>
              <CardBody card={lifted} open={false} />
            </CardShell>
          ) : null}
        </DragOverlay>
      </DndContext>
      )}
    </LiftContext.Provider>
    </ProjectContext.Provider>
  );
}
