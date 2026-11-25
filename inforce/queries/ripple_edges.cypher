// Project graph: all ripple edges, to explain why an artifact is affected.
MATCH (a:Artifact)-[e:USED_BY|TESTED_BY]->(b:Artifact)
RETURN a.id AS source, type(e) AS type, b.id AS target
LIMIT 5000
