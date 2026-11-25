// Law pack -> scan: every relationship between law nodes, by endpoint keys.
MATCH (a)-[r]->(b)
RETURN type(r) AS type, coalesce(a.akn, a.id, a.url) AS s, coalesce(b.akn, b.id, b.url) AS t,
       properties(r) AS props
LIMIT 50000
