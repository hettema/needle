# Every season berth is paid before the boat arrives

**What matters now:** Every season berth is paid before the boat arrives — season berths paid before arrival, by count — command grep -c paid office/season.log expect >= 40 by 2026-10-31 every 7d
**What holds it back:** The invoice leaves the office late, because the meter readings it waits on arrive as text the office drops — invoices sent within a day of the reading — command grep -c "sent within a day" office/invoices.log expect >= 30 by 2026-10-31 every 7d
**Evidence:** docs/plans/2026-09-03-every-metered-kilowatt-is-billed.md (every reading since 5 July dropped); docs/plans/done/2026-06-15-the-first-invoice-leaves-the-office.md (the invoice waits on the last reading)
**Rival:** skippers pay late because the price is not shown before booking (docs/plans/2026-09-02-the-skipper-sees-the-price-before-the-berth.md); separated by the office log — the late invoices are the ones with no reading, not the ones with no price
**Recheck:** the diagnosis is read again against both measures — session harbourmaster by 2026-10-15
**Proposed:** conversation 9a3c1e7f, 2026-09-04

## Why

The harbour wants every season berth paid before the boat arrives. The
office cannot invoice a berth until the last meter reading of the previous
stay is on the invoice, and since 5 July every reading has been dropped by
the handler that reads a string as a number. The limit is metrics — the
office is blind to what it has to bill — and not market or money: the
skippers who pay late are the ones whose invoice left late, which the
office log shows berth by berth.
