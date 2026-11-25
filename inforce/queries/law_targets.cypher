// Project graph: every law node an artifact rests on (encoded rules, cited rules/provisions/Acts).
MATCH (a:Artifact)-[:ENCODES|HAS_CLAIM]->(x)
OPTIONAL MATCH (x:Claim)-[:CITES]->(c)
WITH CASE WHEN x:Claim THEN c ELSE x END AS t
WHERE t IS NOT NULL
RETURN DISTINCT labels(t)[0] AS label, t.key AS key
ORDER BY label, key
LIMIT 1000
