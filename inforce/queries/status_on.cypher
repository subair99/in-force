// Status of one provision on a date. Params: $akn, $on.
MATCH (p:Provision {akn: $akn})
OPTIONAL MATCH (s:Provision)-[sv:SAVES]->(p)
  WHERE s.validFrom <= date($on) AND (sv.until IS NULL OR sv.until > date($on))
WITH p, collect(s.akn) AS savers
RETURN p.akn AS akn,
  CASE
    WHEN p.validFrom IS NOT NULL AND p.validFrom > date($on) THEN 'NOT_YET'
    WHEN p.validTo IS NOT NULL AND p.validTo <= date($on) AND size(savers) > 0 THEN 'SAVED'
    WHEN p.validTo IS NOT NULL AND p.validTo <= date($on) THEN 'REPEALED'
    ELSE 'IN_FORCE'
  END AS status,
  p.validTo AS repealedOn, savers
LIMIT 1
