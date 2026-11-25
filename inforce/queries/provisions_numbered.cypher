// Provisions with a section number, keyed by their Act's short name (for section citations in export).
MATCH (i:Instrument)-[:CONTAINS]->(p:Provision)
WHERE p.number IS NOT NULL AND p.number <> 'TODO' AND i.short IS NOT NULL
RETURN p.akn AS akn, p.number AS number, i.short AS short, p.verified AS verified
ORDER BY akn
LIMIT 5000
