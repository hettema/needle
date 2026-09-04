import { useEffect, useState } from "react";
import { getCard, getFile, openDoor, type DoorName } from "../api";
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
  ClosedDoor,
  ClosedDoors,
  Doubt,
  EssenceBig,
  Hist,
  HistRow,
  Inline,
  Markdown,
  MoveTo,
  Note,
  Notice,
  OpenBody,
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
  const [opening, setOpening] = useState<DoorName | null>(null);

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
  const through = async (door: DoorName, body: object = {}) => {
    setOpening(door);
    setSaid({ text: `${door === "signal" ? "Reading" : door[0]?.toUpperCase() + door.slice(1)}…`, bad: false });
    try {
      const result = await openDoor(slug, card.number, door, body);
      setSaid({ text: result.said, bad: false });
    } catch (e) {
      setSaid({ text: `${door[0]?.toUpperCase() + door.slice(1)} did not open: ${e instanceof Error ? e.message : String(e)}`, bad: true });
    } finally {
      setOpening(null);
    }
  };
  const door = (name: DoorName, d: Door, ghost = true) =>
    d.offered ? (
      <Button key={name} ghost={ghost} onClick={() => void through(name)} disabled={opening !== null} title={d.why}>
        {d.label}
      </Button>
    ) : null;
  const doors = detail.doors;
  const lane = detail.lane;

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

  return (
    <OpenBody>
      <Acts>
        {doors.start.offered ? (
          <Button onClick={() => void through("start")} disabled={opening !== null} title={doors.start.why}>
            {doors.start.label}
          </Button>
        ) : doors.start_anyway.offered ? (
          <>
            <ClosedDoor why={doors.start.why}>Start</ClosedDoor>
            <Button onClick={() => void through("start", { anyway: true })} disabled={opening !== null} title={doors.start_anyway.why}>
              {doors.start_anyway.label}
            </Button>
          </>
        ) : card.gate && (card.place.column === "Up next" || card.place.column === "Planned") ? (
          <ClosedDoor why={doors.start.why}>Start</ClosedDoor>
        ) : null}
        {door("watch", doors.watch)}
        {door("look", doors.look)}
        {door("resume", doors.resume)}
        {door("stop", doors.stop)}
        {door("discuss", doors.discuss)}
        {doors.collision && doors.collision.verdict !== "clear" && (doors.start.offered || doors.start_anyway.offered) ? <Quiet>{doors.collision.sentence}</Quiet> : null}
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
      {detail.summary.standing.state === "doubted" && detail.summary.standing.words ? <Doubt>{detail.summary.standing.words}</Doubt> : null}

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

      {lane && lane.state !== "none" ? (
        <Section title="The lane" from={lane.session ? `${lane.session.short_id} · ${lane.session.model ?? "fable"} on ${lane.session.slot}` : lane.name}>
          <Band state={lane.state}>{lane.sentence}</Band>
          {lane.state === "asking" && lane.question ? <Ask>{lane.question}</Ask> : null}
          {doors.answer.offered ? <AnswerBox onSend={(text) => void through("answer", { text })} disabled={opening !== null} hint="One sentence resumes the lane with it" /> : null}
          {lane.died ? <Quiet>{lane.died}</Quiet> : null}
          {lane.moved ? <Quiet>{lane.moved}</Quiet> : null}
        </Section>
      ) : null}

      {card.place.column === "Executed" || card.place.column === "Done" || detail.signal ? (
        <Section title="The signal" from={detail.signal ? `${detail.signal.kind} · due ${detail.signal.due} · every ${detail.signal.every_hours}h` : "none the board can read"}>
          {detail.signal ? (
            <RowLine kind="WATCH" text={`${detail.signal.what} — ${detail.signal.kind} ${detail.signal.target}${detail.signal.expect ? ` expect ${detail.signal.expect}` : ""}`} />
          ) : (
            <Quiet>{detail.signal_note ?? "No WATCH row names a signal."} Without one the card cannot enter Executed.</Quiet>
          )}
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
                <HistRow key={r.id} when={when(r.at)} what={<What detail={`${r.delivered === null ? "Unreadable" : r.delivered ? "Delivered" : "Not delivered"} — ${r.words}`} />} who="board" owner={false} />
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
              </StatLines>
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
