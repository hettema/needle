import { useEffect, useState } from "react";
import { getCard, getFile, openDoor, openPlan, type DoorName } from "../api";
import type { CardDetail, CardSummary } from "../types/board";
import type { Column } from "../types/column";
import { COLUMN_VALUES } from "../types/column";
import type { AuditEntry } from "../types/audit";
import type { Door } from "../types/lane";
import {
  Acts,
  AnswerBox,
  Ask,
  Band,
  Button,
  Carries,
  Clash,
  ClosedDoor,
  ClosedDoors,
  Doubt,
  EssenceBig,
  Heard,
  Hist,
  HistRow,
  Inline,
  Items,
  Markdown,
  MoveTo,
  Note,
  Notice,
  OpenBody,
  Passes,
  PathText,
  PlanBlock,
  PlanBody,
  PlanHead,
  Quiet,
  RowLine,
  Said,
  Section,
  StatLine,
  StatLines,
  Strip,
} from "../components/ui";
import { ago, when } from "./time";
import { useProject } from "./ProjectContext";

const WHO: Record<AuditEntry["actor"], string> = { owner: "you", session: "session", import: "import", corpus: "corpus", machine: "board" };

function What({ detail }: { detail: string }) {
  const space = detail.indexOf(" ");
  if (space < 0) return <b>{detail}</b>;
  return (
    <>
      <b>{detail.slice(0, space)}</b>
      {detail.slice(space)}
    </>
  );
}

export function OpenCard({ card, onMoveTo }: { card: CardSummary; onMoveTo: (number: number, column: string) => Promise<boolean> }) {
  const { slug, path: projectPath } = useProject();
  const [detail, setDetail] = useState<CardDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wholeFile, setWholeFile] = useState<{ path: string; text: string } | null>(null);
  const [said, setSaid] = useState<{ text: string; bad: boolean } | null>(null);
  const [intentOpen, setIntentOpen] = useState(true);
  const [opening, setOpening] = useState<DoorName | "plan" | null>(null);

  useEffect(() => {
    let live = true;
    setDetail(null);
    setWholeFile(null);
    setSaid(null);
    getCard(slug, card.number).then(
      (d) => {
        if (live) setDetail(d);
      },
      (e: unknown) => {
        if (live) setError(e instanceof Error ? e.message : String(e));
      },
    );
    return () => {
      live = false;
    };
  }, [slug, card.number, card.place.column, card.place.group, card.place.position]);

  if (error) {
    return (
      <OpenBody>
        <Notice>This card could not be read: {error}</Notice>
      </OpenBody>
    );
  }
  if (!detail) {
    return (
      <OpenBody>
        <Section title="Reading">
          <Quiet>Reading the card and its document…</Quiet>
        </Section>
      </OpenBody>
    );
  }

  const document = detail.document;
  const docPath = detail.summary.document_path;
  const reviewRow = detail.record.find((r) => r.kind === "REVIEW");
  const reviewPath = reviewRow ? /docs\/[\w./-]+\.md/.exec(reviewRow.text)?.[0] ?? null : null;

  const openFile = async (path: string, what: string) => {
    if (wholeFile && wholeFile.path === path) {
      setWholeFile(null);
      return;
    }
    try {
      const file = await getFile(slug, path);
      setWholeFile({ path: file.path, text: file.text });
      setSaid({ text: `${what} opened, read ${ago(file.read_at)}`, bad: false });
    } catch (e) {
      setSaid({ text: `Could not open ${what}: ${e instanceof Error ? e.message : String(e)}`, bad: true });
    }
  };

  const copyPath = async () => {
    const absolute = `${projectPath}/${docPath ?? ""}`;
    try {
      if (!docPath) throw new Error("this card cites no document");
      await navigator.clipboard.writeText(absolute);
      setSaid({ text: `Copied ${absolute}`, bad: false });
    } catch (e) {
      setSaid({ text: `Could not copy: ${e instanceof Error ? e.message : String(e)}`, bad: true });
    }
  };

  const moveTo = async (column: Column) => {
    if (column === card.place.column) return;
    const ok = await onMoveTo(card.number, column);
    setSaid(ok ? { text: `Moved to ${column}`, bad: false } : { text: "Not moved — see the card", bad: true });
  };

  // A door opens through the runtime and answers with its evidence, or fails by name;
  // the board's own stream then brings the card's new state.
  const through = async (door: DoorName | "plan", body: object = {}) => {
    setOpening(door);
    setSaid({ text: `${door === "signal" ? "Reading" : door[0]?.toUpperCase() + door.slice(1)}…`, bad: false });
    try {
      const result = door === "plan" ? await openPlan(slug, [card.number]) : await openDoor(slug, card.number, door, body);
      setSaid({ text: result.said, bad: false });
    } catch (e) {
      setSaid({ text: `${door[0]?.toUpperCase() + door.slice(1)} did not open: ${e instanceof Error ? e.message : String(e)}`, bad: true });
    } finally {
      setOpening(null);
    }
  };
  const doors = detail.doors;
  const lane = detail.lane;
  // The items are the lane's own copy while it has hands on the card, and
  // the plan as the trunk holds it in every other column — so a shipped
  // card keeps the shape of its run (plan 13, item 3).
  const progress = lane?.progress ?? null;
  const items = progress ? progress.items : document?.items ?? [];
  // The header keeps to one line at the open card's width (the served board
  // wrapped it under the whole count line): the count, and where it was read.
  const itemsFrom = progress
    ? `${progress.met} of ${progress.total} met${progress.deviated ? `, ${progress.deviated} deviated` : ""} · read ${ago(progress.read_at)} from the lane's copy`
    : document
      ? `${document.items.filter((i) => i.stance !== null).length} of ${document.items.length} marked, as the plan holds them`
      : undefined;
  // One door is filled and the rest are outlined: pressable is a shape, never
  // a hue (plan 27, item 4). The filled one is the first act this state
  // allows, in the order a card is acted on.
  const primary = ([
    ["start", doors.start],
    ["answer", doors.answer],
    ["watch", doors.watch],
    ["resume", doors.resume],
    ["look", doors.look],
    ["plan", doors.plan],
  ] as const).find(([, d]) => d.offered)?.[0] ?? null;
  const door = (name: DoorName, d: Door) =>
    d.offered ? (
      <Button key={name} ghost={primary !== name} onClick={() => void through(name)} disabled={opening !== null} title={d.why}>
        {d.label}
      </Button>
    ) : null;

  const essenceFrom =
    detail.summary.essence_source === "card"
      ? "the card's own words"
      : detail.summary.essence_source === "document"
        ? "the first sentence of the document's intent, standing in"
        : undefined;

  // The doors sit under the title, where the owner's hand already is (plan 04,
  // item 2), and every door he would expect on this card that cannot open says
  // why in text: on card 387 he looked for Watch and found only a tooltip.
  const expected: { label: string; why: string }[] = [];
  if (lane && lane.state !== "none") {
    for (const d of [doors.watch, doors.answer, doors.look, doors.resume, doors.stop]) if (!d.offered) expected.push({ label: d.label, why: d.why });
  }
  if (!doors.discuss.offered) expected.push({ label: doors.discuss.label, why: doors.discuss.why });
  if (card.document_state === "suggestion" && !doors.plan.offered) expected.push({ label: doors.plan.label, why: doors.plan.why });
  // A gateless document in the queue shows Start closed with its reason, like every other closed door (plan 06, item 3).
  const startable = card.place.column === "Up next" || card.place.column === "Planned";

  return (
    <OpenBody>
      <Acts>
        {doors.start.offered ? (
          <Button onClick={() => void through("start")} disabled={opening !== null} title={doors.start.why}>
            {doors.start.label}
          </Button>
        ) : startable && detail.card.folded_into === null ? (
          <ClosedDoor why={doors.start.why}>Start</ClosedDoor>
        ) : null}
        {door("watch", doors.watch)}
        {door("look", doors.look)}
        {door("resume", doors.resume)}
        {door("stop", doors.stop)}
        {door("discuss", doors.discuss)}
        {doors.plan.offered ? (
          <Button ghost={primary !== "plan"} onClick={() => void through("plan")} disabled={opening !== null} title={doors.plan.why}>
            {doors.plan.label}
          </Button>
        ) : null}
        {doors.collision && doors.collision.verdict !== "clear" && doors.start.offered ? <Quiet>{doors.collision.sentence}</Quiet> : null}
        {docPath && document ? <Button ghost onClick={() => void openFile(docPath, document.kind === "plan" ? "the plan" : "the suggestion")}>{wholeFile?.path === docPath ? "Close the file" : document.kind === "plan" ? "Open the plan" : "Open the suggestion"}</Button> : null}
        {docPath ? (
          <Button ghost onClick={() => void copyPath()}>
            Copy path
          </Button>
        ) : null}
        {reviewPath ? (
          <Button ghost onClick={() => void openFile(reviewPath, "the review")}>
            {wholeFile?.path === reviewPath ? "Close the review" : "Open the review"}
          </Button>
        ) : null}
        {said ? <Said bad={said.bad}>{said.text}</Said> : null}
        <MoveTo value={card.place.column} options={COLUMN_VALUES} onChange={(c) => void moveTo(c)} />
      </Acts>
      <ClosedDoors doors={expected} />
      {startable && !doors.start.offered && detail.card.folded_into === null ? <Quiet>Start is closed: {doors.start.why}</Quiet> : null}
      {detail.summary.standing.state === "doubted" && detail.summary.standing.words ? <Doubt>{detail.summary.standing.words}</Doubt> : null}
      {detail.card.folded_into !== null ? <Quiet>Folded into #{detail.card.folded_into}: that card's plan carries this suggestion; this card follows it and closes with it.</Quiet> : null}
      {detail.summary.folded.length ? (
        <Section title="What it carries" from={`${detail.summary.folded.length} suggestion${detail.summary.folded.length === 1 ? "" : "s"} folded under this card; they follow it and close with it`}>
          <Carries cards={detail.summary.folded} open />
        </Section>
      ) : null}

      <Section title="What it makes true" from={essenceFrom}>
        {detail.summary.essence ? (
          <EssenceBig>
            <Inline text={detail.summary.essence} />
          </EssenceBig>
        ) : (
          <Quiet>Nothing written yet — no SERVES row on the card and no intent in a document.</Quiet>
        )}
        {detail.card.deep ? (
          <Note>
            <Inline text={detail.card.deep} />
          </Note>
        ) : null}
      </Section>

      {items.length ? (
        <Section title="The plan's items" from={itemsFrom}>
          <Strip items={items} label={itemsFrom ?? "the plan's items"} />
          <Items items={items} />
        </Section>
      ) : null}

      {progress && !progress.review && progress.met + progress.deviated === progress.total ? (
        <Section title="The review" from="not started, or unnamed">
          <Quiet>Every item is marked, and no record under docs/reviews/ in the lane's worktree names this plan on its Plan: line yet. The counter turns into the review loop's the moment one does.</Quiet>
        </Section>
      ) : null}

      {progress?.review ? (
        <Section title="The review" from={progress.line}>
          <Passes review={progress.review} />
          <Quiet>
            Read from <PathText>{progress.review.path}</PathText> in the lane's worktree, {ago(progress.read_at)}.
          </Quiet>
        </Section>
      ) : null}

      {lane && lane.state !== "none" ? (
        <Section title="The lane" from={lane.session ? `${lane.session.short_id} · ${lane.session.model ?? "fable"} on ${lane.session.slot}` : lane.name}>
          <Band state={card.state}>{lane.sentence}</Band>
          {lane.state === "asking" && lane.question ? <Ask>{lane.question}</Ask> : null}
          {doors.answer.offered ? <AnswerBox onSend={(text) => void through("answer", { text })} disabled={opening !== null} hint="One sentence resumes the lane with it" /> : null}
          {lane.colliding ? <Clash>{lane.colliding.sentence}</Clash> : null}
          {lane.session?.doing ? <Quiet>Doing: {lane.session.doing.step}, {ago(lane.session.doing.at)}{lane.session.detail ? ` — "${lane.session.detail}"` : ""}</Quiet> : null}
          {lane.died ? <Quiet>{lane.died}</Quiet> : null}
          {lane.moved ? <Quiet>{lane.moved}</Quiet> : null}
          {lane.edits.length ? <Quiet>Touching: {lane.edits.join(", ")}</Quiet> : null}
          {lane.declared.length ? <Quiet>Its plan names: {lane.declared.join(", ")}</Quiet> : null}
        </Section>
      ) : null}

      {lane && lane.state !== "none" ? (
        <Section title="The watercooler" from={detail.watercooler.length ? "what the lanes on this project say to each other; a running lane hears it inside its session within a minute, and every lane reads it at start and before its fold" : "nothing said yet"}>
          {detail.heard && detail.heard.at && detail.heard.text ? <Heard who={`its lane heard, ${ago(detail.heard.at)}`}>{detail.heard.text}</Heard> : null}
          {detail.watercooler.length ? (
            <Hist>
              {detail.watercooler.map((line) => (
                <HistRow key={line.id} when={when(line.at)} what={line.text} who={line.card_number === null ? "board" : `#${line.card_number}`} owner={false} />
              ))}
            </Hist>
          ) : (
            <Quiet>No lane has said anything yet. A lane says something when it touches a file outside its footprint or changes a seam another lane depends on.</Quiet>
          )}
        </Section>
      ) : null}

      {detail.summary.planning ? (
        <Section title="The dial" from="the owner's standing ruling: a defect marked Fix: now enters execution without him">
          <Quiet>
            The dial took it: a session is writing its plan in the project's checkout — {detail.summary.planning.session_id.slice(0, 8)} on {detail.summary.planning.slot}, since {ago(detail.summary.planning.started_at)}. Never hands on the tree. When the plan lands this card becomes the plan's and the board opens Start itself; a decision that is yours lands here as an ASK row instead.
          </Quiet>
        </Section>
      ) : null}

      {detail.summary.routing ? (
        <Section title="Who fixes it" from={`Fix: ${detail.summary.fix ? detail.summary.fix.mark : "unmarked"} · routes as ${detail.summary.routing.state}`}>
          <Quiet>{detail.summary.routing.why}</Quiet>
          {detail.triage ? (
            <Quiet>
              The reading of {detail.triage.at.slice(0, 10)} landed <b>{detail.triage.result}</b>, decision {detail.triage.decision}
              {detail.triage.direction ? `, direction: ${detail.triage.direction}` : ""}. {detail.triage.words}
            </Quiet>
          ) : null}
          {detail.source ? <Quiet>The source it read: {detail.source.note}</Quiet> : null}
          {detail.summary.triaging ? (
            <Quiet>
              A reading is verifying this mark now: {detail.summary.triaging.session_id.slice(0, 8)} on {detail.summary.triaging.slot}, since {ago(detail.summary.triaging.started_at)}. It has no share of the context that filed the defect, and it writes nothing but its result.
            </Quiet>
          ) : null}
          {doors.answer.offered && detail.summary.routing.state === "triaged his" ? (
            <Ask>
              {doors.answer.why}
              <AnswerBox onSend={(text) => void through("answer", { text })} disabled={opening !== null} hint="Your sentence is the ruling; a short lane writes it into the document" label="Rule" />
            </Ask>
          ) : null}
        </Section>
      ) : null}

      {detail.trigger || (detail.summary.fix?.mark === "when" && detail.trigger_note) ? (
        <Section title="The trigger" from={detail.trigger ? `Fix: when · ${detail.trigger.kind} · due ${detail.trigger.due} · every ${detail.trigger.every_hours}h` : "Fix: when, and the board cannot read it"}>
          {detail.trigger ? (
            <Quiet>
              {detail.trigger.what} — {detail.trigger.kind} {detail.trigger.target}
              {detail.trigger.expect ? ` expect ${detail.trigger.expect}` : ""}. Read on the same cadence as a shipped card's signal; delivered makes this defect eligible for the dial and moves nothing.
            </Quiet>
          ) : (
            <Quiet>{detail.trigger_note}</Quiet>
          )}
          {detail.summary.reading ? (
            <Quiet>
              A session is reading this trigger now: {detail.summary.reading.session_id.slice(0, 8)} on {detail.summary.reading.slot}, since {ago(detail.summary.reading.started_at)}.
            </Quiet>
          ) : null}
          {doors.signal.offered && !detail.signal ? (
            <Ask>
              {doors.signal.why}
              <Acts>
                <Button onClick={() => void through("signal", { delivered: true })} disabled={opening !== null}>
                  Fired
                </Button>
                <Button ghost onClick={() => void through("signal", { delivered: false })} disabled={opening !== null}>
                  Not yet
                </Button>
              </Acts>
            </Ask>
          ) : null}
          {detail.readings.length && !detail.signal ? (
            <Hist>
              {detail.readings.slice(0, 5).map((r) => (
                <HistRow key={r.id} when={when(r.at)} what={<What detail={`${r.delivered === null ? (r.actor === "session" ? "Cannot tell" : "Unreadable") : r.delivered ? "Fired" : "Not yet"} — ${r.words}`} />} who={r.actor === "owner" ? "you" : r.actor === "session" ? "a session" : "board"} owner={r.actor === "owner"} />
              ))}
            </Hist>
          ) : null}
        </Section>
      ) : null}

      {card.place.column === "Executed" || card.place.column === "Done" || detail.signal ? (
        <Section title="The signal" from={detail.signal ? `${detail.signal.kind} · due ${detail.signal.due} · every ${detail.signal.every_hours}h` : "none the board can read"}>
          {detail.signal ? (
            <RowLine kind="WATCH" text={`${detail.signal.what} — ${detail.signal.kind} ${detail.signal.target}${detail.signal.expect ? ` expect ${detail.signal.expect}` : ""}`} />
          ) : (
            <Quiet>{detail.signal_note ?? "No WATCH row names a signal."} Without one the card cannot enter Executed.</Quiet>
          )}
          {detail.summary.reading ? (
            <Quiet>
              A session is reading this signal now: {detail.summary.reading.session_id.slice(0, 8)} on {detail.summary.reading.slot}, since {ago(detail.summary.reading.started_at)}. Never hands on the tree; its finding moves the card.
            </Quiet>
          ) : null}
          {doors.signal.offered ? (
            <Ask>
              {doors.signal.why}
              <Acts>
                <Button onClick={() => void through("signal", { delivered: true })} disabled={opening !== null}>
                  Delivered
                </Button>
                <Button ghost onClick={() => void through("signal", { delivered: false })} disabled={opening !== null}>
                  Not delivered
                </Button>
              </Acts>
            </Ask>
          ) : null}
          {detail.readings.length ? (
            <Hist>
              {detail.readings.slice(0, 5).map((r) => (
                <HistRow key={r.id} when={when(r.at)} what={<What detail={`${r.delivered === null ? (r.actor === "session" ? "Cannot tell" : "Unreadable") : r.delivered ? "Delivered" : "Not delivered"} — ${r.words}`} />} who={r.actor === "owner" ? "you" : r.actor === "session" ? "a session" : "board"} owner={r.actor === "owner"} />
              ))}
            </Hist>
          ) : null}
        </Section>
      ) : null}

      <Section title="The brief" from={detail.brief.length ? `${detail.brief.length} point${detail.brief.length === 1 ? "" : "s"}` : "nothing written yet"}>
        {detail.brief.length ? detail.brief.map((r, i) => <RowLine key={i} kind={r.kind} text={r.text} />) : <Quiet>Nothing is written on this card before the work.</Quiet>}
      </Section>

      <Section title="The record" from={detail.record.length ? "written back by the session that did the work" : "nothing written yet"}>
        {detail.record.length ? (
          detail.record.map((r, i) => <RowLine key={i} kind={r.kind} text={r.text} />)
        ) : (
          <Quiet>Nothing has been done to this card. What a session writes back — what it delivered, what to watch for, the review record — lands here, in this place on every card.</Quiet>
        )}
      </Section>

      <Section
        title={document ? (document.kind === "plan" ? "The plan" : "The suggestion") : "The document"}
        from={document ? `read from the file, ${ago(document.read_at)}` : detail.summary.document_state === "gone" ? "cited, and nowhere" : "none — this card is a note"}
      >
        {document ? (
          <PlanBlock>
            <PlanHead path={document.path} toggle={() => setIntentOpen((v) => !v)} open={intentOpen} toggleLabel={document.intent_heading ? document.intent_heading.toLowerCase() : "text"} />
            <PlanBody>
              <StatLines>
                {document.head_fields.map((f) => (
                  <StatLine key={f.key} k={f.key} v={<Inline text={f.value} />} />
                ))}
                {document.archived ? <StatLine k="Archived" v={<b>yes — in done/</b>} /> : null}
                {detail.handouts.named.map((h, i) => (
                  <StatLine key={i} k="Hands out" v={<Inline text={`${h.item ? `${h.item} — ` : ""}${h.role}: ${h.what}; verifies ${h.verifies ?? "nothing named"}`} />} />
                ))}
              </StatLines>
              {detail.handouts.verdict ? <Notice>{detail.handouts.verdict}</Notice> : null}
              {intentOpen ? <Markdown text={document.intent ? `## ${document.intent_heading ?? "Intent"}\n\n${document.intent}` : "_This document has no body._"} /> : null}
            </PlanBody>
          </PlanBlock>
        ) : docPath ? (
          <Notice>
            This card cites <PathText>{docPath}</PathText>, and no such file exists in the project.
          </Notice>
        ) : (
          <Quiet>No plan or suggestion is written behind this card. It is a note: the owner's own item, legitimately on the board without a document.</Quiet>
        )}
        {detail.other_citations.length ? (
          <StatLines>
            <StatLine k="Also cites" v={detail.other_citations.map((c) => <PathText key={c}>{c} </PathText>)} />
          </StatLines>
        ) : null}
        {wholeFile ? (
          <PlanBlock>
            <PlanHead path={wholeFile.path} toggle={() => setWholeFile(null)} open={true} toggleLabel="whole file" />
            <Markdown text={wholeFile.text} />
          </PlanBlock>
        ) : null}
      </Section>

      <Section title="History" from="every change to this card, since Needle">
        <Hist>
          {detail.history.map((h) => (
            <HistRow key={h.id} when={when(h.at)} what={<What detail={h.detail} />} who={WHO[h.actor]} owner={h.actor === "owner"} />
          ))}
        </Hist>
        <Quiet>0.1 kept no history, so every card's record starts at the import. From here on, nothing moves without a row.</Quiet>
      </Section>

    </OpenBody>
  );
}
