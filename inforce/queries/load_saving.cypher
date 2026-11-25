// Law pack loader: savings clauses. Params: $rows [{saver, saves, until, note, verified, source}].
// `saves` names a Grant (by id) or a Provision (by akn).
UNWIND $rows AS r
MATCH (s:Provision {akn: r.saver})
MATCH (t) WHERE (t:Grant AND t.id = r.saves) OR (t:Provision AND t.akn = r.saves)
MERGE (s)-[x:SAVES]->(t)
SET x.until = date(r.until), x.note = r.note, x.verified = r.verified, x.source = r.source
