// Node counts by label, for `inforce load` output and `make inspect`.
MATCH (n)
RETURN labels(n)[0] AS label, count(*) AS n
ORDER BY label
LIMIT 20
