// Every date in the law pack at which some status can change (start, end, repeal, saving end,
// commencement). Status is constant between consecutive dates, so `export` evaluates each one.
MATCH (p:Provision)
WITH collect(p.validFrom) + collect(p.validTo) AS ds
MATCH (i:Instrument)
WITH ds, collect(i.commencesOn) AS more
WITH ds + more AS ds
OPTIONAL MATCH ()-[r:REPEALS]->()
WITH ds, collect(r.on) AS more
WITH ds + more AS ds
OPTIONAL MATCH ()-[s:SAVES]->()
WITH ds, collect(s.until) AS more
UNWIND ds + more AS d
WITH DISTINCT d
WHERE d IS NOT NULL
RETURN d
ORDER BY d
LIMIT 1000
