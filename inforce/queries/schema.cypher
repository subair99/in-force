// Applied by `inforce load` (law pack) and on first `scan` (project graph).
// One statement per line block; the loader splits on ';'.
CREATE CONSTRAINT instrument_akn IF NOT EXISTS FOR (i:Instrument) REQUIRE i.akn IS UNIQUE;
CREATE CONSTRAINT provision_akn IF NOT EXISTS FOR (p:Provision) REQUIRE p.akn IS UNIQUE;
CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:Artifact) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT source_url IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE;
CREATE FULLTEXT INDEX provision_text IF NOT EXISTS FOR (p:Provision) ON EACH [p.summary];
CREATE FULLTEXT INDEX rule_text IF NOT EXISTS FOR (r:Rule) ON EACH [r.text, r.topic];
// Rule embeddings for `ask` (model2vec potion-base-8M: 256 dimensions, checked 2026-11-25).
// No WITH-filter: status depends on the date asked about, so `ask` over-fetches and filters by date after.
CREATE VECTOR INDEX rule_embedding IF NOT EXISTS
  FOR (r:Rule) ON (r.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 256, `vector.similarity_function`: 'cosine'}};
