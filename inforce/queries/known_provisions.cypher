// Provisions whose text was on record on $d, for those that carry recordedAt/closedAt.
MATCH (p:Provision)
WHERE p.recordedAt IS NOT NULL OR p.closedAt IS NOT NULL
WITH p, (p.recordedAt IS NULL OR p.recordedAt <= date($d)) AND (p.closedAt IS NULL OR p.closedAt > date($d)) AS known
RETURN p.akn AS akn, p.summary AS summary, known, p.recordedAt AS recordedAt, p.closedAt AS closedAt
ORDER BY akn
LIMIT 5000
