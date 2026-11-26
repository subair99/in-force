// When the provision that sets $id was replaced as a whole (SUCCEEDED_BY), the rules the new
// provision sets on the same topic: the whole new scale, in id order. Params: $id.
MATCH (r:Rule {id: $id})<-[ps:SETS]-(p:Provision)-[s:SUCCEEDED_BY]->(n:Provision)
WHERE coalesce(ps.secondary, false) = false
MATCH (n)-[ns:SETS]->(x:Rule)
WHERE coalesce(ns.secondary, false) = false AND x.topic = r.topic
OPTIONAL MATCH (i:Instrument)-[:CONTAINS]->(n)
RETURN n.akn AS provision, n.number AS number, i.short AS short, s.note AS note, s.verified AS verified,
       x.id AS id, x.text AS text, x.value AS value, x.verified AS ruleVerified
ORDER BY x.id
LIMIT 50
