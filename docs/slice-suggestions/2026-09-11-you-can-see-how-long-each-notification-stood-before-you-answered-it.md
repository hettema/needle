# You can see how long each notification stood before you answered it

**Kind:** defect
**Fix:** now — #41's item 4 (`docs/plans/done/2026-09-05-a-card-that-finishes-or-needs-you-stays-on-screen-until-you-dismiss-it.md`) is the written intent: how long each popup stood is the other half of the reading that decides whether the sound stays, the popup goes, or the reading says he was away, and its review's finding 12 added the answer log for exactly that; a line that does not say which popup it answers cannot give that for any card the board told him about twice before he answered; the fix stays inside the line the popup's own shell writes (`runtime/notice.py::tell`) and removes the class: every answer line names the moment its popup was raised, so each line joins its one told row whatever else rang on the card
**Found by:** #41's reading, 2026-09-11

## The intent it breaks

When a card finishes or needs you, the board keeps a note of when you answered its notification, so the reading of whether the notification is worth its interruption can tell a popup you dismissed in seconds from one that sat for hours. The note says when it was answered, the project, the card, and whether you pressed or dismissed it, but not which notification it answers, so on any card the board told you about more than once — Needle's #83 was told 50 times in two days — a missing or late answer shifts every answer after it onto the wrong notification, and the reading that decides whether the notifications stay cannot say how long any of that card's stood.

## Evidence

- The laptop's answer log (`~/.local/share/needle/told.log`, read 2026-09-11 13:59 local): 92 lines of the form `2026-09-09T19:41:32Z hellorevenue 456 dismissed` — the stamp is `date -u` when the popup closed (`runtime/notice.py`, the `record` words in `tell`), and nothing on the line says when it was raised.
- The board's memory on the laptop (`~/.local/share/needle/needle.db`, opened read-only the same minute): 98 `told` rows since the fold. Per card, rows against answer lines: hellorevenue #456 11 against 10, #483 18 against 17, #503 3 against 2, needle #83 50 against 47; #409, needle #107 and omarchy #52 match. Six notifications have no line, and nothing says whether each still stands or its shell was ended before writing.
- What that does to the reading: pairing each row with the next line for its card puts hellorevenue #456's exit notification of 2026-09-09 15:16:12Z against the line at 19:41:32Z — four hours and 25 minutes standing — when that line may as well answer the notification raised at 19:41:25Z, seven seconds earlier. The two readings of the plan's item 4 (dismissed within a minute: the notification is noise; sat for hours: he was away) come out opposite on the same card.
- Four stamps carry more than one line (2026-09-10 06:43:57Z ×2, 17:01:47Z ×2, 18:38:12Z ×3, 19:11:59Z ×2), across different projects, which is several notifications closed in the same second; the line cannot say which rows those were either.

## What would fix it

The popup's shell writes the raise stamp — the same instant as the `told` row the loop writes before raising it — beside the answer stamp, so a line joins its row exactly and a missing line is a known notification that was never answered, not a shift. A test on the test board raises two notifications for one card, answers the second first, and reads each line back against its own row.
