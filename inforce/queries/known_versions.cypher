// Which version of each Act was on record on $d ("known on" D): recordedAt <= D < closedAt.
// A version with no recordedAt has an unknown start: it is reported, flagged, never assumed.
MATCH (i:Instrument)-[:HAS_VERSION]->(v:Version)
WHERE (v.recordedAt IS NULL OR v.recordedAt <= date($d))
  AND (v.closedAt IS NULL OR v.closedAt > date($d))
RETURN i.akn AS akn, i.short AS short, v.version AS version, v.recordedAt AS recordedAt,
       v.closedAt AS closedAt, v.recordedAt IS NULL AS startUnknown, v.verified AS verified
ORDER BY akn, version
LIMIT 500
