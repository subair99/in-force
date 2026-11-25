// Law pack loader: old rule -> new rule. Params: $rows [{old, new, verified}].
UNWIND $rows AS r
MATCH (o:Rule {id: r.old})
MATCH (n:Rule {id: r.new})
MERGE (o)-[x:REPLACED_BY]->(n)
SET x.verified = r.verified
