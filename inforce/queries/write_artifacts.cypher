// Project graph: artifacts found by scan. Params: $rows [{id, path, symbol, kind, line}].
UNWIND $rows AS r
MERGE (a:Artifact {id: r.id})
SET a.path = r.path, a.symbol = r.symbol, a.kind = r.kind, a.line = r.line, a.origin = 'scan'
