// Project graph: (X)-[:USED_BY]->(Y) "X is used by Y"; (X)-[:TESTED_BY]->(T) "X is tested by T".
// Params: $rows [{source, target, type}] with type USED_BY or TESTED_BY.
UNWIND $rows AS r
MATCH (a:Artifact {id: r.source})
MATCH (b:Artifact {id: r.target})
MERGE (a)-[:$(r.type)]->(b)
