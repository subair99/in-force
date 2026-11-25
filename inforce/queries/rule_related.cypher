// Rules related to $id (read together; not successors). Params: $id.
MATCH (r:Rule {id: $id})-[x:RELATED]->(o:Rule)
RETURN o.id AS id, o.text AS text, x.note AS note, x.verified AS verified
ORDER BY id
LIMIT 20
