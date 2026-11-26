// Law pack loader: repeals. Params: $rows [{by, target, on, verified, source}].
// The target may be a whole instrument or one provision.
UNWIND $rows AS r
MATCH (by:Instrument {akn: r.by})
MATCH (t:Instrument|Provision {akn: r.target})
MERGE (by)-[x:REPEALS]->(t)
SET x.on = date(r.on), x.verified = r.verified, x.source = r.source,
    x.section = r.section, x.page = r.page, x.secondarySource = r.secondarySource, x.byProvision = r.byProvision
