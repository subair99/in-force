// Rules that the most artifacts rest on, directly or through callers/tests.
MATCH (r:Rule)<-[:ENCODES]-(a:Artifact)
OPTIONAL MATCH (a)<-[:TESTED_BY|USED_BY*1..3]-(ripple:Artifact)
WITH r, count(DISTINCT a) AS direct, count(DISTINCT ripple) AS downstream
MATCH (p:Provision)-[:SETS]->(r)
RETURN r.text AS rule, p.akn AS provision, direct, downstream,
       direct + downstream AS weight
ORDER BY weight DESC
LIMIT 10
