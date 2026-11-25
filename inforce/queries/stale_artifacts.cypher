// Project graph: artifacts that encode or cite law that is REPEALED on the date.
// Params: $stale = keys of law nodes whose status on the date is REPEALED (computed with
// status_on / instrument_status on this same graph, so the date is applied on every read).
MATCH (a:Artifact)-[l:ENCODES|HAS_CLAIM]->(x)
OPTIONAL MATCH (x:Claim)-[:CITES]->(c)
WITH a, l, x, CASE WHEN x:Claim THEN c ELSE x END AS t
WHERE t.key IN $stale
RETURN a.id AS artifact, a.kind AS kind, a.path AS path,
       collect(DISTINCT {target: t.key, label: labels(t)[0],
                         line: coalesce(l.line, x.line),
                         text: CASE WHEN x:Claim THEN x.text ELSE a.symbol END}) AS because
ORDER BY artifact
LIMIT 200
