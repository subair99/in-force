// Law pack loader: sources. Params: $rows [{id, url, kind, title}].
UNWIND $rows AS r
MERGE (s:Source {url: r.url})
SET s.id = r.id, s.kind = r.kind, s.title = r.title, s.citation = r.citation
