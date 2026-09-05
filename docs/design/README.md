# Design — the comp is a gate, not a picture

The owner judges UI in product terms, and he cannot read the code to find out
what a surface will be. So a slice that builds a surface stops before the
build and shows a **comp**: a static HTML page, opened in a browser, carrying
the real data of the thing it mocks.

Needle 0.1 was built from a comp, and that step is why its surface held while
its runtime did not — the column grammar was settled at the comp, in one
sitting, before any of it was code.

## The rules

**A comp carries real data.** Lorem ipsum hides exactly the problems a comp
exists to find: a title that is four lines long, a column with sixty-three
cards, an essence sentence that says nothing. Every card in these comps is a
card off a board in the shape of the one being mocked, with its own words.
Since 2026-09-04 that board is Harbourmaster's, the synthetic project under
`tests/fixtures/harbourmaster/` that the fixtures and the page's tests also
draw on: the repository is public and carries no real project's content
(plan 01b, item 4; a ratchet holds it). The first comps were drawn from the
first real project and were re-seated on Harbourmaster with the design
unchanged — the one edit a signed comp has had, and the reason for it.

**A comp says what is staged.** A state that cannot occur in a still page —
a drag in flight, a hover, a failed write — is faked so it can be judged. The
comp names every one of them at the top, so nothing on the page is mistaken
for something the build already does.

**A comp asks for judgement, not approval.** It ends with a numbered list of
the calls it makes, split into the ones that are the executing session's
(stated, made, open to veto) and the ones that are the owner's (asked, with
the trade named). A comp with no list is a picture, and a picture cannot be
signed.

**A comp is frozen once signed, and is one file.** It is dated, it is not
edited afterwards, and the build follows it. Its stylesheet is inlined rather
than shared: a shared one lets the next slice's comp silently restyle an
already-signed page, which is the one thing a frozen record may not do. What
the build learns that the comp got wrong goes in the slice's review record,
not back into the comp.

**The comp seeds the design system; it never becomes it.** The first comp's
token set is copied once into `frontend/src/components/ui/`, and from then on
that folder is the single living source, with a ratchet refusing a raw colour
outside it. Two homes for one thing is failed alignment, so the comp keeps its
copy only as the record of what was signed.

## What is here

| File | What it is |
|---|---|
| `2026-09-03-the-board.html` | Slice 01, comp 1: the board — eight columns, cards at rest, drag, the failed write, the furled archive. |
| `2026-09-03-the-card.html` | Slice 01, comp 2: the expanded card — the five sections, before the work and after it. |
| `2026-09-04-the-colour-language/` | Slice 27, a canvas: the five-word colour language, the head, the board at rest, the collapsed card in every state, the open card, the triage lens. |
| `2026-09-05-how-far-a-running-card-has-come/` | Slice 13, a canvas: the collapsed card in every progress state, the Executing column at its real width, the open card's items with their stance, the open card in its review loop. Signed 2026-09-05. |

Open them in a browser. Both carry a **Notes** toggle that pins each judged
call to the place on the page it lives, and a **Dark** toggle, because the
board is read at both ends of the day.
