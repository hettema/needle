import { useState } from "react";
import { acceptClass, openDoor } from "../api";
import type { EvidenceClass, VerdictLine } from "../types/verdict";
import { EVIDENCE_CLASS_VALUES } from "../types/verdict";
import { AnswerBox, Notice, TriageGroup, TriageList, TriageRow } from "../components/ui";

/**
 * The triage lens (plan 05, item 2): every card carrying an unread verdict as
 * one line — number, title, where it sits, the evidence, the landing — grouped
 * by class, with Accept all in this class, Accept and Overturn. Each ruling
 * goes through the doors the board offers and the board is re-read after;
 * nothing here moves a card itself.
 */
export function Triage({ slug, verdicts, onRuled }: { slug: string; verdicts: VerdictLine[]; onRuled: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<string | null>(null);
  const [overturning, setOverturning] = useState<number | null>(null);

  const rule = async (what: () => Promise<string>) => {
    setBusy(true);
    try {
      setSaid(await what());
    } catch (e) {
      setSaid(`The ruling did not land — ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
      setOverturning(null);
      await onRuled();
    }
  };
  const accept = (number: number) => rule(async () => (await openDoor(slug, number, "accept", {})).said);
  const overturn = (number: number, text: string) => rule(async () => (await openDoor(slug, number, "overturn", { text })).said);
  const acceptAll = (evidenceClass: EvidenceClass) =>
    rule(async () => {
      const ruled = await acceptClass(slug, evidenceClass);
      const refused = ruled.refused.length ? `; refused ${ruled.refused.length}: ${ruled.refused.join(" · ")}` : "";
      return `Accepted ${ruled.accepted} in "${evidenceClass}"${refused}`;
    });

  const groups = EVIDENCE_CLASS_VALUES.map((evidenceClass) => ({ evidenceClass, lines: verdicts.filter((v) => v.verdict.evidence_class === evidenceClass) })).filter((g) => g.lines.length > 0);
  const title = `${verdicts.length} card${verdicts.length === 1 ? "" : "s"} carr${verdicts.length === 1 ? "ies" : "y"} a verdict you have not read`;

  return (
    <TriageList title={title}>
      {groups.length === 0 ? <Notice quiet>Every verdict is read. The board is as clean as its evidence.</Notice> : null}
      {groups.map(({ evidenceClass, lines }) => (
        <TriageGroup key={evidenceClass} name={evidenceClass} count={lines.length} onAcceptAll={() => void acceptAll(evidenceClass)} disabled={busy}>
          {lines.map((line) => (
            <TriageRow
              key={line.number}
              number={line.number}
              title={line.title}
              column={line.place.column}
              evidence={line.verdict.evidence}
              landing={line.verdict.to === null ? "stays" : `→ ${line.verdict.to}`}
              onAccept={() => void accept(line.number)}
              onOverturn={() => setOverturning(overturning === line.number ? null : line.number)}
              overturning={overturning === line.number}
              disabled={busy}
            >
              {overturning === line.number ? <AnswerBox label="Overturn" onSend={(text) => void overturn(line.number, text)} disabled={busy} hint="Your word keeps the card where it is and is recorded on it" /> : null}
            </TriageRow>
          ))}
        </TriageGroup>
      ))}
      {said ? <Notice quiet>{said}</Notice> : null}
    </TriageList>
  );
}
