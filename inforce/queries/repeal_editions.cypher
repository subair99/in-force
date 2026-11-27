// One repeal, per edition of the repealing Act: whether that edition lists it, at which section
// and paragraph. Params: $by (repealing Act akn), $akn (repealed Act akn).
MATCH (by:Instrument {akn: $by})-[x:REPEALS]->(t:Instrument {akn: $akn})
MATCH (by)-[:HAS_VERSION]->(v:Version)
OPTIONAL MATCH (bp:Provision {akn: x.byProvision})-[n:NUMBERED_AS]->(v)
RETURN v.version AS version, v.version IN coalesce(x.editions, []) AS listed,
       [k IN range(0, size(coalesce(x.editions, [])) - 1) WHERE x.editions[k] = v.version | x.paragraphs[k]][0] AS paragraph,
       n.number AS section, n.page AS page
ORDER BY v.recordedAt
LIMIT 50
