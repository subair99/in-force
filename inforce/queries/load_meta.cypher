// Law pack loader: build hash, so `inforce load` can skip an up-to-date pack. Params: $hash.
MERGE (m:Meta {key: 'lawpack'})
SET m.buildHash = $hash
