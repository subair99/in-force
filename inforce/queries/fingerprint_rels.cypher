// Every relationship with its endpoints' keys and properties, for the what-if fingerprint.
MATCH (a)-[r]->(b)
RETURN type(r) AS type, properties(r) AS props,
       coalesce(a.key, a.akn, a.id, a.url) AS s, coalesce(b.key, b.akn, b.id, b.url) AS t
LIMIT 100000
