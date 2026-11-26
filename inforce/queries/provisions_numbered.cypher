// Provisions with a section number (any edition), keyed by their Act's short name (for citations in export).
MATCH (i:Instrument)-[:CONTAINS]->(p:Provision)
WHERE i.short IS NOT NULL
OPTIONAL MATCH (p)-[n:NUMBERED_AS]->()
WITH i, p, collect(DISTINCT n.number) + [p.number] AS nums
UNWIND nums AS number
WITH DISTINCT p, i, number
WHERE number IS NOT NULL AND number <> 'TODO'
RETURN p.akn AS akn, number, i.short AS short, p.verified AS verified
ORDER BY akn, number
LIMIT 5000
