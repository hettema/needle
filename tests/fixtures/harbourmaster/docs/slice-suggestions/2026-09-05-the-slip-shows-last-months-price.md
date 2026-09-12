# The slip shows last month's price

**Kind:** defect
**Fix:** now — the tariff plan says the price on a slip is the price on the day it is printed, and the slip reads the month before
**Found by:** the owner, 2026-09-05, from a skipper's letter.

## The intent it breaks

A skipper pays what the tariff says today. A slip that shows last month's price is a bill the office has to take back and print again, and until it does the skipper believes a number that is not true.

## Observation

`office/slip.py::price_of` reads the tariff table by the month the berth was let, not the month the slip is printed. Every tariff change since spring has produced a week of wrong slips.

## What would hold it

The slip reads the tariff by the day of printing, and the office's nightly check refuses a slip whose price differs from the tariff that day.
