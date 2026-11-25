// Law pack loader: grants. Params: $rows [{id, title, grantedUnder, verified}].
// grantedUnder may name a provision or a whole instrument.
UNWIND $rows AS r
MERGE (g:Grant {id: r.id})
SET g.title = r.title, g.verified = r.verified
WITH g, r
MATCH (t:Provision|Instrument {akn: r.grantedUnder})
MERGE (g)-[:GRANTED_UNDER]->(t)
