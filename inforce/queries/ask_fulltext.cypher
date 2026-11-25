// ask: rules whose text or topic match the question's words. Params: $q (terms joined with OR).
MATCH (r:Rule)
SEARCH r IN (FULLTEXT INDEX rule_text FOR $q LIMIT 20) SCORE AS score
RETURN r.id AS id, score
ORDER BY score DESC
LIMIT 20
