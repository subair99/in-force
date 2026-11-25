PY ?= python
LAW := data/ng-tax-2026.rl
DEMO := demo/naira-payroll

.PHONY: install spike load demo test verify export inspect clean

install:
	$(PY) -m pip install -e ".[dev,embed]"

spike:
	$(PY) scripts/spike_relate.py

load:
	inforce load --allow-unverified

demo: load
	inforce demo --fast

test:
	$(PY) -m pytest -q

# Prints every rule with its source link and verified flag, for the human to tick off.
verify:
	inforce verify

export:
	inforce export

inspect:
	relate --database $(LAW) --read-only --mode envelope "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n LIMIT 20"
	@if [ -f $(DEMO)/.inforce/project.rl ]; then \
	  relate --database $(DEMO)/.inforce/project.rl --read-only --mode envelope "MATCH (a:Artifact) RETURN a.id, a.status LIMIT 50"; \
	else echo "(no project graph yet: run 'inforce scan $(DEMO)' to create $(DEMO)/.inforce/project.rl)"; fi

clean:
	rm -rf $(DEMO)/.inforce/tmp .pytest_cache
