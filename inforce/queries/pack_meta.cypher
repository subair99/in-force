// Law pack: the build hash stored by the last `inforce load`.
MATCH (m:Meta {key: 'lawpack'})
RETURN m.buildHash AS hash
LIMIT 1
