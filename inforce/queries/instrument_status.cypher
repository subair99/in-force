// Status of a whole Act on a date. Params: $ref (akn, short name or title, any case), $on.
MATCH (i:Instrument)
WHERE i.akn = $ref OR i.short = $ref OR toLower(i.title) = toLower($ref)
OPTIONAL MATCH (by:Instrument)-[x:REPEALS]->(i)
  WHERE x.on <= date($on)
WITH i, by, x ORDER BY x.on
WITH i, collect(by)[0] AS repealer, collect(x)[0] AS rep
OPTIONAL MATCH (src:Source {id: rep.source})
RETURN i.akn AS akn, i.short AS short, i.title AS title,
  CASE
    WHEN i.commencesOn IS NOT NULL AND i.commencesOn > date($on) THEN 'NOT_YET'
    WHEN rep IS NOT NULL THEN 'REPEALED'
    ELSE 'IN_FORCE'
  END AS status,
  rep.on AS endedOn, repealer.akn AS repealedBy, repealer.short AS repealedByShort,
  repealer.title AS repealedByTitle, rep.verified AS verified, i.verified AS instrumentVerified,
  src.url AS source
LIMIT 1
