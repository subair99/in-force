// Law pack -> scan: every law node with a uniform key (akn, id or url).
MATCH (n)
WHERE n:Instrument OR n:Provision OR n:Rule OR n:Source OR n:Grant
RETURN labels(n)[0] AS label, coalesce(n.akn, n.id, n.url) AS key, properties(n) AS props
LIMIT 10000
