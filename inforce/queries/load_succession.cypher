// Law pack loader: an old provision replaced as a whole by a new one. Params: $rows [{old, new, note, verified, source}].
UNWIND $rows AS r
MATCH (o:Provision {akn: r.old})
MATCH (n:Provision {akn: r.new})
MERGE (o)-[x:SUCCEEDED_BY]->(n)
SET x.note = r.note, x.verified = r.verified, x.source = r.source
