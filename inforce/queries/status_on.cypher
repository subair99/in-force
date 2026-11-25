// Status of one provision on a date. Params: $akn, $on (ISO date).
// Ends at the earliest of: its own validTo, a repeal of the provision, a repeal of its Act.
// Starts at its own validFrom, else its Act's commencesOn.
// A saving provision that is itself in force on $on keeps an ended provision SAVED.
MATCH (p:Provision {akn: $akn})
OPTIONAL MATCH (i:Instrument)-[:CONTAINS]->(p)
OPTIONAL MATCH (rp:Instrument)-[rx:REPEALS]->(p)
  WHERE rx.on <= date($on)
OPTIONAL MATCH (ri:Instrument)-[ix:REPEALS]->(i)
  WHERE ix.on <= date($on)
WITH p, i,
     [e IN [{on: p.validTo, by: null, byShort: null}, {on: rx.on, by: rp.akn, byShort: rp.short},
             {on: ix.on, by: ri.akn, byShort: ri.short}]
        WHERE e.on IS NOT NULL AND e.on <= date($on)] AS ends
WITH p, i, ends,
     reduce(first = null, e IN ends |
       CASE WHEN first IS NULL OR e.on < first.on OR (e.on = first.on AND first.by IS NULL) THEN e ELSE first END) AS ended,
     coalesce(p.validFrom, i.commencesOn) AS startsOn
OPTIONAL MATCH (s:Provision)-[sv:SAVES]->(p)
  WHERE coalesce(s.validFrom, date('0001-01-01')) <= date($on)
    AND (sv.until IS NULL OR sv.until > date($on))
    AND EXISTS { MATCH (si:Instrument)-[:CONTAINS]->(s) WHERE coalesce(si.commencesOn, date('0001-01-01')) <= date($on) }
WITH p, i, ended, startsOn, collect(s.akn) AS savers
RETURN p.akn AS akn,
  CASE
    WHEN startsOn IS NOT NULL AND startsOn > date($on) THEN 'NOT_YET'
    WHEN ended IS NOT NULL AND size(savers) > 0 THEN 'SAVED'
    WHEN ended IS NOT NULL THEN 'REPEALED'
    ELSE 'IN_FORCE'
  END AS status,
  ended.on AS endedOn,
  ended.by AS repealedBy, ended.byShort AS repealedByShort,
  startsOn, savers, i.akn AS instrument, p.verified AS verified
LIMIT 1
