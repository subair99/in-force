// Project graph: claims in documents, each citing a law node when recognised.
// Params: $rows [{id, artifact, text, kind, line, target}] (target null = not recognised).
UNWIND $rows AS r
MATCH (a:Artifact {id: r.artifact})
MERGE (c:Claim {id: r.id})
SET c.text = r.text, c.kind = r.kind, c.line = r.line
MERGE (a)-[:HAS_CLAIM]->(c)
WITH c, r
MATCH (t {key: r.target})
MERGE (c)-[:CITES]->(t)
