# The night audit re-reads the whole harbour log

**Found by:** the cost review of 2026-09-01.

## Observation

The night audit reads only what changed since the last one. Today it reads all 14,000 log lines every night, and the log grows by the season.

## Done means

The audit keeps a cursor; a night's read is bounded by the day's lines.
