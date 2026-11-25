// Project graph: every artifact with each law link (or unrecognised claim) it has.
MATCH (a:Artifact)
OPTIONAL MATCH (a)-[l:ENCODES|HAS_CLAIM]->(x)
OPTIONAL MATCH (x:Claim)-[:CITES]->(c)
WITH a, x, CASE WHEN x:Claim THEN c ELSE x END AS t
RETURN a.id AS artifact, a.kind AS kind, a.path AS path,
       x IS NOT NULL AS linked, t.key AS target, t.verified AS verified
ORDER BY artifact
LIMIT 5000
