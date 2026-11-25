// Project graph: cache each artifact's status for quick inspection (always recomputed on read).
// Params: $rows [{id, status}], $on, $at.
UNWIND $rows AS r
MATCH (a:Artifact {id: r.id})
SET a.status = r.status, a.statusOn = date($on), a.scannedAt = $at
