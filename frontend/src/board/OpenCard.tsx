import { useEffect, useState } from "react";
import { getCard, getFile } from "../api";
import type { CardDetail, CardSummary } from "../types/board";
import type { Column } from "../types/column";
import { COLUMN_VALUES } from "../types/column";
import type { AuditEntry } from "../types/audit";
import {
  Acts,
  Button,
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

const WHO: Record<AuditEntry["actor"], string> = { owner: "you", session: "session", import: "import", corpus: "corpus" };

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

  const essenceFrom =
    detail.summary.essence_source === "card"
      ? "the card's own words"
      : detail.summary.essence_source === "document"
        ? "the first sentence of the document's intent, standing in"
        : undefined;

  return (
    <OpenBody>
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

      <Acts>
        {docPath && document ? <Button onClick={() => void openFile(docPath, document.kind === "plan" ? "the plan" : "the suggestion")}>{wholeFile?.path === docPath ? "Close the file" : document.kind === "plan" ? "Open the plan" : "Open the suggestion"}</Button> : null}
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
    </OpenBody>
  );
}
