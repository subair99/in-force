// Status of a whole Act on a date. Params: $ref (akn, short name or title, any case), $on.
// A repeal listed in only some editions of the repealing Act (editionDependent) gives UNKNOWN:
// the status depends on the edition, and the repeal's note says how. A full repeal wins over one.
MATCH (i:Instrument)
WHERE i.akn = $ref OR i.short = $ref OR toLower(i.title) = toLower($ref)
OPTIONAL MATCH (by:Instrument)-[x:REPEALS]->(i)
  WHERE x.on <= date($on)
WITH i, by, x ORDER BY x.on, coalesce(x.editionDependent, false)
WITH i, collect(by)[0] AS repealer, collect(x)[0] AS rep
OPTIONAL MATCH (src:Source {id: rep.source})
RETURN i.akn AS akn, i.short AS short, i.title AS title,
  CASE
    WHEN i.commencesOn IS NOT NULL AND i.commencesOn > date($on) THEN 'NOT_YET'
    WHEN rep IS NOT NULL AND rep.editionDependent = true THEN 'UNKNOWN'
    WHEN rep IS NOT NULL THEN 'REPEALED'
    ELSE 'IN_FORCE'
  END AS status,
  rep.on AS endedOn, repealer.akn AS repealedBy, repealer.short AS repealedByShort,
  repealer.title AS repealedByTitle, rep.verified AS verified, i.verified AS instrumentVerified,
  // What the status rests on: a REPEALED (or edition-dependent) verdict on the repeal edge (a verified
  // repeal of an unverified stub Act is a verified repeal), any other verdict on the Act's own entry.
  CASE
    WHEN i.commencesOn IS NOT NULL AND i.commencesOn > date($on) THEN coalesce(i.verified, false) = true
    WHEN rep IS NOT NULL THEN coalesce(rep.verified, false) = true
    ELSE coalesce(i.verified, false) = true
  END AS statusVerified,
  src.url AS source, src.title AS sourceTitle, i.commencesOn AS commencesOn,
  rep.note AS repealNote, rep.editions AS repealEditions, i.citation AS citation
LIMIT 1
