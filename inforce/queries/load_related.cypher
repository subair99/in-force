// Law pack loader: two rules worth reading together; NOT a successor. Params: $rows [{rule, related, note, verified}].
UNWIND $rows AS r
MATCH (a:Rule {id: r.rule})
MATCH (b:Rule {id: r.related})
MERGE (a)-[x:RELATED]->(b)
SET x.note = r.note, x.verified = r.verified
