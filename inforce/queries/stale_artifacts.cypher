// Artifacts in the project graph resting on law repealed by $on, with no saving.
// Params: $on (ISO date string). Verify EXISTS{} support in the spike first.
MATCH (a:Artifact)-[:ENCODES]->(r:Rule)<-[:SETS]-(p:Provision)
WHERE p.validTo IS NOT NULL AND p.validTo <= date($on)
  AND NOT EXISTS {
    MATCH (s:Provision)-[sv:SAVES]->(p)
    WHERE s.validFrom <= date($on) AND (sv.until IS NULL OR sv.until > date($on))
  }
OPTIONAL MATCH (r)-[:REPLACED_BY*1..3]->(now:Rule)
OPTIONAL MATCH (a)<-[:TESTED_BY|USED_BY*1..3]-(ripple:Artifact)
RETURN a.id AS artifact, r.text AS staleRule, p.akn AS repealedProvision,
       collect(DISTINCT now.text) AS replacement,
       collect(DISTINCT ripple.id) AS alsoCheck
LIMIT 100
