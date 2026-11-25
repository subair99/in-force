// Project graph: keys of law nodes already copied in (by any earlier scan or recorded answer).
MATCH (n)
WHERE n.lawCopy = true
RETURN n.key AS key
LIMIT 10000
