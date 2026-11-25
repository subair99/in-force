// Law pack loader: published versions of an Act (bitemporal: when each was the version on record).
// Params: $rows [{key, instrument, version, recordedAt, closedAt, verified, source}].
UNWIND $rows AS r
MATCH (i:Instrument {akn: r.instrument})
MERGE (v:Version {key: r.key})
SET v.version = r.version, v.recordedAt = date(r.recordedAt), v.closedAt = date(r.closedAt),
    v.verified = r.verified, v.source = r.source
MERGE (i)-[:HAS_VERSION]->(v)
