// Project graph: code that encodes a rule. Params: $rows [{artifact, rule, line, pattern}].
UNWIND $rows AS r
MATCH (a:Artifact {id: r.artifact})
MATCH (x:Rule {id: r.rule})
MERGE (a)-[e:ENCODES]->(x)
SET e.line = r.line, e.pattern = r.pattern
