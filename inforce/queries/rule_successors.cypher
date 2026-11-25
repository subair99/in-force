// Rules that replace $id, directly or down a chain (REPLACED_BY), nearest first. Params: $id.
MATCH path = (r:Rule {id: $id})-[:REPLACED_BY*1..5]->(n:Rule)
OPTIONAL MATCH (p:Provision)-[:SETS]->(n)
OPTIONAL MATCH (n)-[:FROM]->(s:Source)
RETURN n.id AS id, n.text AS text, n.verified AS verified, p.akn AS provision,
       s.url AS source, length(path) AS depth
ORDER BY depth, id
LIMIT 20
