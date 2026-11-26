// One rule with the provision that sets it, its Act and source. Params: $id.
MATCH (r:Rule {id: $id})
OPTIONAL MATCH (p:Provision)-[ps:SETS]->(r)
  WHERE coalesce(ps.secondary, false) = false   // the primary provision
OPTIONAL MATCH (i:Instrument)-[:CONTAINS]->(p)
OPTIONAL MATCH (r)-[:FROM]->(s:Source)
RETURN r.id AS id, r.text AS text, r.topic AS topic, r.value AS value, r.unit AS unit,
       r.verified AS verified, p.akn AS provision, p.number AS number,
       i.akn AS instrument, i.short AS short, s.url AS source
LIMIT 1
