// Law pack: build hash and embedding model stored by the last `inforce load`.
MATCH (m:Meta {key: 'lawpack'})
RETURN m.buildHash AS hash, m.embedModel AS embedModel
LIMIT 1
