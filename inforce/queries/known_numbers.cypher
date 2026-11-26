// Section numbers on record on $d: each provision's number in the edition of its Act known on that date.
MATCH (p:Provision)-[n:NUMBERED_AS]->(v:Version)<-[:HAS_VERSION]-(i:Instrument)
WHERE (v.recordedAt IS NULL OR v.recordedAt <= date($d))
  AND (v.closedAt IS NULL OR v.closedAt > date($d))
RETURN p.akn AS akn, p.summary AS summary, p.note AS note, i.short AS short, v.version AS version,
       n.number AS number, n.page AS page
ORDER BY akn
LIMIT 5000
