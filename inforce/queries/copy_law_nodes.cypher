// Project graph: copy law nodes the repo depends on. Params: $rows [{label, key, props}].
UNWIND $rows AS r
MERGE (n:$(r.label) {key: r.key})
SET n += r.props, n.lawCopy = true
