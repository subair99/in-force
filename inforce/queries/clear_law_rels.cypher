// Project graph: drop relationships between copied law nodes before re-copying them from the
// current law pack, so links removed from the pack (e.g. a withdrawn REPLACED_BY) disappear here too.
MATCH (a)-[r]->(b)
WHERE a.lawCopy = true AND b.lawCopy = true
DELETE r
