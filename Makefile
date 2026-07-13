.PHONY: compile test validate simulate check report materials knowledge-audit knowledge-enrich-primary-math knowledge-enrich-secondary-math knowledge-enrich-math-assessment knowledge-enrich-chinese knowledge-enrich-english knowledge-enrich-stem-sciences knowledge-enrich-social-studies knowledge-enrich-science-technology knowledge-enrich-practical-arts knowledge-enrich-all web health backup bundle init-repo release tag all

PYTHON := PYTHONPYCACHEPREFIX=/private/tmp/pycache python3

compile:
	$(PYTHON) -m py_compile edu_tracker/__init__.py edu_tracker/__main__.py edu_tracker/cli.py edu_tracker/data_management.py edu_tracker/input_validation.py edu_tracker/materials.py edu_tracker/models.py edu_tracker/knowledge_registry.py edu_tracker/ocr.py edu_tracker/pipeline.py edu_tracker/reporting.py edu_tracker/storage.py edu_tracker/validation.py edu_tracker/web.py services/__init__.py services/edu_tracker/cli.py services/edu_tracker/data_management.py services/edu_tracker/input_validation.py services/edu_tracker/materials.py services/edu_tracker/models.py services/edu_tracker/knowledge_registry.py services/edu_tracker/ocr.py services/edu_tracker/pipeline.py services/edu_tracker/reporting.py services/edu_tracker/storage.py services/edu_tracker/validation.py services/edu_tracker/web.py

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) -m edu_tracker validate

simulate:
	$(PYTHON) scripts/run_flow_simulation.py

check: compile test validate

report:
	$(PYTHON) -m edu_tracker report

materials:
	$(PYTHON) -m edu_tracker materials

knowledge-audit:
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-primary-math:
	$(PYTHON) scripts/enrich_primary_math.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-secondary-math:
	$(PYTHON) scripts/enrich_secondary_math.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-math-assessment:
	$(PYTHON) scripts/enrich_math_assessment.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-chinese:
	$(PYTHON) scripts/enrich_chinese.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-english:
	$(PYTHON) scripts/enrich_english.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-stem-sciences:
	$(PYTHON) scripts/enrich_stem_sciences.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-social-studies:
	$(PYTHON) scripts/enrich_social_studies.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-science-technology:
	$(PYTHON) scripts/enrich_science_technology.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-practical-arts:
	$(PYTHON) scripts/enrich_practical_arts.py
	$(PYTHON) scripts/audit_knowledge_content.py

knowledge-enrich-all:
	$(PYTHON) scripts/enrich_primary_math.py
	$(PYTHON) scripts/enrich_secondary_math.py
	$(PYTHON) scripts/enrich_math_assessment.py
	$(PYTHON) scripts/enrich_chinese.py
	$(PYTHON) scripts/enrich_english.py
	$(PYTHON) scripts/enrich_stem_sciences.py
	$(PYTHON) scripts/enrich_social_studies.py
	$(PYTHON) scripts/enrich_science_technology.py
	$(PYTHON) scripts/enrich_practical_arts.py
	$(PYTHON) scripts/audit_knowledge_content.py

web:
	$(PYTHON) -m edu_tracker web

health:
	$(PYTHON) -m edu_tracker health

backup:
	$(PYTHON) -m edu_tracker backup

all: check report materials

bundle:
	sh scripts/build_transfer_bundle.sh

init-repo:
	@test -n "$(TARGET)" || (echo "请通过 TARGET=/path/to/repo 指定目标目录" >&2; exit 1)
	sh scripts/init_independent_repo.sh "$(TARGET)"

release:
	@test -n "$(VERSION)" || (echo "请通过 VERSION=0.1.2 指定版本号" >&2; exit 1)
	sh scripts/generate_release_note.sh "$(VERSION)"

tag:
	@test -n "$(VERSION)" || (echo "请通过 VERSION=0.1.2 指定版本号" >&2; exit 1)
	sh scripts/create_git_tag.sh "$(VERSION)"
