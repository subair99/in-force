// Law pack loader: a further provision that also sets a rule (the rule's `provision` stays primary).
// Params: $rows [{rule, provision}].
UNWIND $rows AS r
MATCH (x:Rule {id: r.rule})
MATCH (p:Provision {akn: r.provision})
MERGE (p)-[s:SETS]->(x)
SET s.secondary = true
