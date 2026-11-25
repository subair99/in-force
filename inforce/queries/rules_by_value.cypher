// Rules on a topic whose value equals $value (floats compared with a tolerance). Params: $topic, $value.
MATCH (r:Rule {topic: $topic})
WHERE r.value IS NOT NULL AND abs(r.value - $value) < 0.000001
RETURN r.id AS id
ORDER BY id
LIMIT 20
