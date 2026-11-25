// What-if (always inside a transaction that is rolled back): a hypothetical Act repeals $target on $on.
// $target: a provision akn, an Act akn or an Act short name. Returns a row only if the target exists.
MATCH (t)
WHERE (t:Provision AND t.akn = $target) OR (t:Instrument AND (t.akn = $target OR t.short = $target))
MERGE (w:Instrument {akn: $key})
SET w.short = 'WHATIF', w.title = 'Hypothetical repeal', w.key = $key, w.commencesOn = date($on)
MERGE (w)-[r:REPEALS]->(t)
SET r.on = date($on)
RETURN labels(t)[0] AS label, coalesce(t.akn, t.short) AS target
LIMIT 1
