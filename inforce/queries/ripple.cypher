// Project graph: what rests on each artifact, up to 3 hops along USED_BY / TESTED_BY. Params: $ids.
UNWIND $ids AS id
MATCH (a:Artifact {id: id})-[:USED_BY|TESTED_BY*1..3]->(r:Artifact)
RETURN id AS artifact, collect(DISTINCT r.id) AS alsoCheck
LIMIT 500
