// What fell, or was saved, when an instrument was repealed. Params: $repealed, $on.
MATCH (law:Instrument {akn: $repealed})-[:CONTAINS]->(p:Provision)
MATCH (dep)-[:MADE_UNDER|GRANTED_UNDER]->(p)
OPTIONAL MATCH (saver:Provision)-[s:SAVES]->(dep)
  WHERE saver.validFrom <= date($on) AND (s.until IS NULL OR s.until > date($on))
RETURN coalesce(dep.title, dep.akn, dep.id) AS dependent,
       CASE WHEN saver IS NULL THEN 'FELL' ELSE 'SAVED' END AS verdict,
       saver.akn AS savedBy
LIMIT 200
