// Law pack loader: rules. Params: $rows [{id, provision, text, topic, value, unit, verified, source, embedding}].
UNWIND $rows AS r
MERGE (x:Rule {id: r.id})
SET x.text = r.text, x.topic = r.topic, x.value = r.value, x.unit = r.unit, x.verified = r.verified,
    x.embedding = r.embedding
WITH x, r
MATCH (p:Provision {akn: r.provision})
MERGE (p)-[:SETS]->(x)
WITH x, r
MATCH (s:Source {id: r.source})
MERGE (x)-[:FROM]->(s)
