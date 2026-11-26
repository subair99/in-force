// Law pack loader: provisions. Params: $rows [{akn, instrument, number, summary, validFrom, validTo,
// recordedAt, closedAt, verified, stub, source}]. recordedAt/closedAt: when this text was on record (bitemporal).
UNWIND $rows AS r
MERGE (p:Provision {akn: r.akn})
SET p.number = r.number, p.summary = r.summary,
    p.validFrom = date(r.validFrom), p.validTo = date(r.validTo),
    p.recordedAt = date(r.recordedAt), p.closedAt = date(r.closedAt),
    p.verified = r.verified, p.stub = r.stub, p.page = r.page, p.secondarySource = r.secondarySource
WITH p, r
MATCH (i:Instrument {akn: r.instrument})
MERGE (i)-[:CONTAINS]->(p)
WITH p, r
MATCH (s:Source {id: r.source})
MERGE (p)-[:FROM]->(s)
