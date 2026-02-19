# RRD -> Measure contract (hee/v1)

Recommended representation: `spec.measure: metric.series` (chunked time series).

RRD provenance goes in:
- spec.context.rrd.file_ref
- spec.context.rrd.ds (RRD DS key/name)
- spec.context.rrd.ds_type (GAUGE/COUNTER/DERIVE/ABSOLUTE)
- spec.context.rrd.cf (AVERAGE/MIN/MAX/LAST)
- spec.context.rrd.rra_index
- step/resolution details: step_sec, pdp_per_row, resolution_sec, rows, xff_dec

Unknown handling:
- RRD NaN/UNKNOWN must be represented as YAML `null` (never coerced to 0).

RFC3339++:
- use explicit UTC `...Z` for RRD exports.
- keep last_update as both epoch + RFC3339 when available.

Gate candidates (future status.gates):
- step alignment
- unknown preservation
- series length integrity
