// Project graph: artifacts. Params: $rows [{id, path, symbol, kind, line, origin?}].
// origin is 'scan' unless given (agents record answers with origin 'agent').
UNWIND $rows AS r
MERGE (a:Artifact {id: r.id})
SET a.path = r.path, a.symbol = r.symbol, a.kind = r.kind, a.line = r.line,
    a.origin = coalesce(r.origin, 'scan')
