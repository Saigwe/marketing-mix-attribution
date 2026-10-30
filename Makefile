PY ?= python
DB ?= warehouse/marketing.duckdb
DBT_BIN ?= dbt
DBT = cd dbt && DUCKDB_PATH=../$(DB) $(DBT_BIN)
GA4_URL = https://huggingface.co/datasets/gizdevans/ga4-bq-flattened-data/resolve/main/full_flatten_data.csv
GA4_SHA256 = f09b13d6d59f8fd72ef07095eb95085388fa873129961eb116fc0d20dc1e9012
BOOTSTRAP ?= 40

.PHONY: all download load dbt attribution mmm test clean

all: download load dbt attribution mmm test   ## real GA4 -> sessions, funnel, attribution; simulated spend -> MMM

download:   ## Google's public GA4 sample, flattened (1.8 GB), checked against a pinned sha256
	mkdir -p data/raw
	[ -s data/raw/ga4_flattened.csv ] || curl -sL -o data/raw/ga4_flattened.csv $(GA4_URL)
	echo "$(GA4_SHA256)  data/raw/ga4_flattened.csv" | sha256sum -c -

load:
	$(PY) ingestion/load_ga4.py --csv data/raw/ga4_flattened.csv --db $(DB)

dbt:
	$(DBT) deps --profiles-dir .
	$(DBT) build --profiles-dir .

attribution:   ## Markov removal-effect attribution, beside the five rule-based models from dbt
	$(PY) -m attribution.run --db $(DB) --out results

mmm:           ## simulated spend with known truth: observational vs experiment-calibrated MMM, budget optimiser
	$(PY) -m mmm.run --out results --bootstrap $(BOOTSTRAP)

test:
	$(PY) -m pytest -q

clean:
	rm -rf warehouse dbt/target dbt/logs dbt/dbt_packages
