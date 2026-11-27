// Repeal lists on record on $d: for each repeal recorded per edition, whether the edition of the
// repealing Act on record on $d lists it, at which section and paragraph.
MATCH (by:Instrument)-[x:REPEALS]->(t:Instrument)
WHERE x.editions IS NOT NULL
MATCH (by)-[:HAS_VERSION]->(v:Version)
WHERE (v.recordedAt IS NULL OR v.recordedAt <= date($d))
  AND (v.closedAt IS NULL OR v.closedAt > date($d))
OPTIONAL MATCH (bp:Provision {akn: x.byProvision})-[n:NUMBERED_AS]->(v)
RETURN t.akn AS akn, coalesce(t.short, t.title) AS act, by.short AS by, v.version AS version,
       v.version IN x.editions AS listed,
       [k IN range(0, size(x.editions) - 1) WHERE x.editions[k] = v.version | x.paragraphs[k]][0] AS paragraph,
       n.number AS section, n.page AS page, x.note AS note
ORDER BY akn, version
LIMIT 500
