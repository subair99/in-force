// Every rule (id order).
MATCH (r:Rule)
RETURN r.id AS id, r.text AS text
ORDER BY id
LIMIT 5000
