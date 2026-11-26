// Notes on every provision that sets a rule, primary or secondary (e.g. a proviso in another section).
// Params: $id.
MATCH (p:Provision)-[:SETS]->(r:Rule {id: $id})
WHERE p.note IS NOT NULL
RETURN p.akn AS provision, p.number AS number, p.note AS note
ORDER BY provision
LIMIT 20
