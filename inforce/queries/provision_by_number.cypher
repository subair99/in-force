// Find a provision by its Act (akn or short name) and section number. Params: $ref, $number.
MATCH (i:Instrument)-[:CONTAINS]->(p:Provision)
WHERE (i.akn = $ref OR i.short = $ref) AND p.number = $number
RETURN p.akn AS akn
LIMIT 1
