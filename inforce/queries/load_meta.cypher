// Law pack loader: build hash (YAML + loader + queries) and the embedding model used (null = none).
// Params: $hash, $model.
MERGE (m:Meta {key: 'lawpack'})
SET m.buildHash = $hash, m.embedModel = $model
