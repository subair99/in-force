// Law pack loader: provisions. Params: $rows [{akn, instrument, number, summary, validFrom, validTo, verified, stub, source}].
UNWIND $rows AS r
MERGE (p:Provision {akn: r.akn})
SET p.number = r.number, p.summary = r.summary,
    p.validFrom = date(r.validFrom), p.validTo = date(r.validTo),
    p.verified = r.verified, p.stub = r.stub
WITH p, r
MATCH (i:Instrument {akn: r.instrument})
MERGE (i)-[:CONTAINS]->(p)
WITH p, r
MATCH (s:Source {id: r.source})
MERGE (p)-[:FROM]->(s)
