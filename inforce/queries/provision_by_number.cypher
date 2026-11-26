// Find a provision by its Act (akn or short name) and a section number in any edition. Params: $ref, $number.
MATCH (i:Instrument)-[:CONTAINS]->(p:Provision)
WHERE (i.akn = $ref OR i.short = $ref)
  AND (p.number = $number OR EXISTS { MATCH (p)-[n:NUMBERED_AS]->() WHERE n.number = $number })
RETURN p.akn AS akn, p.number AS current, p.numberNote AS note
LIMIT 1
