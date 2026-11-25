// Every Act (akn order), excluding the what-if placeholder.
MATCH (i:Instrument)
WHERE i.short IS NULL OR i.short <> 'WHATIF'
RETURN i.akn AS akn, i.short AS short, i.title AS title
ORDER BY akn
LIMIT 1000
