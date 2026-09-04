# The quay display polls the office all night

**Found by:** the close of card #249, carried out.

## Observation

The office costs nothing while nothing happens — but only because the quay display is not installed. It asks the office for the berth list every eight seconds via `/api/quay`, all night, and installing it as it stands quietly breaks that.

## Done means

The display is told when the list changes and asks nothing otherwise.
