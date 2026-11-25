// ask: nearest rules to the question's embedding (over-fetch; status by date is applied after). Params: $q.
MATCH (r:Rule)
SEARCH r IN (VECTOR INDEX rule_embedding FOR $q LIMIT 20) SCORE AS score
RETURN r.id AS id, score
ORDER BY score DESC
LIMIT 20
