// Project graph: the rules the most artifacts rest on. Direct = artifacts that encode the rule or cite it
// in a claim; downstream = other artifacts that use or test those (USED_BY / TESTED_BY, up to 3 hops).
MATCH (a:Artifact)-[:ENCODES|HAS_CLAIM]->(x)
OPTIONAL MATCH (x:Claim)-[:CITES]->(c:Rule)
WITH a, CASE WHEN x:Rule THEN x ELSE c END AS r
WHERE r IS NOT NULL
WITH r, collect(DISTINCT a) AS direct
UNWIND direct AS d
OPTIONAL MATCH (d)-[:USED_BY|TESTED_BY*1..3]->(rip:Artifact)
WITH r, direct, collect(DISTINCT rip) AS ripple
WITH r, direct, [x IN ripple WHERE NOT x IN direct] AS down
OPTIONAL MATCH (p:Provision)-[:SETS]->(r)
RETURN r.id AS rule, r.text AS text, p.akn AS provision,
       size(direct) AS direct, size(down) AS downstream, size(direct) + size(down) AS weight,
       [x IN direct | x.id] AS directArtifacts, [x IN down | x.id] AS downstreamArtifacts
ORDER BY weight DESC, rule
LIMIT 10
