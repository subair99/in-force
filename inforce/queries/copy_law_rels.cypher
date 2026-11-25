// Project graph: copy relationships between copied law nodes. Params: $rows [{type, s, t, props}].
UNWIND $rows AS r
MATCH (a {key: r.s})
MATCH (b {key: r.t})
MERGE (a)-[x:$(r.type)]->(b)
SET x += r.props
