// Project graph: remove what the previous scan wrote (artifacts and their claims).
// Law copies and anything written by other tools (origin <> 'scan') are kept.
MATCH (a:Artifact {origin: 'scan'})
OPTIONAL MATCH (a)-[:HAS_CLAIM]->(c:Claim)
DETACH DELETE c, a
