// Law pack loader: instruments. Params: $rows [{akn, short, title, kind, assentedOn, commencesOn, verified, source}].
// Dates arrive as ISO strings or null; date(null) is null, so the property is left unset.
UNWIND $rows AS r
MERGE (i:Instrument {akn: r.akn})
SET i.short = r.short, i.title = r.title, i.kind = r.kind,
    i.assentedOn = date(r.assentedOn), i.commencesOn = date(r.commencesOn),
    i.verified = r.verified, i.stub = r.stub
WITH i, r
MATCH (s:Source {id: r.source})
MERGE (i)-[:FROM]->(s)
