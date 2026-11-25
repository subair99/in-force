// Applied by `inforce load` (law pack) and on first `scan` (project graph).
// One statement per line block; the loader splits on ';'.
CREATE CONSTRAINT instrument_akn IF NOT EXISTS FOR (i:Instrument) REQUIRE i.akn IS UNIQUE;
CREATE CONSTRAINT provision_akn IF NOT EXISTS FOR (p:Provision) REQUIRE p.akn IS UNIQUE;
CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:Artifact) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT source_url IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE;
CREATE FULLTEXT INDEX provision_text IF NOT EXISTS FOR (p:Provision) ON EACH [p.summary];
// Vector index: dimensions must match the embedding model (model2vec default: check in spike).
CREATE VECTOR INDEX provision_summary IF NOT EXISTS
  FOR (p:Provision) ON (p.embedding) WITH [p.inForceNow]
  OPTIONS {indexConfig: {`vector.dimensions`: 256, `vector.similarity_function`: 'cosine'}};
