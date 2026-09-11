# Our working rules earn the work they cause

**Status:** Delivered; owner assessment of the recommendations remains the outcome signal
**Written:** 2026-09-11 — Dennis asked for extensive comparison with popular agentic GitHub projects after restoring finite review.
**Effort gate:** high — distinguish published practices from measured effects and our collaboration needs from avoidable work.

## Intent

Dennis can decide which remaining working rules deserve keeping or testing, using current public instruction files and research rather than popularity or intuition alone.

## Words that asked for it

“Can we do research on some of the most popular agentic github projects and check their claude.md/agent.md instructions?” The main hypothesis is that recursive review was the principal source of waste, while other rules primarily support collaboration and ground truth.

## Terrain and existing work

Read docs/HOW-WE-WORK.md, docs/HOW-WE-HOLD-IT.md and docs/research/2026-09-11-review-fix-loop-diagnosis.md. The existing Hello Revenue coding-harness trial remains frozen; this research does not restart it. Search covered those existing findings and current primary literature on repository instructions. Extend that evidence with a dated, commit-pinned public repository comparison; no new runtime or doctrine mechanism is proposed here.

## Work

### 1. Compare actual current instructions

Inspect twelve widely used coding-agent repositories, recording selection limits, current popularity, revision, root and relevant nested instructions, and the distinction between contributor guidance and runtime prompts. Done means a source inventory supports every project comparison and records missing or inaccessible evidence.

Hands out: search — collect disjoint repository inventories; verifies cited files and lines before drawing conclusions.

**Met:** Fifteen repositories are compared in docs/research/2026-09-11-agent-instructions-comparison.md, with forty-two retrieved source files indexed at exact revisions in docs/research/2026-09-11-agent-instructions-inventory.json. Delegation was attempted to the two existing collectors; no usable results arrived, so the lead collected and checked the evidence directly. Roo Code is explicitly marked archived; root-file absence and contributor versus runtime layers are distinguished.

### 2. Test the interpretation against research and our rules

Read primary empirical studies, including contrary results and revised versions, and map our remaining rules to collaboration, ground truth, execution constraints and possible work amplification. Done means the report distinguishes observations, causal evidence and hypotheses, with concrete recommendations and bounded uncertainties.

**Met:** Five primary empirical studies and two vendor engineering reports are assessed against all fourteen current doctrine sections. Causal limits, revised paper results, contrary evidence, and the incomplete historical local trials are explicit.

### 3. Deliver a readable report

Publish a linked research report and comparison table in the repository. Done means Dennis can inspect sources and understand what to retain, what to test and what the evidence does not establish. No runtime or doctrine changes are included.

**Met:** The report is available as Markdown, standalone HTML and a nine-page PDF beside it. No runtime or doctrine changes were made.

## Acceptance

Source links resolve to the inspected revision where possible; popularity is not treated as efficacy; review recurrence is assessed separately from other mechanisms; prior incomplete experiments are not reported as results.

## Loop

If this comparison identifies concrete candidate rules whose costs can be isolated, use it to select a bounded next experiment after Dennis chooses the direction; otherwise improve the evidence rather than adding enforcement.

Loop: Dennis judges whether the report identifies a useful next decision — owner research recommendations by 2026-09-18

## Verification and close record

The lead read the cited source sections and verified the core claims, word counts and revision identities against fetched GitHub files. No source instructions were adopted. All report-relative links and fifteen footnote definitions resolve. PDF page count and a rendered comparison page were checked. Nineteen relevant existing title, review-record and doctrine-holder ratchet tests pass. No product code changed, so product runtime tests and another code review were not applicable; the source software remains the already-tested a6eb528 baseline. Recommendations are research judgments, not measured Needle outcomes. The existing HR experiments were not restarted.
