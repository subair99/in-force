// What fell, or was saved, when an Act was repealed. Params: $repealed (akn or short name), $on.
// Dependents hang off the Act itself or any of its provisions (MADE_UNDER / GRANTED_UNDER).
MATCH (law:Instrument)
WHERE law.akn = $repealed OR law.short = $repealed
OPTIONAL MATCH (by:Instrument)-[x:REPEALS]->(law)
  WHERE x.on <= date($on)
WITH law, min(x.on) AS repealedOn
MATCH (dep)-[:MADE_UNDER|GRANTED_UNDER]->(base)
WHERE base = law OR EXISTS { MATCH (law)-[:CONTAINS]->(base) }
OPTIONAL MATCH (saver:Provision)-[s:SAVES]->(dep)
  WHERE coalesce(saver.validFrom, date('0001-01-01')) <= date($on)
    AND (s.until IS NULL OR s.until > date($on))
    AND EXISTS { MATCH (si:Instrument)-[:CONTAINS]->(saver) WHERE coalesce(si.commencesOn, date('0001-01-01')) <= date($on) }
    AND (saver.validTo IS NULL OR saver.validTo > date($on))
    AND NOT EXISTS { MATCH (:Instrument)-[rs:REPEALS]->(saver) WHERE rs.on <= date($on) }
    AND NOT EXISTS { MATCH (:Instrument)-[ri:REPEALS]->(:Instrument)-[:CONTAINS]->(saver) WHERE ri.on <= date($on) }
WITH law, repealedOn, dep, base, collect(saver.akn)[0] AS savedBy, collect(s.until)[0] AS savedUntil
RETURN coalesce(dep.title, dep.akn, dep.id) AS dependent, dep.id AS id,
       base.akn AS restsOn, repealedOn,
       CASE WHEN repealedOn IS NULL THEN 'STANDS'
            WHEN savedBy IS NULL THEN 'FELL'
            ELSE 'SAVED' END AS verdict,
       savedBy, savedUntil
ORDER BY dependent
LIMIT 200
