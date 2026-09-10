# Two colleagues started in the same minute are told apart on the list

**Kind:** defect
**Fix:** now — the intent it breaks is written (plan 57: the one list names every colleague of either kind so a caller can name one), the fix stays inside the short id a Codex row is shown by (`runtime/codex.py::SHORT_LENGTH`, the first eight characters of a time-ordered id), and it removes the class — a prefix that two ids minted in one minute share — by showing the shortest prefix that is unique on the list, as a session id's prefix already resolves a call
**Found by:** the lane on card #110 (docs/plans/2026-09-10-a-fix-says-who-else-it-reaches-and-what-it-assumes-and-a-colleague-checks-both-before-it-ships.md), calling two cold readers of the other kind fourteen seconds apart

## The intent it breaks

The list of colleagues at work names each one so he, or a session, can point at one and say "that one" — call it, stop it, read what it is doing. Two colleagues of the other kind started in the same minute show the same name on the list, so the list shows three rows called the same thing and nothing on the page tells them apart; a call by that name is refused as naming two, which is right, but the list gave nothing better to name them by. What he loses while it does: a list he can read as "who is who" when several readers run at once, which is exactly what the review loop of card #110 does.

## The evidence

On 2026-09-10 at 09:58Z the lane on card #110 called two fresh Codex readers fourteen seconds apart (calls 74 and 75). Their ids were `01a08ac1-3ac1-…` and `01a08ac1-6e75-…`: a Codex session id is time-ordered, so its first eight characters are the minute it was minted, and `needle sessions` showed three rows `codex 01a08ac1 working background codex-01a08ac1` — the two readers and a third thread of #83's from the same minute. The rows carried different full ids in the board's call table, so the calls themselves were right; only the shown name was blind. `runtime/service.py::colleague` already refuses a prefix that names two; the list should show a prefix that names one.
