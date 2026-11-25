// Project graph: remove one artifact and its claims (before re-recording it). Params: $id.
MATCH (a:Artifact {id: $id})
OPTIONAL MATCH (a)-[:HAS_CLAIM]->(c:Claim)
DETACH DELETE c, a
