# hee/v1 Measure

Measure is a hee-object used to represent:
- finance: bank transactions, ledger transactions, fills, positions, balances, derived measures
- ops: monitoring metrics (nagios/perfdata), time series (rrd), gauges/counters, derived ops measures

Universal labels (required on all hee objects):
- metadata.labels.hee.object: "true"
- metadata.labels.hee.tcos/env: test|prod
- metadata.labels.hee.tcos/topic: finance|ops|...

Notes:
- spec is payload/content.
- status is reserved for gate/validation summaries.
- prefer raw-first normalization:
  - *_raw: verbatim strings from source
  - *_dec: numeric as string (avoid float rounding)
  - *_cents / *_micros: fixed-point ints when safe
