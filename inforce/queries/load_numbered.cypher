// Law pack loader: a provision's section number in one published edition of its Act.
// Params: $rows [{provision, version, number, page, text}].
UNWIND $rows AS r
MATCH (p:Provision {akn: r.provision})
MATCH (v:Version {key: r.version})
MERGE (p)-[n:NUMBERED_AS]->(v)
SET n.number = r.number, n.page = r.page, n.text = r.text
