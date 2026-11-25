// Every node's labels and properties, for the what-if before/after fingerprint.
MATCH (n)
RETURN labels(n) AS labels, properties(n) AS props
LIMIT 100000
